import json
import os
import csv
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal, getcontext

import dateutil
import requests
from requests.exceptions import RetryError

import uuid

import pandas as pd
import matplotlib.pyplot as plt

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
REPORTS_DIR = os.environ["REPORTS_DIR"]
CREDENTIALS_FILE = os.environ['CREDENTIALS_FILE']
HIST_DATA_PATH = os.environ['HIST_DATA_PATH']
BETTING_CRAWLER_PATH = os.environ['BETTING_CRAWLER_PATH']

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
        config = json.load(f)
    return config

def update_config(obj: dict, file_path: str):
    with open(file_path, 'w') as f:
        json.dump(obj, f)

def create_dir(path: str):
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Directory '{path}' created.")
    else:
        print(f"Directory '{path}' already exists.")

def get_files_list(path):
    if not os.path.exists(path):
        return None
    
    files = []
    for root, dirs, files in os.walk(path, topdown=False):
        # Iterate over the files in current root
        for file_entry in files:
            # create the relative path to the file
            files.append(os.path.join(root, file_entry))
    return files

def record_bankroll(starting_bk: float, bk: float, file_path: str, date: datetime):
    with open(file_path, 'a') as file:
        writer = csv.DictWriter(file, fieldnames=['date', 'bankroll'])

        if not os.path.isfile(file_path):
            writer.writeheader()
            writer.writerow({'date': (date-timedelta(1)).strftime('%Y-%m-%d'), 'bankroll': starting_bk})

        writer.writerow({'date': date.strftime('%Y-%m-%d'), 'bankroll': bk})

def read_csv_file(file_path: str):
    df = pd.read_csv_file(file_path, header=0)
    return df

def generate_chart(csv_file, output_file, **kwargs):
    league = kwargs.get('league', '')
    season = kwargs.get('season', '')
    # Load the CSV file into a DataFrame
    df = read_csv_file(csv_file)

    # Ensure the date column is parsed as a datetime
    df['date'] = pd.to_datetime(df['date'])

    # Plot the data
    plt.figure(figsize=(10, 6))
    plt.plot(df['date'], df['data'], marker='o')

    # Set plot labels and title
    plt.xlabel('Date')
    plt.ylabel('Bankroll')
    plt.title(f'{league} Bankroll evolution for {season}')

    # Save the plot as a PNG file
    plt.savefig(output_file)

    # Close the plot to prevent it from displaying
    plt.close()

def fetch_upcoming_games(league, date, season):
    try:
        fixtures = []
        insert_into_upcoming_games = configs.get('INSERT_INTO_UPCOMING_GAMES').data

        params = {"league":league,"season":season.split('-')[0],"date": date,"timezone":"America/New_York"}
        response = requests.get(url, headers=headers, params=params)

        # print(response.json())

        data = response.json()

        fixtures = [
            (fixture['fixture']['id'],
            dateutil.parser.parse(fixture['fixture']['date']).strftime('%Y-%m-%d'), 
            fixture['teams']['home']['name'],
            fixture['teams']['away']['name'],
            fixture['league']['name'],
            fixture['league']['round'].split(" - ")[-1],
            ) for fixture in data['response']
        ]

    except requests.HTTPError as http_err:
        print(f"Login failed | HTTP error occurred: {http_err}")
    except RetryError as retry_err:
        print(f"Login failed | Retry Error: {retry_err}")
    except Exception as err:
        print(f"fetch_today_games_results(): Other error occurred: {err}")
    else:
        if len(fixtures) > 0:
            execute_many(insert_into_upcoming_games, fixtures)
            return True

def load_one(q, *args):
    return db.load_one(q, args)

def load_many(q, *args):
    return db.load_many(q, args)

def execute_many(q, data):
    db.execute_many(q, data)

def delete_some(q, data):
    db.execute(q, data)

def delete_all(q):
    db.execute(q)
