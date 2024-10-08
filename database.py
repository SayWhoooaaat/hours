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
                hours REAL NOT NULL,
                lunch_break BOOLEAN NOT NULL DEFAULT 1
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        self.conn.commit()

    def add_entry(self, date, check_in, check_out, entry_type, hours, lunch_break):
        self.resolve_overlaps(date, check_in, check_out)
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO work_entries (date, check_in, check_out, type, hours, lunch_break)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (date, check_in, check_out, entry_type, hours, lunch_break))
        self.conn.commit()

    def get_entries(self, start_date, end_date):
        cursor = self.conn.cursor()
        cursor.execute('''
            SELECT * FROM work_entries
            WHERE date BETWEEN ? AND ?
        ''', (start_date, end_date))
        return cursor.fetchall()

    def get_entry(self, date, check_in):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT * FROM work_entries
            WHERE date = ? AND check_in = ?
        """, (date, check_in))
        return cursor.fetchone()

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

    def update_entry(self, old_date, old_check_in, old_check_out, new_date, new_check_in, new_check_out, new_type, new_hours, new_lunch_break):
        if new_check_in and new_check_out:
            self.resolve_overlaps(new_date, new_check_in, new_check_out, exclude=(old_date, old_check_in, old_check_out))
        cursor = self.conn.cursor()
        cursor.execute("""
            UPDATE work_entries
            SET date = ?, check_in = ?, check_out = ?, type = ?, hours = ?, lunch_break = ?
            WHERE date = ? AND check_in = ? AND check_out = ?
        """, (new_date, new_check_in, new_check_out, new_type, new_hours, new_lunch_break, old_date, old_check_in, old_check_out))
        self.conn.commit()

    def delete_entry(self, date, check_in, check_out):
        cursor = self.conn.cursor()
        print("database is told to delete")
        cursor.execute("""
            DELETE FROM work_entries
            WHERE date = ? AND check_in = ? AND check_out = ?
        """, (date, check_in, check_out))
        self.conn.commit()

    def resolve_overlaps(self, date, new_check_in, new_check_out, exclude=None):
        cursor = self.conn.cursor()
        cursor.execute("""
            SELECT date, check_in, check_out, hours, type, lunch_break FROM work_entries 
            WHERE date = ?
            ORDER BY check_in
        """, (date,))
        entries = cursor.fetchall()

        new_start = datetime.strptime(new_check_in, "%H:%M")
        new_end = datetime.strptime(new_check_out, "%H:%M")

        for entry_date, check_in, check_out, hours, entry_type, lunch_break in entries:
            if exclude and (entry_date, check_in, check_out) == exclude:
                continue

            start = datetime.strptime(check_in, "%H:%M")
            end = datetime.strptime(check_out, "%H:%M")

            if new_start < end and new_end > start:
                if new_start <= start and new_end >= end:
                    # Complete overlap, delete the existing entry
                    self.delete_entry(entry_date, check_in, check_out)
                elif new_start > start and new_end < end:
                    # New entry is inside existing entry, split the existing entry
                    self.update_entry(entry_date, check_in, check_out, 
                                    entry_date, check_in, new_start.strftime("%H:%M"), 
                                    entry_type, (new_start - start).seconds / 3600, lunch_break)
                    self.add_entry(entry_date, new_end.strftime("%H:%M"), check_out, entry_type, 
                                (end - new_end).seconds / 3600, lunch_break)
                elif new_start <= start:
                    # Overlap at the start
                    self.update_entry(entry_date, check_in, check_out,
                                    entry_date, new_end.strftime("%H:%M"), check_out,
                                    entry_type, (end - new_end).seconds / 3600, lunch_break)
                elif new_end >= end:
                    # Overlap at the end
                    self.update_entry(entry_date, check_in, check_out,
                                    entry_date, check_in, new_start.strftime("%H:%M"),
                                    entry_type, (new_start - start).seconds / 3600, lunch_break)
                    

