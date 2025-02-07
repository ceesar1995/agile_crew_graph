
from dotenv import load_dotenv
from langchain_core.tools import tool

from Config import *

load_dotenv()

@tool
def get_project_context() -> str:
    """Get the project context for the user stories creation"""
    return config.get_value_by_mapping(ConfigMapping.PROJECT_CONTEXT)
