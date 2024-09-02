from logging import Logger
import sys
from datetime import datetime

from decimal import Decimal, getcontext
import time

import requests
from requests.exceptions import RetryError

from jproperties import Properties

from helpers.logger import setup_logger
from helpers.session import SessionManager
from utils.utils import API_KEY, LOGS, RAPIDAPI_HOST, SQL_PROPERTIES, CONFIG_FILE, delete_all, execute_many, load_many, read_config

url = f"https://{RAPIDAPI_HOST}/v3/fixtures"

headers = {
	"x-rapidapi-key": API_KEY,
	"x-rapidapi-host": RAPIDAPI_HOST
}

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

def main():
    try:
        args = sys.argv
        betting_strategy = args[1].lower()

        getcontext.prec = 3

        today = datetime.now().strftime('%Y-%m-%d')

        config = read_config(CONFIG_FILE)
        leagues = config['leagues']

        logger = setup_logger('bet_settler', f"{LOGS}/{betting_strategy}/{config['season']}/{today}_bet_settler.log")

        logger.info(f'Starting bet_bot:bet_settler: {args[0]} {args[1:]}')

        select_from_match_ratings_query = configs.get('SELECT_FROM_MATCH_RATINGS').data
        update_match_ratings = configs.get('UPDATE_MATCH_RATINGS').data
        delete_all_from_upcoming_games_query= configs.get('DELETE_ALL_FROM_UPCOMING_GAMES').data
        
        updates = []
        session = SessionManager().get_session()

        for league, league_id in leagues.items():
            bets = load_many(select_from_match_ratings_query, league, today)
            bets = {bet['game_id']: bet for bet in bets}

            logger.info(f"Bets for {league} on {today}: {bets}")
            results = fetch_today_games_results(session, league_id, today, config['season'], logger)

            time.sleep(1)

            for result in results:
                fthg, ftag, ftr, game_id = result
                bet = bets[game_id]
                gl = Decimal(bet['stake']) * Decimal(bet['bet_odds']) if ftr == bet['bet'] else -Decimal(bet['stake'])
                gl = float(gl)
                profit = gl - bet['stake'] if gl > 0 else gl
                profit = float(profit)
                res =  'W' if gl > 0 else 'L'
                rtn = Decimal(profit) / Decimal(bet['bankroll']) - 1
                rtn = float(rtn)
                updates.append((fthg, ftag, ftr, res, gl, profit, rtn, game_id))
                logger.info(f"Results for {bet['home_team']} - {bet['away_team']}: Score: {fthg}-{ftag} | My bet: {bet['bet']} | G/L: {gl} | Profit: {profit} | Return: {rtn}")
            
            execute_many(update_match_ratings, updates)
        delete_all(delete_all_from_upcoming_games_query)
    except Exception as e:
        logger.error(e)

def fetch_today_games_results(session: requests.Session, league, date, season, logger: Logger):
    try:
        params = {"league":league,"season":season.split('-')[0],"date": date,"timezone":"America/New_York"}

        response = session.get(url, headers=headers, params=params)

        # print(response.json())

        data = response.json()

        fixtures = [
            (
                int(fixture['goals']['home']),
                int(fixture['goals']['away']),
                'H' if int(fixture['goals']['home']) > int(fixture['goals']['away']) 
                else ('A' if int(fixture['goals']['home']) < int(fixture['goals']['away']) else 'D'),
                fixture['fixture']['id'],
            ) for fixture in data['response']
        ]
    except requests.HTTPError as http_err:
        logger.error(f"Login failed | HTTP error occurred: {http_err}")
        return []
    except RetryError as err:
        logger.error(f"Login failed | Retry Error: {err}")
        return []
    except Exception as err:
        logger.error(f"fetch_today_games_results(): Other error occurred: {err}")
        return []
    else:
        logger.info(f"Games to settle: {fixtures}")
        return fixtures

if __name__ == '__main__':
    main()