import json
import operator
from typing import Sequence, TypedDict, Annotated, List

from dotenv import load_dotenv
from langchain_core.messages import BaseMessage
from langchain_core.output_parsers import PydanticOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_openai import AzureChatOpenAI
from loguru import logger

from Config import *
from models.AgileCrewModels import ListOfTasks, \
    UserStory, ListOfUserStories, BaseUserStory, BaseFeature, Feature, Task, \
    ListOfAcceptanceCriteria

load_dotenv()




# Define the graph state
class AgentState(TypedDict):
    # The annotation tells the graph that new messages will always
    # be added to the current states
    input: Annotated[str, operator.setitem]
    messages: Annotated[Sequence[BaseMessage], operator.add]
    feature_description: Annotated[str, operator.setitem]
    # The 'next' field indicates where to route to next
    next: Annotated[str, operator.setitem]
    user_stories: Annotated[ListOfUserStories, operator.setitem]
    user_story_to_process: Annotated[BaseUserStory, operator.setitem]
    acceptance_criteria_us: Annotated[List[ListOfAcceptanceCriteria], operator.setitem]
    tasks: Annotated[List[ListOfTasks], operator.setitem]
    final_output: Annotated[Feature, operator.setitem]
    feedback: Annotated[str, operator.setitem]
    verification_attempts: Annotated[int, operator.setitem]


# Nodes


def select_next_user_story_to_process(state: AgentState):
    """ Select the next user story to process based on the user stories created """
    user_stories_to_process = [us for us in state["user_stories"].user_stories if not us.processed]
    if len(user_stories_to_process) == 0:
        return {"next": "FINISH"}
    if debug_mode:
        logger.debug(f"User story to process: {user_stories_to_process[0].title}")
    return {"next": "CONTINUE",
            "user_story_to_process": user_stories_to_process[0],
            "messages": [("system", f"Process new user story: {user_stories_to_process[0].title}")]}


def process_user_story(state: AgentState):
    """ Mark the user story as processed """
    user_story = state["user_story_to_process"]
    us_completed = [us for us in state["user_stories"].user_stories if us.title == user_story.title][0]
    us_completed.processed = True
    if debug_mode:
        logger.debug(f"User story processed: {user_story.title}")
    return {"messages": [("system", f"User story has been processed successfully. "
                                    f"\nIt looks like this: \n\n {json.dumps(user_story.dict(), indent=4)}"
                                    f"\n\nThis are the acceptance criteria for this user story:\n {json.dumps(state['acceptance_criteria_us'][-1].dict(), indent=4)}"
                                    f"\n\nThese are the tasks for this user story:\n {json.dumps(state['tasks'][-1].dict(), indent=4)}")]}



def write_final_output(state: AgentState):
    """ Generates the feature title and description and produces the final output """
    node_llm = AzureChatOpenAI(model=config.get_value_by_mapping(ConfigMapping.MODEL_DEPLOYED_FEATURE),
                               temperature=config.get_value_by_mapping(ConfigMapping.MODEL_TEMPERATURE_FEATURE))
    feature_parser = PydanticOutputParser(pydantic_object=BaseFeature)

    prompt = ChatPromptTemplate.from_messages(
        [
            ("system", config.get_value_by_mapping(ConfigMapping.FEATURE_TASK_PROMPT)),
            ("user", "This is the feature description: {feature_description}."),
            ("user", "{format_instructions}")
        ]
    )

    chain = prompt | node_llm
    result = chain.invoke({"feature_description": state["feature_description"],
                           "project_context": config.get_value_by_mapping(ConfigMapping.PROJECT_CONTEXT),
                           "format_instructions": feature_parser.get_format_instructions()})

    # Create the final output in the correct format
    final_output: Feature = Feature(**feature_parser.parse(result.content).dict())
    final_output.user_stories = [UserStory(**us.dict()) for us in state["user_stories"].user_stories]
    for i in range(len(final_output.user_stories)):
        final_output.user_stories[i].acceptance_criteria = state["acceptance_criteria_us"][i].acceptance_criteria
        final_output.user_stories[i].tasks = [Task(**task.dict()) for task in state["tasks"][i].tasks]

    if debug_mode:
        logger.debug(f"Final output: {final_output}")
    return {
        "final_output": final_output
    }

