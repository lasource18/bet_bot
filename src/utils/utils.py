import json
from logging import Logger
import os
import sys
import csv
from datetime import datetime, timedelta
from decimal import ROUND_DOWN, Decimal, getcontext
from typing import Dict, List

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

API_KEY = os.environ['X_RAPIDAPI_KEY']
RAPIDAPI_HOST = os.environ["RAPIDAPI_HOST"]
DB_FILE = os.environ["DB_FILE"]
SQL_PROPERTIES = os.environ["SQL_PROPERTIES"]
CONFIG_FILE = os.environ["CONFIG_FILE"]
MAPPINGS_FILE = os.environ["MAPPINGS_FILE"]
LOGS = os.environ["LOGS"]
REPORTS_DIR = os.environ["REPORTS_DIR"]
RESPONSES_DIR = os.environ["RESPONSES_DIR"]
BANKROLL_DIR = os.environ["BANKROLL_DIR"]
CREDENTIALS_FILE = os.environ['CREDENTIALS_FILE']
HIST_DATA_PATH = os.environ['HIST_DATA_PATH']
BETTING_CRAWLER_PATH = os.environ['BETTING_CRAWLER_PATH']
DEVICE_UUID = os.environ['DEVICE_UUID']

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

headers = {
	"x-rapidapi-key": API_KEY,
	"x-rapidapi-host": RAPIDAPI_HOST
}

getcontext().prec = 4
getcontext().rounding = ROUND_DOWN

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
    getcontext().prec = 4

    if decimal_odds == 1.0:
        return 0
    if decimal_odds >= 2.0:
        return int((decimal_odds - 1) * 100)
    else:
        return int(-100 / (decimal_odds - 1))

def generate_uuid():
    return str(uuid.uuid4())

def calculate_vig(*args):
    getcontext().prec = 4
    commission = float(Decimal(1) - (Decimal(1) / Decimal(sum(args))))
    return commission if commission > 0 else 0.

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
    file_exists = os.path.isfile(file_path)
    with open(file_path, 'a') as file:
        writer = csv.DictWriter(file, fieldnames=['date', 'bankroll'])

        if not file_exists:
            writer.writeheader()    
            writer.writerow({'date': (date-timedelta(1)).strftime('%Y-%m-%d'), 'bankroll': starting_bk})

        writer.writerow({'date': date.strftime('%Y-%m-%d'), 'bankroll': bk})

def read_csv_file(file_path: str):
    df = pd.read_csv(file_path)
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
    plt.plot(df['date'], df['bankroll'], marker='o')

    # Set plot labels and title
    plt.xlabel('Date')
    plt.ylabel('Bankroll')
    plt.title(f'{league} Bankroll evolution for {season}')

    # Save the plot as a PNG file
    plt.savefig(output_file)

    # Close the plot to prevent it from displaying
    plt.close()

def fetch_upcoming_games(league: str, league_code: str, date: datetime, season: str, logger: Logger):
    try:
        def fetch_teams_rank():
            try:
                url = f"https://{RAPIDAPI_HOST}/v3/standings"
                params = {"league":league,"season":season.split('-')[0]}
                res = requests.get(url, headers=headers, params=params)

                data = res.json()

                res.raise_for_status()

                teams: List[dict] = data['response'][0]['league']['standings'][0]
                teams_rank: Dict[str, str] = {team['team']['name']: team['rank'] for team in teams}
            except requests.HTTPError as http_err:
                logger.error(f"fetch_teams_rank failed | HTTP error occurred: {http_err}")
            except RetryError as retry_err:
                logger.error(f"fetch_teams_rank failed | Retry Error: {retry_err}")
            except Exception as err:
                logger.error(f"fetch_teams_rank(): Other error occurred: {err}")
            else:
                return teams_rank
            
        teams_rank = fetch_teams_rank()
        fixtures = []
        insert_into_upcoming_games = configs.get('INSERT_INTO_UPCOMING_GAMES').data.replace('\"', '')
        check_upcoming_games = configs.get('CHECK_UPCOMING_GAMES').data.replace('\"', '')
        upcoming_games_ids = load_many(check_upcoming_games, date, league_code)
        upcoming_games_ids = [game_id[0] for game_id in upcoming_games_ids] if upcoming_games_ids else []

        url = f"https://{RAPIDAPI_HOST}/v3/fixtures"
        params = {"league":league,"season":season.split('-')[0],"date": date,"timezone":"America/New_York"}
        response = requests.get(url, headers=headers, params=params)

        # print(response.json())

        data = response.json()

        response.raise_for_status()

        fixtures = [
            (fixture['fixture']['id'],
            dateutil.parser.parse(fixture['fixture']['date']).strftime('%Y-%m-%d'), 
            fixture['teams']['home']['name'],
            fixture['teams']['away']['name'],
            season,
            league_code,
            fixture['league']['name'],
            fixture['league']['round'].split(" - ")[-1],
            teams_rank[fixture['teams']['home']['name']],
            teams_rank[fixture['teams']['away']['name']]
            ) for fixture in data['response'] if int(fixture['fixture']['id']) not in upcoming_games_ids
        ]

        if len(fixtures) > 0:
            execute_many(insert_into_upcoming_games, fixtures)

    except requests.HTTPError as http_err:
        logger.error(f"fetch_upcoming_games failed | HTTP error occurred: {http_err}")
    except RetryError as retry_err:
        logger.error(f"fetch_upcoming_games failed | Retry Error: {retry_err}")
    except Exception as err:
        e_type, e_object, e_traceback = sys.exc_info()
        e_filename = os.path.split(
            e_traceback.tb_frame.f_code.co_filename
        )[1]
        e_line_number = e_traceback.tb_lineno
        logger.error(f'fetch_upcoming_games(): {err}, type: {e_type}, filename: {e_filename}, line: {e_line_number}')
    else:
        return True
        
def map_from_rapidapi_to_bookmaker(home, away, league, bookmaker):
    config_ = read_config(MAPPINGS_FILE)
    values = config_.get(f'rapidapi_to_{bookmaker}', {}).get(league, {})

    if not values:
        raise ValueError('League values are is missing from mappings file.')
    
    return values.get(home, home), values.get(away, away)

def map_from_rapidapi_to_hist_data(home, away, league):
    config_ = read_config(MAPPINGS_FILE)
    values: dict = config_.get(f'rapidapi_to_hist_data').get(league, {})

    if not values:
        raise ValueError('League values are is missing from mappings file.')
    
    return values.get(home, home), values.get(away, away)

def load_one(q, *args):
    return db.load_one(q, *args)

def load_many(q, *args):
    return db.load_many(q, *args)

def execute(q, data):
    db.execute(q, data)

def execute_many(q, data):
    db.execute_many(q, data)

def delete_some(q, data):
    db.execute(q, data)

def delete_all(q):
    db.execute(q)
