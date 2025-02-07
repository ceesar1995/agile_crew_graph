from dotenv import load_dotenv
from langgraph.graph import END, StateGraph, START
from loguru import logger

from AgentCreator import AgentCreator
from AgentVerifier import AgentVerifier
from Config import *
from GraphElements import AgentState, select_next_user_story_to_process, \
    process_user_story, \
    write_final_output
from models.AgileCrewModels import Feature

load_dotenv()

class AgileCrewGraph:
    creator_us_agent_creator: AgentCreator
    creator_ac_agent: AgentCreator
    creator_tasks_agent: AgentCreator
    check_us_agent: AgentVerifier
    check_ac_agent: AgentVerifier
    check_tasks_agent: AgentVerifier

    def __init__(self):
        self.creator_us_agent = AgentCreator("user_story")
        self.creator_ac_agent = AgentCreator("acceptance_criteria")
        self.creator_tasks_agent = AgentCreator("tasks")
        self.check_us_agent = AgentVerifier("user_story")
        self.check_ac_agent = AgentVerifier("acceptance_criteria")
        self.check_tasks_agent = AgentVerifier("tasks")

    def create_workflow(self):
        # Define the graph
        workflow = StateGraph(AgentState)

        # Define the nodes
        workflow.add_node("user_story_creation", self.creator_us_agent.create_agent_node())
        workflow.add_node("user_stories_review", self.check_us_agent.create_agent_node())
        workflow.add_node("select_next_user_story", select_next_user_story_to_process)
        workflow.add_node("agent_ac", self.creator_ac_agent.create_agent_node())
        workflow.add_node("ac_review", self.check_ac_agent.create_agent_node())
        workflow.add_node("agent_tasks", self.creator_tasks_agent.create_agent_node())
        workflow.add_node("tasks_review", self.check_tasks_agent.create_agent_node())
        workflow.add_node("process_user_story", process_user_story)
        workflow.add_node("write_output", write_final_output)

        # Define the edges
        workflow.add_edge(START, "user_story_creation")
        last_conditional_map = {"CONTINUE": "agent_ac", "FINISH": "write_output"}
        us_creation_conditional_map = {"CONTINUE": "user_stories_review", "ERROR": "user_story_creation"}
        us_review_conditional_map = {"REVIEW": "user_story_creation", "CONTINUE": "select_next_user_story", "ERROR": "user_stories_review"}
        ac_creation_conditional_map = {"CONTINUE": "ac_review", "ERROR": "agent_ac"}
        ac_review_conditional_map = {"REVIEW": "agent_ac", "CONTINUE": "agent_tasks", "ERROR": "ac_review"}
        tasks_creation_conditional_map = {"CONTINUE": "tasks_review", "ERROR": "agent_tasks"}
        tasks_review_conditional_map = {"REVIEW": "agent_tasks", "CONTINUE": "process_user_story", "ERROR": "tasks_review"}
        workflow.add_conditional_edges("select_next_user_story", lambda x: x["next"], last_conditional_map)
        workflow.add_conditional_edges("user_stories_review", lambda x: x["next"], us_review_conditional_map)
        workflow.add_conditional_edges("ac_review", lambda x: x["next"], ac_review_conditional_map)
        workflow.add_conditional_edges("tasks_review", lambda x: x["next"], tasks_review_conditional_map)
        workflow.add_conditional_edges("user_story_creation", lambda x: x["next"], us_creation_conditional_map)
        workflow.add_conditional_edges("agent_ac", lambda x: x["next"], ac_creation_conditional_map)
        workflow.add_conditional_edges("agent_tasks", lambda x: x["next"], tasks_creation_conditional_map)
        workflow.add_edge("process_user_story", "select_next_user_story")
        workflow.add_edge("write_output", END)

        return workflow


    def invoke_graph(self, feature_description: str, project_context: str) -> Feature:
        logger.add("logs/file_{time}.log")
        workflow = self.create_workflow()
        graph = workflow.compile()
        config.set_config_value(ConfigMapping.FEATURE_DESCRIPTION, feature_description)
        config.set_config_value(ConfigMapping.PROJECT_CONTEXT, project_context)
        if debug_mode:
            logger.debug("Starting the Agile Crew Graph")
        result = graph.invoke({
            "messages": [("human", config.get_value_by_mapping(ConfigMapping.GRAPH_INITIAL_MESSAGE))],
            "feature_description": feature_description,
            "verification_attempts": 0,
        },
            config={"recursion_limit": config.get_value_by_mapping(ConfigMapping.RECURSION_LIMIT)})
        logger.debug(result.get("final_output").json())
        return result.get("final_output")

