#!/usr/bin/python3

import sys 

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

getcontext().prec = 2

def main(args):
    try:
        betting_strategy = args.betting_strategy.lower()

        config = read_config(CONFIG_FILE)
        strategies_list = config.get('strategies', [])
        leagues = config.get('leagues', {})
        season = config.get('season', '2024-2025')

        if betting_strategy in strategies_list:
            getcontext().prec = 3

            today_dt = datetime.now()
            today = today_dt.strftime('%Y-%m-%d')

            log_path = f"{LOGS}/{betting_strategy}/bet_settler/{season}"
            create_dir(log_path)
            logger = setup_logger('bet_settler', f'{log_path}/{today}_bet_settler.log')

            logger.info(f'Starting bet_bot: bet_settler {betting_strategy}')

            select_from_match_ratings_query = configs.get('SELECT_FROM_MATCH_RATINGS').data.replace('\"', '')
            update_match_ratings = configs.get('UPDATE_MATCH_RATINGS').data.replace('\"', '')
            # delete_all_from_upcoming_games_query = configs.get('DELETE_ALL_FROM_UPCOMING_GAMES').data.replace('\"', '')
            delete_some_from_upcoming_games_query = configs.get('DELETE_SOME_FROM_UPCOMING_GAMES').data.replace('\"', '')
            strategy_factory = StrategyFactory()

            config_path = strategy_factory.get_config(betting_strategy)
            strat_config = read_config(config_path)
            
            updates = []
            session = SessionManager().get_session()

            subject = f'Settling bets for {today} with {betting_strategy} strategy'
            messages = []

            total_wagered = 0
            total_earnings = 0
            total_profit = 0

            bk_dir = f'{BANKROLL_DIR}/{season}/data'
            create_dir(bk_dir)
            bk_chart_dir = f'{BANKROLL_DIR}/{season}/charts'
            create_dir(bk_chart_dir)

            bets = []

            consolidated_starting = 0

            for league, league_id in leagues.items():
                league_name = strat_config[league]['name']

                starting_bk = round(strat_config[league]['bankroll'], 2)

                messages.append(f"{league_name} starting bankroll: ${starting_bk}\n")

                logger.info(f"Starting bankroll for {league_name}: ${starting_bk}")
                consolidated_starting += starting_bk

                bets = load_many(select_from_match_ratings_query, league, today)

                if len(bets) == 0:
                    messages.append(f"No bets to settle for {league_name}\n")
                    logger.warning(f"No bets to settle for {league_name}")
                    continue

                bets = {bet[0]: bet for bet in bets}

                bets_headlines = '\n'.join([f"{bet[1]} - {bet[2]}" for bet in bets.values()])

                messages.append(f"{league_name} games\n {'-' * (len(league_name)+6)}\n")

                logger.info(f"Bets for {league_name} on {today}: \n{bets_headlines}")
                results = fetch_today_games_results(session, league_id, today, season, bets.keys(), logger)

                # if len(bets) != len(results):
                #     messages.append(f'Results length does not match bets length for {league}\n')
                #     logger.warning(f'Results length does not match bets length for {league}')
                #     continue

                wagered = 0
                earnings = 0
                sum_profit = 0

                time.sleep(1)

                for result in results:
                    fthg, ftag, ftr, game_id = result

                    # game_id, home_team, away_team, bet, stake, bet_odds, bookmaker, bankroll

                    bet = bets.get(game_id, {})

                    if not bet:
                        messages.append(f'Game with id={game_id} is not found in bets table for {league}\n')
                        logger.warning(f'Game with id={game_id} is not found in bets table for {league}')
                        continue

                    gl = float(Decimal(bet[4]) * Decimal(bet[5])) if ftr == bet[3] else 0

                    profit = float(Decimal(gl) - Decimal(bet[4])) if gl > 0 else -bet[4]

                    if bet[8] == 'SUCCESS':
                        res =  'W' if gl > 0 else 'L'
                        wagered += bet[4]
                        earnings += gl
                        sum_profit += profit
                    else:
                        res = 'NB'
                    
                    yield_ = float(Decimal(profit) / Decimal(bet[4]) * 100)

                    updated_at = datetime.now().strftime('%Y-%m-%d %H:%M:%f')

                    updates.append((fthg, ftag, ftr, res, gl, profit, yield_, updated_at, game_id))
                    messages.append(f"Results for {bet[1]} - {bet[2]}: Score: {fthg}-{ftag} | My bet: {bet[3]} | Status: {bet[8]} | Odds: {bet[5]} | Bookmaker: {bet[6]} | Result: {res} | Stake: ${bet[4]} | G/L: ${gl} | Profit: ${profit} | Yield: {yield_}%\n")
                    logger.info(f"Results for {bet[1]} - {bet[2]}: Score: {fthg}-{ftag} | My bet: {bet[3]} | Status: {bet[8]} | Odds: {bet[5]} | Bookmaker: {bet[6]} | Result: {res} | Stake: ${bet[4]} | G/L: ${gl} | Profit: ${profit} | Yield: {yield_}%")

                messages.append(f'Amount wagered for {league_name}: ${wagered:.2f}')
                logger.info(f'Amount wagered for {league_name}: ${wagered:.2f}')
                messages.append(f'Amount earned for {league_name}: ${earnings:.2f}')
                logger.info(f'Amount earned for {league_name}: ${earnings:.2f}')
                messages.append(f'Profit for {league_name}: ${(sum_profit):.2f}')
                logger.info(f'Profit for {league_name}: ${(sum_profit):.2f}')

                strat_config[league]['bankroll'] += earnings
                strat_config[league]['bankroll'] = round(strat_config[league]['bankroll'], 2)
                
                messages.append(f"Final bankroll for {league_name}: ${strat_config[league]['bankroll']}\n")
                logger.info(f"Final bankroll for {league_name}: ${strat_config[league]['bankroll']}")

                file_path = f'{BANKROLL_DIR}/{season}/data/{league}_bankroll.csv'
                output_path = f'{BANKROLL_DIR}/{season}/charts/{league}_bankroll.png'
                record_bankroll(starting_bk, strat_config[league]['bankroll'], file_path, today_dt)
                generate_chart(file_path, output_path, league=league_name, season=season)

                total_wagered += wagered
                total_earnings += earnings
                total_profit += sum_profit

                execute_many(update_match_ratings, updates)

                logger.info(f'Deleting settled games from upcoming_games table for {league}')
                delete_some(delete_some_from_upcoming_games_query, (league, today))
            
            update_config(strat_config, config_path)

            if len(bets) > 0:
                file_path = f'{BANKROLL_DIR}/{season}/data/Consolidated_bankroll.csv'
                output_path = f'{BANKROLL_DIR}/{season}/charts/Consolidated_bankroll.png'
                final_bk = round(consolidated_starting+total_earnings, 2)
                record_bankroll(consolidated_starting, final_bk, file_path, today_dt)
                generate_chart(file_path, output_path, league='Consolidated', season=season)

                messages.append(f'Total amount wagered: ${total_wagered:.2f}')
                logger.info(f'Total amount wagered: ${total_wagered:.2f}')
                messages.append(f'Total amount earned: ${total_earnings:.2f}')
                logger.info(f'Total amount earned: ${total_earnings:.2f}')
                messages.append(f'Total profit: ${(total_profit):.2f}\n')
                logger.info(f'Total profit: ${(total_profit):.2f}')

                messages.append(f"Consolidated starting bankroll: ${consolidated_starting:.2f}")
                logger.info(f"Consolidated starting bankroll: ${consolidated_starting:.2f}")
                messages.append(f"Consolidated ending bankroll: ${final_bk:.2f}\n")
                logger.info(f"Consolidated ending bankroll: ${final_bk:.2f}")
                
            # delete_all(delete_all_from_upcoming_games_query)
            send_email(messages, subject, logger)
        else:
            print('Unknown betting strategy or empty strategies list from config')
            exit(1)
    except Exception as e:
        e_type, e_object, e_traceback = sys.exc_info()
        e_filename = os.path.split(
            e_traceback.tb_frame.f_code.co_filename
        )[1]
        e_line_number = e_traceback.tb_lineno
        logger.error(f'{e}, type: {e_type}, filename: {e_filename}, line: {e_line_number}')
    else:
        logger.info('Mission accomplished.')

def fetch_today_games_results(session: requests.Session, league, date, season, game_ids, logger: Logger):
    try:
        fixtures = []
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
    except RetryError as err:
        logger.error(f"Login failed | Retry Error: {err}")
    except Exception as err:
        logger.error(f"fetch_today_games_results(): Other error occurred: {err}")
    else:
        logger.info(f"Games to settle: {fixtures}")
    finally:
        return fixtures

if __name__ == '__main__':
    args = args_parser() 
    main(args)
