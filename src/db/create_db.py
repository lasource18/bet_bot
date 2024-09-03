import sqlite3
import os
from dotenv import load_dotenv

load_dotenv()

DB_FILE = os.environ['DB_FILE']

con = sqlite3.connect(database=DB_FILE)

cursor = con.cursor()

cursor.execute("""
    CREATE TABLE IF NOT EXISTS upcoming_games ( id INTEGER PRIMARY KEY, 
               game_id INTEGER UNIQUE NOT NULL, 
               game_date TEXT NOT NULL, 
               home_team TEXT NOT NULL, 
               away_team TEXT NOT NULL,
               season TEXT NOT NULL, 
               league_code TEXT NOT NULL, 
               league_name TEXT NOT NULL, 
               round TEXT NOT NULL,
               created_at DATETIME NOT NULL DEFAULT datetime(current_timestamp, 'localtime'),
               updated_at DATETIME NOT NULL DEFAULT datetime(current_timestamp, 'localtime')
               );
""")

cursor.execute("""
    CREATE TABLE IF NOT EXISTS match_ratings ( id INTEGER PRIMARY KEY, 
               game_id INTEGER UNIQUE NOT NULL,
               game_date TEXT NOT NULL, 
               home_team TEXT NOT NULL, 
               away_team TEXT NOT NULL,
               season TEXT NOT NULL, 
               league_code INTEGER NOT NULL, 
               league_name TEXT NOT NULL, 
               round INTEGER NOT NULL,
               fthg INTEGER NULL,
               ftag INTEGER NULL,
               ftr TEXT NULL,
               bookmaker TEXT NOT NULL,
               bookmaker_game_id TEXT NOT NULL,
               home_odds REAL NOT NULL,
               draw_odds REAL NOT NULL,
               away_odds REAL NOT NULL,
               home_proba REAL NOT NULL,
               draw_proba REAL NOT NULL,
               away_proba REAL NOT NULL,
               vig REAL NOT NULL,
               home_rating INTEGER NOT NULL,
               away_rating INTEGER NOT NULL,
               match_rating INTEGER NOT NULL,
               hwto REAL NOT NULL,
               dto REAL NOT NULL,
               awto REAL NOT NULL,
               hwtp REAL NOT NULL,
               dtp REAL NOT NULL,
               awtp REAL NOT NULL,
               hv REAL NOT NULL,
               dv REAL NOT NULL,
               av REAL NOT NULL,
               h REAL NOT NULL,
               d REAL NOT NULL,
               a REAL NOT NULL,
               bet TEXT NOT NULL,
               bet_odds REAL NOT NULL,
               value REAL NOT NULL,
               stake REAL NOT NULL,
               status TEXT NOT NULL,
               bankroll REAL NOT NULL,
               result TEXT NULL DEFAULT 'NB',
               gl REAL NULL,
               profit REAL NULL,
               yield REAL NULL,
               created_at DATETIME NOT NULL DEFAULT datetime(current_timestamp, 'localtime'),
               updated_at DATETIME NOT NULL DEFAULT datetime(current_timestamp, 'localtime')
               );
""")

con.commit()
con.close()