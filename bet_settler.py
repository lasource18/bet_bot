#!/usr/bin/python3

from logging import Logger
from datetime import datetime

from decimal import Decimal, getcontext
import time

import requests
from requests.exceptions import RetryError

from jproperties import Properties

from helpers import send_email
from helpers.bet_settler_args_parser import args_parser
from helpers.logger import setup_logger
from helpers.session import SessionManager
from utils.utils import API_KEY, LOGS, RAPIDAPI_HOST, SQL_PROPERTIES, CONFIG_FILE, delete_all, delete_some, execute_many, load_many, read_config

url = f"https://{RAPIDAPI_HOST}/v3/fixtures"

headers = {
	"x-rapidapi-key": API_KEY,
	"x-rapidapi-host": RAPIDAPI_HOST
}

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

def main(args):
    try:
        betting_strategy = args.betting_strategy.lower()

        config = read_config(CONFIG_FILE)
        leagues = config['leagues']
        strategies_list = config['strategies']

        if betting_strategy in strategies_list:
            getcontext.prec = 3

            today = datetime.now().strftime('%Y-%m-%d')

            logger = setup_logger('bet_settler', f"{LOGS}/{betting_strategy}/bet_settler/{config['season']}/{today}_bet_settler.log")

            logger.info(f'Starting bet_bot:bet_settler {betting_strategy}')

            select_from_match_ratings_query = configs.get('SELECT_FROM_MATCH_RATINGS').data
            update_match_ratings = configs.get('UPDATE_MATCH_RATINGS').data
            # delete_all_from_upcoming_games_query = configs.get('DELETE_ALL_FROM_UPCOMING_GAMES').data
            delete_some_from_upcoming_games_query = configs.get('DELETE_SOME_FROM_UPCOMING_GAMES').data
            
            updates = []
            session = SessionManager().get_session()

            subject = f'Bets results for {today} with {betting_strategy} strategy'
            messages = []

            total_wagered = 0
            total_earnings = 0

            bets = []

            for league, league_id in leagues.items():
                bets = load_many(select_from_match_ratings_query, league, today)
                bets = {bet['game_id']: bet for bet in bets}

                if len(bets) == 0:
                    messages.append(f"No bets for {league} on {today}.")
                    break

                bets_headlines = '\n'.join([f"{bet['home_team']} - {bet['away_team']}" for bet in bets.values()])

                messages.append(f"{league} games")
                messages.append(f"{'-' * (len(league)+6)}\n\n")

                logger.info(f"Bets for {league} on {today}: \n{bets_headlines}")
                results = fetch_today_games_results(session, league_id, today, config['season'], logger)

                wagered = 0
                earnings= 0

                time.sleep(1)

                for result in results:
                    fthg, ftag, ftr, game_id = result
                    bet = bets[game_id]
                    wagered += bet['stake']
                    gl = Decimal(bet['stake']) * Decimal(bet['bet_odds']) if ftr == bet['bet'] else -Decimal(bet['stake'])
                    gl = float(gl)
                    earnings += gl
                    profit = gl - bet['stake'] if gl > 0 else gl
                    profit = float(profit)
                    res =  'W' if gl > 0 else ('NB' if gl == 0 else 'L')
                    yield_ = Decimal(profit) / Decimal(bet['bankroll']) * 100
                    yield_ = float(yield_)
                    updates.append((fthg, ftag, ftr, res, gl, profit, yield_, game_id))
                    messages.append(f"Results for {bet['home_team']} - {bet['away_team']}: Score: {fthg}-{ftag} | My bet: {bet['bet']} | Odds: {bet['bet_odds']} | Bookmaker: {bet['bookmaker']} | Result: {res} | Stake: ${bet['stake']} | G/L: {gl} | Profit: {profit} | Yield: {yield_}%\n")
                    logger.info(f"Results for {bet['home_team']} - {bet['away_team']}: Score: {fthg}-{ftag} | My bet: {bet['bet']} | Odds: {bet['bet_odds']} | Bookmaker: {bet['bookmaker']} | Result: {res} | Stake: ${bet['stake']} | G/L: {gl} | Profit: {profit} | Yield: {yield_}%")
                
                if len(bets) > 0:
                    messages.append(f'Amount wagered for {league}: ${wagered}\n')
                    logger.info(f'Amount wagered for {league}: ${wagered}')
                    messages.append(f'Amount earned for {league}: ${earnings}\n')
                    logger.info(f'Amount earned for {league}: ${earnings}')
                    messages.append(f'Profit for {league}: ${earnings-wagered}\n')
                    logger.info(f'Profit for {league}: ${earnings-wagered}')

                    total_wagered += wagered
                    total_earnings += earnings

                    execute_many(update_match_ratings, updates)
                
                delete_some(delete_some_from_upcoming_games_query, (league, today))
            
            if len(bets) > 0:
                messages.append(f'Total amount wagered: ${total_wagered}\n')
                logger.info(f'Total amount wagered: ${total_wagered}')
                messages.append(f'Total amount earned: ${total_earnings}\n')
                logger.info(f'Total amount earned: ${total_earnings}')
                messages.append(f'Total profit: ${total_earnings-total_wagered}\n')
                logger.info(f'Total profit: ${total_earnings-total_wagered}')
                
            # delete_all(delete_all_from_upcoming_games_query)
            send_email(messages, subject)
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
    args = args_parser() 
    main(args)
