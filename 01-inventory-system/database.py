import sqlite3

def connect():
    return sqlite3.connect("inventory.db")

def create_table():
    conn = connect()
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS inventory (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            location TEXT,
            last_updated TEXT
        )
    """)
    conn.commit()
    conn.close()
