#!/usr/bin/python3

from logging import Logger
from datetime import datetime

from decimal import Decimal, getcontext
import time

import requests
from requests.exceptions import RetryError

from jproperties import Properties

from helpers.send_email import send_email
from helpers.bet_settler_args_parser import args_parser
from helpers.logger import setup_logger
from helpers.session import SessionManager
from strategies.strategy_factory import StrategyFactory
from utils.utils import *

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
        strategies_list = config.get('strategies', [])
        leagues = config.get('leagues', {})
        season = config.get('season', '2024-2025')

        if betting_strategy in strategies_list:
            getcontext().prec = 3

            today = datetime.now().strftime('%Y-%m-%d')

            log_path = f"{LOGS}/{betting_strategy}/bet_settler/{season}"
            create_dir(log_path)
            logger = setup_logger('bet_settler', f'{log_path}/{today}_bet_settler.log')

            logger.info(f'Starting bet_bot:bet_settler {betting_strategy}')

            select_from_match_ratings_query = configs.get('SELECT_FROM_MATCH_RATINGS').data.replace('\"', '')
            update_match_ratings = configs.get('UPDATE_MATCH_RATINGS').data.replace('\"', '')
            # delete_all_from_upcoming_games_query = configs.get('DELETE_ALL_FROM_UPCOMING_GAMES').data.replace('\"', '')
            delete_old_games_from_upcoming_games_query = configs.get('DELETE_OLD_GAMES_FROM_UPCOMING_GAMES').data.replace('\"', '')
            delete_some_from_upcoming_games_query = configs.get('DELETE_SOME_FROM_UPCOMING_GAMES').data.replace('\"', '')
            strategy_factory = StrategyFactory()

            config_path = strategy_factory.get_config(betting_strategy)
            strat_config = read_config(config_path)
            
            updates = []
            session = SessionManager().get_session()

            subject = f'Bets results for {today} with {betting_strategy} strategy'
            messages = []

            total_wagered = 0
            total_earnings = 0

            bets = []

            for league, league_id in leagues.items():
                league_name = strat_config[league]['name']

                bets = load_many(select_from_match_ratings_query, league, today)

                if len(bets) == 0:
                    messages.append(f"No bets for {league_name}\n")
                    logger.warning(f"No bets for {league_name}")
                    continue

                delete_some(delete_old_games_from_upcoming_games_query, (today,))

                bets = {bet['game_id']: bet for bet in bets}
                
                starting_bk = strat_config[league]['bankroll']

                messages.append(f"{league_name} starting bankroll: {starting_bk}\n\n")

                logger.info(f"Starting bankroll for {league_name}: ${starting_bk}")
                consolidated_starting += starting_bk

                bets_headlines = '\n'.join([f"{bet['home_team']} - {bet['away_team']}" for bet in bets.values()])

                messages.append(f"{league_name} games")
                messages.append(f"{'-' * (len(league_name)+6)}\n\n")

                logger.info(f"Bets for {league_name} on {today}: \n{bets_headlines}")
                results = fetch_today_games_results(session, league_id, today, season, bets.keys(), logger)

                if len(bets) != len(results):
                    messages.append(f'Results length does not match bets length for {league}\n')
                    logger.warning(f'Results length does not match bets length for {league}')
                    continue

                wagered = 0
                earnings= 0

                time.sleep(1)

                for result in results:
                    fthg, ftag, ftr, game_id = result

                    bet = bets.get(game_id, {})

                    if not bet:
                        messages.append(f'Game with id={game_id} is not found in bets table for {league}\n')
                        logger.warning(f'Game with id={game_id} is not found in bets table for {league}')
                        continue
                        
                    wagered += bet['stake']

                    gl = Decimal(bet['stake']) * Decimal(bet['bet_odds']) if ftr == bet['bet'] else -Decimal(bet['stake'])
                    gl = float(gl)
                    earnings += gl

                    profit = gl - bet['stake'] if gl > 0 else gl

                    res =  'W' if gl > 0 else ('NB' if gl == 0 else 'L')
                    
                    yield_ = Decimal(profit) / Decimal(bet['bankroll']) * 100
                    yield_ = float(yield_)

                    updates.append((fthg, ftag, ftr, res, gl, profit, yield_, game_id))
                    messages.append(f"Results for {bet['home_team']} - {bet['away_team']}: Score: {fthg}-{ftag} | My bet: {bet['bet']} | Odds: {bet['bet_odds']} | Bookmaker: {bet['bookmaker']} | Result: {res} | Stake: ${bet['stake']} | G/L: {gl} | Profit: {profit} | Yield: {yield_}%\n")
                    logger.info(f"Results for {bet['home_team']} - {bet['away_team']}: Score: {fthg}-{ftag} | My bet: {bet['bet']} | Odds: {bet['bet_odds']} | Bookmaker: {bet['bookmaker']} | Result: {res} | Stake: ${bet['stake']} | G/L: {gl} | Profit: {profit} | Yield: {yield_}%")

                messages.append(f'Amount wagered for {league_name}: ${wagered}\n')
                logger.info(f'Amount wagered for {league_name}: ${wagered}')
                messages.append(f'Amount earned for {league_name}: ${earnings}\n')
                logger.info(f'Amount earned for {league_name}: ${earnings}')
                messages.append(f'Profit for {league_name}: ${earnings-wagered}\n')
                logger.info(f'Profit for {league_name}: ${earnings-wagered}')

                strat_config[league_name]['bankroll'] += earnings
                update_config(strat_config, config_path)
                messages.append(f"Final bankroll for {league_name}: ${strat_config[league]['bankroll']}")
                logger.info(f"Final bankroll for {league_name}: ${strat_config[league]['bankroll']}")

                file_path = f'bankroll/{season}/{league}_bankroll.csv'
                output_path = f'bankroll/{season}/charts/{league}_bankroll.png'
                record_bankroll(starting_bk, strat_config[league]['bankroll'], file_path, today)
                generate_chart(file_path, output_path, league=league_name, season=season)

                total_wagered += wagered
                total_earnings += earnings

                execute_many(update_match_ratings, updates)
                
                delete_some(delete_some_from_upcoming_games_query, (league, today))
            
            if len(bets) > 0:
                file_path = f'bankroll/{season}/Consolidated_bankroll.csv'
                output_path = f'bankroll/{season}/charts/Consolidated_bankroll.png'
                final_bk = consolidated_starting+total_earnings
                record_bankroll(consolidated_starting, final_bk, file_path, today)
                generate_chart(file_path, output_path, league='Consolidated', season=season)

                messages.append(f'Total amount wagered: ${total_wagered}\n')
                logger.info(f'Total amount wagered: ${total_wagered}')
                messages.append(f'Total amount earned: ${total_earnings}\n')
                logger.info(f'Total amount earned: ${total_earnings}')
                messages.append(f'Total profit: ${total_earnings-total_wagered}\n\n')
                logger.info(f'Total profit: ${total_earnings-total_wagered}')

                messages.append(f"Consolidated starting bankroll: ${consolidated_starting}\n")
                logger.info(f"Consolidated starting bankroll: ${consolidated_starting}")
                messages.append(f"Consolidated ending bankroll: ${final_bk}\n")
                logger.info(f"Consolidated ending bankroll: ${final_bk}")
                
            # delete_all(delete_all_from_upcoming_games_query)
            send_email(messages, subject, logger)
        else:
            print('Unknown betting strategy or empty strategies list from config')
            exit(1)
    except Exception as e:
        logger.error(e)
    else:
        logger.info('Mission accomplished.')

def fetch_today_games_results(session: requests.Session, league, date, season, game_ids, logger: Logger):
    try:
        params = {"league":league,"season":season.split('-')[0],"date": date,"timezone":"America/New_York"}

        response = session.get(url, headers=headers, params=params)

        # print(response.json())

        data = response.json()

        fixtures = [
            (
                int(fixture['goals']['home']),
                int(fixture['goals']['away']),
                'home' if int(fixture['goals']['home']) > int(fixture['goals']['away']) 
                else ('away' if int(fixture['goals']['home']) < int(fixture['goals']['away']) else 'draw'),
                int(fixture['fixture']['id']),
            ) for fixture in data['response'] if int(fixture['fixture']['id']) in game_ids
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
