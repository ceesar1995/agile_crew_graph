import functools

from dotenv import load_dotenv
from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI
from loguru import logger

from AgileTools import get_project_context
from Config import *
from Utils import create_agent
from models.AgileCrewModels import ListOfTasks, \
    ListOfAcceptanceCriteria, ListOfUserStories

load_dotenv()



class AgentCreator:

    def __init__(self, type: str):
        self.type = type

    def get_prompt(self):
        if self.type == "user_story":
            return ChatPromptTemplate([MessagesPlaceholder("messages"),
                                ("system", config.get_value_by_mapping(ConfigMapping.AGENT_PROMPT_US)),
                             ("user", "Feature description: \n {feature_description}"),
                             ("user", "This is some feedback from previously created user stories:\n {feedback}"),
                             ("user", "Previously created user stories:\n {previously_created_user_stories}"),
                             ("system", "Return the output using the tools provided."),
                             MessagesPlaceholder("agent_scratchpad")],
                            input_variables=["messages", "examples", "agent_scratchpad", "feature_description",
                                             "feedback", "previously_created_user_stories"]).partial(examples="")
        elif self.type == "acceptance_criteria":
            return ChatPromptTemplate(
                    [MessagesPlaceholder("messages"),
                     ("system", config.get_value_by_mapping(ConfigMapping.AGENT_PROMPT_AC)),
                     ("user", "Feature description: \n {feature_description}"),
                     ("user", "User story:\n {user_story_to_process}"),
                     ("user", "This is some feedback from previously created acceptance_criteria:\n {feedback}"),
                     ("user", "Previously created acceptance criteria:\n {previously_created_ac}"),
                     ("system", "Return the output using the tools provided."),
                     MessagesPlaceholder("agent_scratchpad")],
                    input_variables=["examples", "agent_scratchpad", "user_story_to_process", "feedback",
                     "previously_created_ac"]).partial(examples="")
        elif self.type =="tasks":
            return ChatPromptTemplate(
                [MessagesPlaceholder("messages"),("system", config.get_value_by_mapping(ConfigMapping.AGENT_PROMPT_TASKS)),
                 ("user", "User story:\n {user_story_to_process}"),
                 ("user", "Acceptance criteria:\n {acceptance_criteria}"),
                 ("user", "This is some feedback from previusly created tasks:\n {feedback}"),
                 ("user", "Previously created tasks:\n {previously_created_tasks}"),
                 ("user", "You must return the output using the tools provided in the expected format."),
                 MessagesPlaceholder("agent_scratchpad")],
    input_variables=["examples", "agent_scratchpad", "user_story_to_process", "feedback",
                     "acceptance_criteria", "previously_created_tasks"]).partial(examples="")


    def get_llm_with_tools(self):
        if self.type == "user_story":
            return AzureChatOpenAI(model=config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_DEPLOYED_US),
                               temperature=config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_TEMPERATURE_US)).bind_functions([get_project_context, ListOfUserStories])
        elif self.type == "acceptance_criteria":
            return AzureChatOpenAI(model=config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_DEPLOYED_AC),
                               temperature=config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_TEMPERATURE_AC)).bind_functions([get_project_context, ListOfAcceptanceCriteria])
        elif self.type == "tasks":
            return AzureChatOpenAI(model=config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_DEPLOYED_TASKS),
                               temperature=config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_TEMPERATURE_TASKS)).bind_functions([get_project_context, ListOfTasks])

    def get_inputs(self):
        if self.type == "user_story":
            return {
                "messages": lambda x: x["messages"],
                "feature_description": lambda x: x["feature_description"],
                "feedback": lambda x: str(x["feedback"]) if x["feedback"] not in (None, "") else "No feedback received, this is the first iteration.",
                "previously_created_user_stories": lambda x: str(x["user_stories"]) if x["user_stories"] is not None else "No user stories to review, this is the first iteration.",
                # Format agent scratchpad from intermediate steps
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x["intermediate_steps"]
                ),
            }
        elif self.type == "acceptance_criteria":
            return {
                "messages": lambda x: x["messages"],
                "user_story_to_process": lambda x: str(x["user_story_to_process"]),
                "feature_description": lambda x: x["feature_description"],
                "feedback": lambda x: str(x["feedback"])  if x["feedback"] not in (None, "") else "No feedback received, this is the first iteration.",
                "previously_created_ac": lambda x: str(x["acceptance_criteria_us"][-1]) if x["feedback"] not in (None,"") else None,
                # Format agent scratchpad from intermediate steps
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x["intermediate_steps"]
                ),
            }
        elif self.type == "tasks":
            return {
                "messages": lambda x: x["messages"],
                "user_story_to_process": lambda x: str(x["user_story_to_process"]),
                "acceptance_criteria": lambda x: str(x["acceptance_criteria_us"][-1]),
                "feedback": lambda x: str(x["feedback"]) if x["feedback"] not in (None, "") else "No feedback received, this is the first iteration.",
                "previously_created_tasks": lambda x: str(x["tasks"][-1]) if x["feedback"] not in (None, "") else None,
                # Format agent scratchpad from intermediate steps
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x["intermediate_steps"]
                ),
            }

    @staticmethod
    def agent_node_us(state, agent, name):
        result = agent.invoke(state, return_only_outputs=True, )
        try:
            us = ListOfUserStories(**result)
        except Exception as e:
            logger.error(f"Error parsing the output: {e}")
            return {"next": "ERROR"}
        logger.debug(f"User stories created: {us.json(indent=2)}")
        return {
            "next": "CONTINUE",
            "user_stories": us
        }

    @staticmethod
    def agent_node_tasks(state, agent, name):
        result = agent.invoke(state)
        try:
            new_tasks = ListOfTasks(**result)
        except Exception as e:
            logger.error(f"Error parsing the output: {e}")
            return {"next": "ERROR"}
        if state["feedback"] not in ("", None):
            tasks = state["tasks"][:-1] + [new_tasks]
        elif state["tasks"] is None:
            tasks = [new_tasks]
        else:
            tasks = state["tasks"] + [new_tasks]
        return {
            "next": "CONTINUE",
            "tasks": tasks
        }

    @staticmethod
    def agent_node_ac(state, agent, name):
        result = agent.invoke(state)
        try:
            new_ac = ListOfAcceptanceCriteria(**result)
        except Exception as e:
            logger.error(f"Error parsing the output: {e}")
            return {"next": "ERROR"}

        if state["feedback"] not in ("", None):
            acceptance_criteria = state["acceptance_criteria_us"][:-1] + [new_ac]
        elif state["acceptance_criteria_us"] is None:
            acceptance_criteria = [new_ac]
        else:
            acceptance_criteria = state["acceptance_criteria_us"] + [new_ac]
        return {
            "next": "CONTINUE",
            "acceptance_criteria_us": acceptance_criteria
        }
    def create_agent_node(self):
        agent = create_agent(self.get_llm_with_tools(), self.get_prompt(), self.get_inputs())
        agent_executor = AgentExecutor(tools=[get_project_context], agent=agent, verbose=True)
        if self.type == "user_story":
            return functools.partial(self.agent_node_us, agent=agent_executor, name="user_story_creation")
        elif self.type == "acceptance_criteria":
            return functools.partial(self.agent_node_ac, agent=agent_executor, name="acceptance_criteria_creation")
        elif self.type == "tasks":
            return functools.partial(self.agent_node_tasks, agent=agent_executor, name="tasks_creation")
