import subprocess
from langchain_core.tools import tool
import pyautogui
from playwright.async_api import async_playwright
import os

@tool
def execute_shell_command(command: str) -> str:
    """Executes a local shell command and returns the output. Use this to interact with the file system."""
    try:
        # Security note: In a real production system, you'd want to restrict what commands can be run here.
        # Since this is a local personal assistant, we are allowing execution.
        result = subprocess.run(command, shell=True, capture_output=True, text=True, timeout=30)
        output = result.stdout if result.returncode == 0 else result.stderr
        return output.strip() if output else "Command executed successfully with no output."
    except subprocess.TimeoutExpired:
        return "Error: Command timed out."
    except Exception as e:
        return f"Error executing command: {str(e)}"

@tool
def desktop_click(x: int, y: int) -> str:
    """Simulates a mouse click at the given X, Y screen coordinates."""
    try:
        pyautogui.click(x=x, y=y)
        return f"Successfully clicked at ({x}, {y})."
    except Exception as e:
        return f"Error simulating click: {str(e)}"

@tool
def desktop_type(text: str) -> str:
    """Simulates typing text on the keyboard."""
    try:
        pyautogui.write(text, interval=0.05)
        return f"Successfully typed text."
    except Exception as e:
        return f"Error typing text: {str(e)}"

@tool
async def browse_web(url: str) -> str:
    """Navigates to a given URL using a headless browser and returns the text content of the page."""
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            await page.goto(url, wait_until="domcontentloaded", timeout=15000)
            
            # Simple extraction: just grab all text from body
            content = await page.evaluate("document.body.innerText")
            await browser.close()
            
            # Truncate if too long to avoid token limits
            return content[:4000] + ("..." if len(content) > 4000 else "")
    except Exception as e:
        return f"Error browsing web: {str(e)}"

# A list of all available tools for easy importing
all_jarvis_tools = [
    execute_shell_command,
    desktop_click,
    desktop_type,
    browse_web
]
