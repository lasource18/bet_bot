import json
import os
import time
import csv
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal, getcontext

import requests
from requests.exceptions import RetryError

import uuid

import pandas as pd

from dotenv import load_dotenv
from jproperties import Properties

import db.db_utils as db

load_dotenv(override=True)

API_KEY = os.environ['X-RAPIDAPI-KEY']
RAPIDAPI_HOST = os.environ["RAPIDAPI_HOST"]
DB_FILE = os.environ["DB_FILE"]
SQL_PROPERTIES = os.environ["SQL_PROPERTIES"]
CONFIG_FILE = os.environ["CONFIG_FILE"]
LOGS = os.environ["LOGS"]

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

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
    with open(file_path, 'r') as f:
        config = json.load(file_path)
    return config

def update_config(obj: dict, file_path: str):
    with open(file_path, 'w') as f:
        json.dump(obj, f)

def create_dir(directory_path: str):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)
        print(f"Directory '{directory_path}' created.")
    else:
        print(f"Directory '{directory_path}' already exists.")

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
    try:
        date = date

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

    except requests.HTTPError as http_err:
        print(f"Login failed | HTTP error occurred: {http_err}")
        return []
    except RetryError as err:
        print(f"Login failed | Retry Error: {err}")
        return []
    except Exception as err:
        print(f"fetch_today_games_results(): Other error occurred: {err.with_traceback()}")
        return []
    else:
        execute_many(fixtures)

def load_many(q, *args):
    db.load_many(q, args)

def execute_many(q, data):
    db.execute_many(q, data)

def delete_some(q, data):
    db.execute(q, data)

def delete_all(q):
    db.execute(q)