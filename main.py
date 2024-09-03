#!/usr/bin/python3

import sys
import subprocess
import os
import csv
from datetime import datetime, timedelta
from decimal import getcontext, Decimal

from jproperties import Properties

from dotenv import load_dotenv

from helpers.main_args_parser import args_parser
from helpers.send_email import send_email
from helpers.logger import setup_logger
load_dotenv(override=True)

from bot.betting_bot_factory import BettingBotFactory
from strategies.strategy_factory import StrategyFactory
from utils.utils import calculate_vig, fetch_hist_data, fetch_upcoming_games, execute_many, load_many, read_config, record_bankroll, update_config

CONFIG_FILE = os.environ['CONFIG_FILE']
CREDENTIALS_FILE = os.environ['CREDENTIALS_FILE']
HIST_DATA_PATH = os.environ['HIST_DATA_PATH']
SQL_PROPERTIES = os.environ['SQL_PROPERTIES']
LOGS = os.environ['LOGS']

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

insert_new_bets_query = configs.get('INSERT_INTO_MATCH_RATINGS').data
load_upcoming_games_query = configs.get('SELECT_TEAMS_FROM_UPCOMING_GAMES').data

today = datetime.now().strftime('%Y-%m-%d')

def main(args):
    try:
        betting_strategy = args.betting_strategy.lower()
        staking_strategy = args.staking_strategy.lower()
        bookmaker = args.bookmaker.lower()

        config = read_config(CONFIG_FILE)
        strategies_list = config['strategies']

        if betting_strategy in strategies_list:
            # process = subprocess.run(['./venv/bin/scrapy crawl', 'historical_data'], shell=True, capture_output=True, text=True)

            # if process.returncode != 0:
            #     raise OSError('Sorry scrapy is not installed.')
        
            leagues = config['leagues']

            if bookmaker == 'pinnacle':
                bookmaker_ids = config['pinnacle_ids']
            else:
                raise ValueError('Unknown bookmaker chosen.')
            
            season = config['season']

            logger = setup_logger('main', f'{LOGS}/{betting_strategy}/main/{season}/{today}_main.log')

            logger.info(f'Starting bet_bot:main {betting_strategy} {staking_strategy} {bookmaker}')

            credentials = read_config(CREDENTIALS_FILE)

            logger.info(f'Config: Leagues: {leagues} | Season: {season}')

            bets = []
            status = 'FAILED'

            getcontext().prec = 3

            betting_bot_factory = BettingBotFactory()
            betting_bot = betting_bot_factory.select_betting_bot(bookmaker)
            logged_in = betting_bot.login(credentials, logger, today=today)

            if not logged_in:
                raise Exception(f'Unable to log into {bookmaker} account.')
            
            logger.info(f'Succesfully logged into {bookmaker}')

            strategy_factory = StrategyFactory()

            config_path = strategy_factory.get_config(betting_strategy)
            strat_config = read_config(config_path)

            consolidated = 0

            select_upcoming_games_query = configs.get('SELECT_TEAMS_FROM_UPCOMING_GAMES').data

            subject = f'Bets for {today} with {betting_strategy} strategy with {bookmaker}'
            messages = []

            for league, league_id in leagues.items():
                fetch_upcoming_games(league_id, today, season)
                data = fetch_hist_data(os.path.join(HIST_DATA_PATH, f'{season}/{league}.csv'))

                if len(data) == 0:
                    raise ValueError(f'Failed to retrieve historical data for {league}.')
                
                messages.append(f"{strat_config[league]['name']} games")
                messages.append(f"{'-' * (len(strat_config[league]['name'])+6)}\n\n")
                
                games = load_many(select_upcoming_games_query, today, league)

                starting_bk = strat_config[league]['bankroll']

                messages.append(f"{strat_config[league]} starting bankroll: {starting_bk}\n\n")

                logger.info(f"Starting bankroll for {strat_config[league]['name']}: ${starting_bk}")
                consolidated_starting += starting_bk
                
                if len(games) > 0:
                    games_headlines = '\n'.join([f"{game['home_team']} - {game['away_team']}" for game in games])
                    logger.info(f'Games for {league} on {today}: \n{games_headlines}')
                    messages.append(games_headlines)

                    betting_bot.simulate_human_behavior()
                    games_url = betting_bot.get_game_urls(bookmaker_ids[league], logger, today=today)

                    messages.append(f"{strat_config[league]['name']} bets")
                    messages.append(f"{'-' * (len(strat_config[league]['name'])+5)}\n\n")
                else:
                    logger.info(f'No game found for {league} on {today}')
                    messages.append(f'No game found for {league} on {today}')
                    break

                for game in games:
                    game_url = filter(lambda game_: game_['home']==game['home_team'] and game_['away']==game['away_team'], games_url)[0]
                    home_odds, draw_odds, away_odds = betting_bot.check_odds(game_url, logger, today=today)
                    logger.info(f"{bookmaker} odds for {game['home']} - {game['away']}: H: {home_odds} | D: {draw_odds} | A: {away_odds}")

                    home_proba, draw_proba, away_proba = float((Decimal(1) / Decimal(home_odds))*100), float((Decimal(1) / Decimal(draw_odds))*100), float((Decimal(1) / Decimal(away_odds))*100)
                    logger.info(f"{bookmaker} implied proba {game['home']} - {game['away']}: H: {home_proba} | D: {draw_proba} | A: {away_proba}")

                    vig = float(Decimal(calculate_vig(home_proba, draw_proba, away_proba))*100)
                    logger.info(f"{bookmaker} vig for {game['home']} - {game['away']}: {vig}%")

                    strategy = strategy_factory.select_strategy(betting_strategy, data, league, staking_strategy, strat_config, home_odds=home_odds, draw_odds=draw_odds, away_odds=away_odds)
                    
                    try:
                        values = strategy.compute(game['home_team'], game['away_team'], betting_strategy, logger)
                    except ValueError as err:
                        logger.error(err)
                        break
                    
                    status = get_status(betting_bot, bookmaker, values, game_url, game['game_id'], logger)

                    match betting_strategy:
                        case 'match_ratings':
                            pre_computed_values = [
                                game['game_id'], 
                                game['game_date'], 
                                game['home_team'], 
                                game['away_team'], 
                                season,
                                league, 
                                strat_config[league]['name'],
                                game['round'],
                                None,
                                None,
                                None,
                                bookmaker,
                                game_url['id'],
                                home_odds,
                                draw_odds,
                                away_odds,
                                home_proba,
                                draw_proba,
                                away_proba,
                                vig
                            ]

                            additional_values = [status, strat_config[league]['bankroll']]

                            final_values = pre_computed_values + list(values.values()) + additional_values
                            final_values = tuple(final_values)
                        case _:
                            final_values = ()
                    bets.append(final_values)

                    strat_config[league]['bankroll'] = strat_config[league]['bankroll'] - values['stake']
                    consolidated += values['stake']

                    messages.append(f"{game['home']} - {game['away']}: Bet: {values['bet']} | Odds: {values['bet_odds']} | Stake: ${values['stake']} | Vig: {vig}% | Status: {status}\n")

                messages.append(f"{strat_config[league]} amount wagered: ${consolidated}\n")
                messages.append(f"{strat_config[league]} ending bankroll: ${strat_config[league]['bankroll']}\n")
                update_config(strat_config, config_path)

                logger.info(f"Final bankroll for {strat_config[league]['name']}: ${strat_config[league]['bankroll']}")

                if len(bets) > 0:
                    file_path = f'./bankroll/{season}/{league}_bankroll.csv'
                    record_bankroll(starting_bk, strat_config[league]['bankroll'], file_path, today)
            
            if len(bets) > 0:
                file_path = f'./bankroll/{season}/Consolidated_bankroll.csv'
                final_bk = consolidated_starting-consolidated
                record_bankroll(consolidated_starting, final_bk, file_path, today)

                messages.append(f"Total amount wagered: ${consolidated}\n")
                messages.append(f"Consolidated starting bankroll: ${consolidated_starting}\n")
                messages.append(f"Consolidated ending bankroll: ${final_bk}\n")

                execute_many(insert_new_bets_query, bets)
            
            logger.info(f"Consolidated ending bankroll: ${final_bk}")
            send_email(messages, subject)
        else:
            raise ValueError('Unknown strategy picked.')

    except Exception as e:
        logger.error(e)
    else:
        logger.info('Mission accomplished.')

def get_status(betting_bot, bookmaker, values, game_url, game_id, logger):
    min_stake, max_stake = betting_bot.get_max_min_stake(game_url, values['bet'], values['bet_odds'], logger, today=today)
    if min_stake <= values['stake'] and values['flag']:
        betting_bot.simulate_human_behavior() 
        curr_bal = betting_bot.check_balance(logger, today=today) 
        if curr_bal > values['stake']:
            betting_bot.simulate_human_behavior()

            if values['stake'] > max_stake:
                logger.info(f"Original stake of ${values['stake']} too high as per {bookmaker} limits. Updating to ${max_stake}")
                values['stake'] = max_stake

            success = betting_bot.place_bet(values['bet'], values['stake'], values['bet'], game_url, min_stake, logger, today=today, game=game_id)
            if success:
                status = 'SUCCESS'
        else:
            raise ValueError(f"Balance of ${curr_bal} too low for stake ${values['stake']}")
    elif not values['flag']:
        status = 'EXCLUDED'
    else:
        status = 'STAKE TOO LOW'

    return status

if __name__ == '__main__':
    args = args_parser() 
    main(args)