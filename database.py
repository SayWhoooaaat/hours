# database.py
import sqlite3
from datetime import datetime

class Database:
    def __init__(self, db_path='data/work_hours.db'):
        self.conn = sqlite3.connect(db_path)
        self.create_tables()

    def create_tables(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS work_entries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT NOT NULL,
                check_in TEXT,
                check_out TEXT,
                type TEXT NOT NULL,
                hours REAL NOT NULL
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()

    def add_entry(self, date, check_in, check_out, entry_type, hours):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO work_entries (date, check_in, check_out, type, hours)
            VALUES (?, ?, ?, ?, ?)
        ''', (date, check_in, check_out, entry_type, hours))
        self.conn.commit()

    def get_entries(self, start_date, end_date):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM work_entries
            WHERE date BETWEEN ? AND ?
        ''', (start_date, end_date))
        return cursor.fetchall()

    def set_setting(self, key, value):
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
        ''', (key, value))
        self.conn.commit()

    def get_setting(self, key):
        cursor = self.conn.cursor()
        cursor.execute('SELECT value FROM settings WHERE key = ?', (key,))
        result = cursor.fetchone()
        return result[0] if result else None

    def close(self):
        self.conn.close()
