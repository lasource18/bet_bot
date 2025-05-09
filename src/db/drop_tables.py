import sqlite3
import os
from dotenv import load_dotenv

load_dotenv(override=True)

DB_FILE = os.environ['DB_FILE']

con = sqlite3.connect(DB_FILE)
cursor = con.cursor()

cursor.execute("""
               DROP TABLE IF EXISTS upcoming_games;
               """)

cursor.execute("""
               DROP TABLE IF EXISTS match_ratings;
               """)

con.commit()
con.close()