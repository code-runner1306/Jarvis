from core.tools import execute_shell_command, desktop_click, desktop_type, browse_web
from langchain_core.tools import tool

@tool
def ask_human_permission(action_description: str) -> str:
    """Asks the human user for permission before executing a dangerous action."""
    # In a real GUI, this would pop up a dialog. 
    # For now, we will simulate asking the user via the conversational loop.
    return "Permission requested for: " + action_description

automation_tools = [
    execute_shell_command,
    desktop_click,
    desktop_type,
    browse_web,
    ask_human_permission
]
