import functools

from langchain.agents import AgentExecutor
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI
from loguru import logger

from AgileTools import get_project_context
from Config import *
from Utils import create_agent
from models.AgileCrewModels import FeedbackOutput


class AgentVerifier:
    def __init__(self, type):
        self.type = type
        self.prompt = self.create_prompt()

    def prepare_agent_inputs(self) -> dict:
        if self.type == "user_story":
            return {
                "messages": lambda x: x["messages"],
                "feature_description": lambda x: x["feature_description"],
                "feedback": lambda x: x["feedback"] if str(x["feedback"]) not in (None, "") else "No feedback to review, this is the first iteration.",
                "user_stories": lambda x: str(x["user_stories"]) if x["user_stories"] is not None else "No user stories to "
                                                                                              "review, this is the "
                                                                                              "first iteration.",
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x["intermediate_steps"]
                ),
            }
        elif self.type == "acceptance_criteria":
            return {
                "user_story_to_process": lambda x: str(x["user_story_to_process"]),
                "feedback": lambda x: str(x["feedback"]) if x["feedback"] not in (None, "") else "No feedback to review, this is the first iteration.",
                "acceptance_criteria": lambda x: str(x["acceptance_criteria_us"][-1]),
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x["intermediate_steps"]
                ),
            }
        elif self.type == "tasks":
            return {
                "user_story_to_process": lambda x: str(x["user_story_to_process"]),
                "acceptance_criteria": lambda x: str(x["acceptance_criteria_us"][-1]),
                "feedback": lambda x: str(x["feedback"]) if x["feedback"] not in (None, "") else "No feedback to review, this is the first iteration.",
                "tasks": lambda x: str(x["tasks"][-1]) ,
                "agent_scratchpad": lambda x: format_to_openai_function_messages(
                    x["intermediate_steps"]
                ),
            }

    def create_prompt(self) -> ChatPromptTemplate:
        if self.type == "user_story":
            return ChatPromptTemplate([
                ("system", config.get_value_by_mapping(ConfigMapping.AGENT_PROMPT_CHECK_US)),
                ("user", "Feature description: \n{feature_description}"),
                ("user", "User stories to review:\n{user_stories}"),
                ("user", "Previously returned feedback:\n{feedback}"),
                ("system", "Return the feedback using the 'FeedbackOutput' tool provided."),
                MessagesPlaceholder("agent_scratchpad")],
                input_variables=["examples", "agent_scratchpad", "feature_description",
                                 "feedback", "user_stories"]).partial(examples="")
        elif self.type == "acceptance_criteria":
            return ChatPromptTemplate([
                ("system", config.get_value_by_mapping(ConfigMapping.AGENT_PROMPT_CHECK_AC)),
                ("user", "User story:\n{user_story_to_process}"),
                ("user", "Acceptance criteria to review:\n{acceptance_criteria}"),
                ("user", "Previously returned feedback:\n{feedback}"),
                ("system", "Return the feedback using the 'FeedbackOutput' tool provided."),
                MessagesPlaceholder("agent_scratchpad")],
                input_variables=["examples", "agent_scratchpad",
                                 "feedback", "acceptance_criteria", "user_story_to_process"]).partial(examples="")
        elif self.type == "tasks":
            return ChatPromptTemplate([
                ("system", config.get_value_by_mapping(ConfigMapping.AGENT_PROMPT_CHECK_TASKS)),
                ("user", "User story:\n{user_story_to_process}"),
                ("user", "Acceptance criteria:\n{acceptance_criteria}"),
                ("user", "Tasks to check:\n{tasks}"),
                ("user", "Previously returned feedback:\n {feedback}"),
                ("system", "Return the feedback using the 'FeedbackOutput' tool provided."),
                MessagesPlaceholder("agent_scratchpad")],
                input_variables=["examples", "agent_scratchpad",
                                 "feedback", "acceptance_criteria", "user_story_to_process", "tasks",
                                 "feedback_tasks"]).partial(examples="")


    def create_verifier_agent(self):
        if self.type == "user_story":
            model_name = config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_DEPLOYED_CHECK_US)
            model_temp = config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_TEMPERATURE_CHECK_US)
        elif self.type == "acceptance_criteria":
            model_name = config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_DEPLOYED_CHECK_AC)
            model_temp = config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_TEMPERATURE_CHECK_AC)
        elif self.type == "tasks":
            model_name = config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_DEPLOYED_CHECK_TASKS)
            model_temp = config.get_value_by_mapping(ConfigMapping.AGENT_MODEL_TEMPERATURE_CHECK_TASKS)
        llm_with_tools = AzureChatOpenAI(model=model_name,temperature=model_temp).\
            bind_functions([get_project_context, FeedbackOutput])

        return create_agent(llm_with_tools, self.prompt, self.prepare_agent_inputs())

    def retrieve_agent_config_values(self):
        if self.type == "user_story":
            return {
                "check_enabled": config.get_value_by_mapping(ConfigMapping.CHECK_US_ENABLED),
                "max_verification_attempts": config.get_value_by_mapping(ConfigMapping.MAX_US_VERIFICATION_ATTEMPTS),
            }
        elif self.type == "acceptance_criteria":
            return {
                "check_enabled": config.get_value_by_mapping(ConfigMapping.CHECK_AC_ENABLED),
                "max_verification_attempts": config.get_value_by_mapping(ConfigMapping.MAX_AC_VERIFICATION_ATTEMPTS),
            }
        elif self.type == "tasks":
            return {
                "check_enabled": config.get_value_by_mapping(ConfigMapping.CHECK_TASKS_ENABLED),
                "max_verification_attempts": config.get_value_by_mapping(ConfigMapping.MAX_TASKS_VERIFICATION_ATTEMPTS),
            }

    def agent_node_check(self, state, agent, name):
        config_values = self.retrieve_agent_config_values()
        if not config_values["check_enabled"] or \
                state["verification_attempts"] >= config_values["max_verification_attempts"]:
            return {"next": "CONTINUE",
                    "feedback": "",
                    "verification_attempts": 0}
        result = agent.invoke(state, return_only_outputs=True, )
        try:
            feedback = FeedbackOutput(**result)
        except Exception as e:
            logger.error(f"Error parsing the output: {e}")
            return {"next": "ERROR"}
        if debug_mode:
            logger.debug(f"Feedback: {feedback}")
        if feedback.needs_review:
            result = {
                "next": "REVIEW",
                "feedback": feedback.feedback,
                "verification_attempts": state["verification_attempts"] + 1
            }
            if self.type == "acceptance_criteria":
                result["acceptance_criteria_us"] = state["acceptance_criteria_us"]
            elif self.type == "tasks":
                result["tasks"] = state["tasks"]
            return result
        else:
            return {"next": "CONTINUE",
                    "feedback": "",
                    "verification_attempts": 0}

    def create_agent_node(self):
        agent = self.create_verifier_agent()
        executor = AgentExecutor(tools=[get_project_context], agent=agent, verbose=True)
        if self.type == "user_story":
            return functools.partial(self.agent_node_check, agent=executor, name="check_us_quality")
        elif self.type == "acceptance_criteria":
            return functools.partial(self.agent_node_check, agent=executor, name="check_ac_quality")
        elif self.type == "tasks":
            return functools.partial(self.agent_node_check, agent=executor, name="check_tasks_quality")