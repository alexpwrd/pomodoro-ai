import sqlite3
import threading
import os

class ConversationDatabase:
    def __init__(self, db_file='conversation_history.db'):
        self.db_file = os.path.abspath(db_file)
        print(f"Database file path: {self.db_file}")
        self.lock = threading.Lock()
        self.local = threading.local()

    def get_connection(self):
        if not hasattr(self.local, 'conn'):
            self.local.conn = sqlite3.connect(self.db_file)
        return self.local.conn

    def create_table(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations
            (id INTEGER PRIMARY KEY, role TEXT, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)
            ''')
            conn.commit()

    def add_message(self, role, content):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('INSERT INTO conversations (role, content) VALUES (?, ?)', (role, content))
            conn.commit()

    def get_conversation_history(self, limit=500):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('SELECT role, content FROM conversations ORDER BY timestamp DESC LIMIT ?', (limit,))
            return cursor.fetchall()

    def clear_history(self):
        with self.lock:
            conn = self.get_connection()
            cursor = conn.cursor()
            cursor.execute('DELETE FROM conversations')
            conn.commit()

    def close(self):
        if hasattr(self.local, 'conn'):
            self.local.conn.close()
            del self.local.conn
