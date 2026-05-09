import time
import threading
import pygetwindow as gw
import sqlite3
import os

DB_PATH = "./learning_tracking.db"

def init_monitor_db():
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS activity_log (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        window_title TEXT,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    )
    """)
    conn.commit()
    conn.close()

class ActivityMonitor:
    def __init__(self, interval_seconds=60):
        self.interval = interval_seconds
        self.running = False
        self.thread = None
        init_monitor_db()

    def _monitor_loop(self):
        while self.running:
            try:
                active_window = gw.getActiveWindow()
                if active_window and active_window.title:
                    self._log_activity(active_window.title)
            except Exception as e:
                print(f"Error monitoring activity: {e}")
            time.sleep(self.interval)

    def _log_activity(self, title):
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO activity_log (window_title) VALUES (?)", (title,))
        conn.commit()
        conn.close()

    def start(self):
        if not self.running:
            self.running = True
            self.thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self.thread.start()

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()

# Global monitor instance
activity_monitor = ActivityMonitor()
