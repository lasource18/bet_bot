import json
import os
import requests
import time
import csv
from datetime import datetime, timedelta
import uuid

from decimal import ROUND_DOWN, Decimal, getcontext

import pandas as pd

from dotenv import load_dotenv
from jproperties import Properties

from db.db_utils import execute_many, load_many, load_one

load_dotenv(override=True)

API_KEY = os.environ['X-RAPIDAPI-KEY']
RAPIDAPI_HOST = os.environ["RAPIDAPI_HOST"]
DB_FILE = os.environ["DB_FILE"]
SQL_PROPERTIES = os.environ["SQL_PROPERTIES"]

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

MATCH_RATINGS_PATTERN = '[Mm]atch(_?)[Rr]ating(s?)'

url = f"https://{RAPIDAPI_HOST}/v3/fixtures"

headers = {
	"x-rapidapi-key": API_KEY,
	"x-rapidapi-host": RAPIDAPI_HOST
}

def american_to_decimal(american_odds):
    getcontext().prec = 4
    getcontext().rounding = ROUND_DOWN
    if american_odds == 0:
        return 1.0
    if american_odds > 0:
        return (Decimal(american_odds) / Decimal(100)) + 1
    else:
        return (Decimal(100) / Decimal(abs(american_odds))) + 1

def decimal_to_american(decimal_odds):
    if decimal_odds == 1.0:
        return 0
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

def generate_uuid():
    return str(uuid.uuid4())

def calculate_vig(*args):
    commission = 1 - 1 / sum(args)
    return commission if 1 - 1 / sum(args) > 0 else 0

def read_config(file_path: str):
    return json.load(file_path)

def update_config(obj: dict, file_path: str):
    json.dump(obj, file_path)

def record_bankroll(starting_bk: float, bk: float, file_path: str, date: datetime):
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a') as file:
        writer = csv.DictWriter(file, fieldnames=['date', 'bankroll'])

        if not file_exists:
            writer.writeheader()
            writer.writerow({'date': (date-timedelta(1)).strftime('%Y-%m-%d'), 'bankroll': starting_bk})

        writer.writerow({'date': date.strftime('%Y-%m-%d'), 'bankroll': bk})

def fetch_hist_data(file_path: str):
    df = pd.read_csv(file_path, header=0)
    return df

def fetch_upcoming_games(league, date, season):
    date = date.strftime('%Y-%m-%d')

    params = {"league":league,"season":season.split('-')[0],"date": date,"timezone":"America/New_York"}

    response = requests.get(url, headers=headers, params=params)

    # print(response.json())

    data = response.json()

    fixtures = [
        (
            fixture['fixture']['id'],
            fixture['fixture']['date'], 
            fixture['fixture']['teams']['home']['name'],
            fixture['fixture']['teams']['away']['name'],
            season,
            fixture['fixture']['league']['name'],
            fixture['fixture']['league']['round'].split(" - ")[-1],
        ) for fixture in data['response']
    ]

    q = configs.get('INSERT_INTO_UPCOMING_GAMES').data
    execute_many(q, fixtures)

def load_upcoming_games(*args):
    q = configs.get('SELECT_TEAMS_FROM_UPCOMING_GAMES').data
    load_many(q, args)

def insert_new_bets(bets):
    q = configs.get('INSERT_INTO_BETS')
    execute_many(q, bets)

def settle_bets(date, league):
    q = configs.get('SELECT_BETS_TO_SETTLE_FROM_BETS').data
    pass

