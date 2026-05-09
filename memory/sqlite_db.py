import sqlite3
import os

DB_PATH = "./learning_tracking.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Table for tracking topics and mastery
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS topics (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT UNIQUE,
        mastery_level INTEGER DEFAULT 0, -- 0 to 100
        last_reviewed DATE
    )
    """)
    
    # Table for tracking quiz scores
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS quiz_scores (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        topic_id INTEGER,
        score INTEGER,
        total_questions INTEGER,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY(topic_id) REFERENCES topics(id)
    )
    """)
    
    conn.commit()
    conn.close()

def update_topic_mastery(topic_name: str, new_score: int, total: int):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Ensure topic exists
    cursor.execute("INSERT OR IGNORE INTO topics (name) VALUES (?)", (topic_name,))
    cursor.execute("SELECT id, mastery_level FROM topics WHERE name = ?", (topic_name,))
    topic_id, current_mastery = cursor.fetchone()
    
    # Record the quiz
    cursor.execute("INSERT INTO quiz_scores (topic_id, score, total_questions) VALUES (?, ?, ?)", 
                   (topic_id, new_score, total))
    
    # Simple mastery calculation (weighted average, just an example)
    percentage = int((new_score / total) * 100)
    new_mastery = int((current_mastery * 0.7) + (percentage * 0.3)) if current_mastery > 0 else percentage
    
    cursor.execute("UPDATE topics SET mastery_level = ?, last_reviewed = CURRENT_DATE WHERE id = ?", 
                   (new_mastery, topic_id))
    
    conn.commit()
    conn.close()
    
    return new_mastery

def get_topic_mastery(topic_name: str):
    init_db()
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT mastery_level FROM topics WHERE name = ?", (topic_name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0

# Initialize the db on import
init_db()
