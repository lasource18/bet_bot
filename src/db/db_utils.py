import sqlite3
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DB_FILE = os.environ['DB_FILE']

def load_one(query, *args):
    with sqlite3.connect(DB_FILE) as con:
        con.row_factory = sqlite3.Row
        cursor = con.cursor()
        cursor.execute(query, args)
        row = cursor.fetchone()
    return row

def load_many(query, *args):
    with sqlite3.connect(DB_FILE) as con:
        con.row_factory = sqlite3.Row
        cursor = con.cursor()
        cursor.execute(query, args)
        rows = cursor.fetchall()
    return rows

def execute(query, data=None):
    with sqlite3.connect(DB_FILE) as con:
        cursor = con.cursor()
        if data:
            cursor.execute(query, data)
        else:
            cursor.execute(query)
        con.commit()

def execute_many(query, data):
    with sqlite3.connect(DB_FILE) as con:
        cursor = con.cursor()
        cursor.executemany(query, data)
        con.commit()