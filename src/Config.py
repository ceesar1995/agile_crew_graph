from enum import Enum
from functools import reduce

import yaml


class ConfigMapping(Enum):

    # Graph nodes mapping
    MODEL_DEPLOYED_FEATURE = "nodes.feature_creation.model.name"
    MODEL_TEMPERATURE_FEATURE = "nodes.feature_creation.model.temperature"
    FEATURE_TASK_PROMPT = "nodes.feature_creation.prompt"

    # Agents
    AGENT_MODEL_DEPLOYED_US = "agents.user_story_creation.model.name"
    AGENT_MODEL_TEMPERATURE_US = "agents.user_story_creation.model.temperature"
    AGENT_PROMPT_US = "agents.user_story_creation.prompt"

    AGENT_MODEL_DEPLOYED_AC = "agents.acceptance_criteria.model.name"
    AGENT_MODEL_TEMPERATURE_AC = "agents.acceptance_criteria.model.temperature"
    AGENT_PROMPT_AC = "agents.acceptance_criteria.prompt"

    AGENT_MODEL_DEPLOYED_TASKS = "agents.tasks.model.name"
    AGENT_MODEL_TEMPERATURE_TASKS = "agents.tasks.model.temperature"
    AGENT_PROMPT_TASKS = "agents.tasks.prompt"

    CHECK_US_ENABLED = "agents.check_user_story_quality.enabled"
    MAX_US_VERIFICATION_ATTEMPTS = "agents.check_user_story_quality.max_verification_attempts"
    AGENT_MODEL_DEPLOYED_CHECK_US = "agents.check_user_story_quality.model.name"
    AGENT_MODEL_TEMPERATURE_CHECK_US = "agents.check_user_story_quality.model.temperature"
    AGENT_PROMPT_CHECK_US = "agents.check_user_story_quality.prompt"

    CHECK_AC_ENABLED = "agents.check_acceptance_criteria_quality.enabled"
    MAX_AC_VERIFICATION_ATTEMPTS = "agents.check_acceptance_criteria_quality.max_verification_attempts"
    AGENT_MODEL_DEPLOYED_CHECK_AC = "agents.check_acceptance_criteria_quality.model.name"
    AGENT_MODEL_TEMPERATURE_CHECK_AC = "agents.check_acceptance_criteria_quality.model.temperature"
    AGENT_PROMPT_CHECK_AC = "agents.check_acceptance_criteria_quality.prompt"

    CHECK_TASKS_ENABLED = "agents.check_tasks_quality.enabled"
    MAX_TASKS_VERIFICATION_ATTEMPTS = "agents.check_tasks_quality.max_verification_attempts"
    AGENT_MODEL_DEPLOYED_CHECK_TASKS = "agents.check_tasks_quality.model.name"
    AGENT_MODEL_TEMPERATURE_CHECK_TASKS = "agents.check_tasks_quality.model.temperature"
    AGENT_PROMPT_CHECK_TASKS = "agents.check_tasks_quality.prompt"



    # Graph mapping
    GRAPH_INITIAL_MESSAGE = "graph.initial_message"
    FEATURE_DESCRIPTION = "graph.feature_description"
    PROJECT_CONTEXT = "graph.project_context"
    RECURSION_LIMIT = "graph.recursion_limit"
    DEBUG_MODE = "graph.debug_mode"


class Config:
    def __init__(self, path: str = "src/config/config.GPT3.5.yml"):
        # Load the config yaml file as a dictionary
        with open(path, "r") as file:
            self._config = yaml.safe_load(file)

    def get_config(self, key: str) -> str:
        return self._config[key]


    def set_config_value(self, key: str, value: str):
        self._config[key] = value

    # Define the function to access nested keys
    def get_nested_key(self, nested_key: str):
        keys = nested_key.split('.')
        return reduce(lambda d, key: d[key], keys, self._config)

    def get_value_by_mapping(self, key_enum: ConfigMapping):
        return self.get_nested_key(key_enum.value)


config = Config()
debug_mode = bool(config.get_value_by_mapping(ConfigMapping.DEBUG_MODE))