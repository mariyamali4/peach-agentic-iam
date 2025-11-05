import sqlite3
import uuid
from pathlib import Path

BASE_DIR = Path(r"D:\lums-python-programming\thesis\project")
DB_PATH = BASE_DIR / "data" / "history" / "conv_history.db"

# --- Initialize database once ---
def init_db():
    '''
    Initialize the conversation history database and create the table if it doesn't exist.
    Output: None
    '''
    try:
        with sqlite3.connect(DB_PATH) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS conversation_history (
                    conv_id TEXT,
                    turn_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    mode TEXT CHECK(mode IN ('rag', 'scenario_editor')),
                    query TEXT NOT NULL,
                    response TEXT,
                    output_file_name TEXT,
                    timestamp TEXT
                )
            """)
        print("✅ Conversation history database initialized.")
    except Exception as e:
        print("❌ Error initializing database:", e)


def log_turn(conv_id, mode, timestamp, query, response, output_file_name=None):
    ''' 
    Log a single turn in the conversation history.
    Inputs:
    - conv_id (str): Unique conversation ID
    - mode (str): 'rag' or 'scenario_editor'
    - query (str): User's question or instruction
    - response (str): Assistant's response
    - output_file_name (str, optional): For Excel mode, the name of the output file
    - timestamp (str): ISO formatted timestamp
    Output: None
    '''
    with sqlite3.connect(DB_PATH) as conn:
        conn.execute("""
            INSERT INTO conversation_history
            (conv_id, mode, query, response, output_file_name, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (conv_id, mode, query, response, output_file_name, timestamp))
    conn.close()


def get_conversation(conv_id):
    '''
    Retrieve chat history for a given conversation ID.
    Input: conv_id (str)
    Output: List of tuples (turn_id, mode, query, response, output_file_name, timestamp)
    '''
    with sqlite3.connect(DB_PATH) as conn:
        rows = conn.execute("""
            SELECT turn_id, mode, query, response, output_file_name, timestamp
            FROM conversation_history
            WHERE conv_id = ?
           -- ORDER BY turn_id ASC
        """, (conv_id,)).fetchall()
    return rows


def new_conversation():
    '''
    Create a new unique conversation ID for each session.
    Output: conv_id (str) - first 13 characters/2 chunks of a UUID
    '''
    conv_id = str(uuid.uuid4())[:13]  # 
    return conv_id
