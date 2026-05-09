from langchain_core.tools import tool
from memory.vector_db import memory_db
from memory.sqlite_db import update_topic_mastery, get_topic_mastery
import json

@tool
def save_study_notes(topic: str, content: str) -> str:
    """Saves study notes or learning material to semantic memory for later retrieval."""
    memory_db.add_learning_content(content, metadata={"topic": topic})
    return f"Saved notes for topic: {topic}"

@tool
def generate_quiz(topic: str, num_questions: int = 3) -> str:
    """Retrieves learning material and generates a quiz."""
    # Retrieve context from semantic memory
    context = memory_db.search_learning_content(topic, top_k=5)
    
    # In a real setup, we would call the LLM here to generate a quiz based on `context`.
    # For now, returning a simulated response.
    if not context:
        return f"I don't have enough material on '{topic}' to generate a quiz. Please provide some study notes first."
    
    return f"Generated {num_questions} questions on '{topic}' based on your notes:\n1. What is the core concept of {topic}?\n2. Can you explain a use case for {topic}?\n3. What are the main challenges with {topic}?"

@tool
def record_quiz_score(topic: str, score: int, total: int) -> str:
    """Records the score of a quiz and updates the mastery level for the topic."""
    new_mastery = update_topic_mastery(topic, score, total)
    return f"Recorded score {score}/{total} for '{topic}'. New mastery level: {new_mastery}%."

@tool
def get_study_status(topic: str) -> str:
    """Gets the current mastery level for a topic."""
    mastery = get_topic_mastery(topic)
    return f"Current mastery level for '{topic}' is {mastery}%."

learning_tools = [
    save_study_notes,
    generate_quiz,
    record_quiz_score,
    get_study_status
]
