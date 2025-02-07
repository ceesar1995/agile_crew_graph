import json

from bluesheperd.core.items import Feature, Task, UserStory
from bluesheperd.core.project import AzureProject
from langchain_core.agents import AgentActionMessageLog, AgentFinish
from langchain_core.prompts import ChatPromptTemplate


def prepare_tool_prompt(task: str, task_requirements: str, task_input: str) -> ChatPromptTemplate:
    return ChatPromptTemplate.from_messages(
        [
            ("user", "{role}"),
            ("user", task + " Do your best, your work depends on it."),
            ("user", task_requirements),
            ("user", task_input),
            ("user", "{format_instructions}")
        ]
    )

def parse(output):
    # If no function was invoked, return to user
    if "function_call" not in output.additional_kwargs:
        return AgentFinish(return_values={"output": output.content}, log=output.content)

    # Parse out the function call
    function_call = output.additional_kwargs["function_call"]
    name = function_call["name"]
    inputs = json.loads(function_call["arguments"])

    if name in ("ListOfUserStories", "ListOfAcceptanceCriteria", "ListOfTasks", "FeedbackOutput"):
        return AgentFinish(return_values=inputs, log=str(function_call))
    # Otherwise, return an agent action
    else:
        return AgentActionMessageLog(
            tool=name, tool_input=inputs, log="", message_log=[output]
        )


def create_agent(agent_llm, prompt, inputs):
    agent = (
            inputs
            | prompt
            | agent_llm
            | parse
    )
    return agent

def save_to_ado(llm_output: str, project: AzureProject | None = None):
    llm_output = json.loads(llm_output)

    parent_feature = {
        k: v for k, v in llm_output["items"][0].items() if k != "user_stories"
    }

    feat = Feature(
        title=parent_feature["title"],
        description=parent_feature["description"],
        project=project,
    )

    created_feature = feat.create_item()

    user_stories = llm_output["items"][0]["user_stories"]
    for idx, user_story in enumerate(user_stories):
        user_stories[idx] = {k: v for k, v in user_story.items()}

    ado_user_stories = []
    for us in user_stories:
        children_tasks = [
            Task(
                title=task["title"],
                description=task["description"],
                project=project,
            )
            for task in us["tasks"]
        ]

        ado_user_stories.append(
            UserStory(
                title=us["title"],
                description=us["description"],
                acceptance_criteria=us["acceptance_criteria"],
                parent_url=created_feature[0].url,
                children=children_tasks,
                project=project,
            ).create_item()
        )

    return None