#!/usr/bin/python3

import subprocess
import os
import sys

from datetime import datetime
from decimal import getcontext, Decimal

from jproperties import Properties

from bot.betting_bot import BettingBot
from helpers.main_args_parser import args_parser
from helpers.send_email import send_email
from helpers.logger import setup_logger

from bot.betting_bot_factory import BettingBotFactory
from strategies.strategy_factory import StrategyFactory
from utils.utils import *

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

insert_new_bets_query = configs.get('INSERT_INTO_MATCH_RATINGS').data.replace('\"', '')
select_upcoming_games_query = configs.get('SELECT_TEAMS_FROM_UPCOMING_GAMES').data.replace('\"', '')
delete_from_match_ratings_query = configs.get('DELETE_SOME_FROM_MATCH_RATINGS').data.replace('\"', '')
check_match_ratings_query = configs.get('CHECK_MATCH_RATINGS').data.replace('\"', '')

today = datetime.now().strftime('%Y-%m-%d')

def main(args):
    try:
        betting_strategy = args.betting_strategy.lower()
        staking_strategy = args.staking_strategy.lower()
        bookmaker = args.bookmaker.lower()

        config = read_config(CONFIG_FILE)
        leagues = config.get('leagues', {})
        season = config.get('season', '2024-2025')
        strategies_list = config.get('strategies', [])

        if betting_strategy in strategies_list:
            log_path = f'{LOGS}/{betting_strategy}/main/{season}'
            create_dir(log_path)
            logger = setup_logger('main', f'{log_path}/{today}_main.log')

            logger.info(f'Starting bet_bot:main {betting_strategy} {staking_strategy} {bookmaker}')
            
            # process = subprocess.run(f'cd {BETTING_CRAWLER_PATH} && scrapy crawl historical_data', shell=True, capture_output=True, text=True)

            # if process.returncode != 0:
            #     raise OSError('Sorry scrapy is not installed.')

            if bookmaker == 'pinnacle':
                bookmaker_ids = config['pinnacle_ids']
            else:
                raise ValueError('Unknown bookmaker chosen.')

            credentials = read_config(CREDENTIALS_FILE)

            logger.info(f'Config: Leagues: {list(leagues.keys())} | Season: {season}')

            bets = []
            status = 'FAILED'

            getcontext().prec = 3

            betting_bot_factory = BettingBotFactory()
            betting_bot = betting_bot_factory.select_betting_bot(bookmaker)
            logged_in = betting_bot.login(credentials[bookmaker], logger)

            if not logged_in:
                raise Exception(f'Unable to log into {bookmaker} account')
            
            logger.info(f'Succesfully logged into {bookmaker}')

            strategy_factory = StrategyFactory()
            config_path = strategy_factory.get_config(betting_strategy)
            strat_config = read_config(config_path)

            subject = f'Placing bets on {today} for {betting_strategy} strategy with {bookmaker}'
            messages = []

            consolidated_starting = 0
            total_staked = 0
            placed = 0

            for league, league_id in leagues.items():
                league_name = strat_config[league]['name']

                if not fetch_upcoming_games(league_id, league, today, season, logger):
                    logger.info(f'No game(s) found for {league_name}')
                    messages.append(f'No game(s) found for {league_name}\n')
                    continue

                data = read_csv_file(os.path.join(HIST_DATA_PATH, f'{season}/{league}.csv'))

                if len(data) == 0:
                    logger.warning(f'Failed to retrieve historical data for {league_name}')
                    messages.append(f'Failed to retrieve historical data for {league_name}\n')
                    continue
                
                games = load_many(select_upcoming_games_query, today, league)

                bets_ids = execute(check_match_ratings_query, (league, today))

                bets_ids = {bet[0]: bet[1] for bet in bets_ids} if bets_ids else {}

                starting_bk = curr_bal = round(strat_config[league]['bankroll'], 2)
                consolidated_starting += starting_bk

                logger.info(f"Starting bankroll for {league_name}: ${starting_bk}")
                messages.append(f"{league_name} starting bankroll: ${starting_bk}\n")
                
                if len(games) > 0:
                    games_headlines = '\n'.join([f"{game[3]} - {game[4]}" for game in games])
                    logger.info(f'Games for {league_name}: \n{games_headlines}')

                    betting_bot.simulate_human_behavior()
                    games_url = betting_bot.get_game_urls(bookmaker_ids[league], logger, today=today)

                    messages.append(f"{league_name} games")
                    messages.append(f"{'-' * (len(league_name)+6)}\n")
                    messages.append(games_headlines+'\n')
                else:
                    logger.warning(f'Failed to retrieve upcoming games from DB for {league}')
                    messages.append(f'Failed to retrieve upcoming games from DB for {league}\n')
                    continue

                consolidated = 0

                for game in games:
                    if game[0] in bets_ids.keys():
                        bet_status = bets_ids.get(game[0], None)
                        if bet_status == 'SUCCESS':
                            logger.info(f"Bet for {game[3]} - {game[4]} already placed")
                            messages.append(f"Bet for {game[3]} - {game[4]} already placed")
                            continue
                        elif bet_status == 'FAILED':
                            delete_some(delete_from_match_ratings_query, (game[0],))
                            logger.info(f"Bet for {game[3]} - {game[4]} failed will re-attempt it")
                            messages.append(f"Bet for {game[3]} - {game[4]} failed will re-attempt it")
                        else:
                            logger.info(f"Bet for {game[3]} - {game[4]} was not placed because {bet_status}")
                            messages.append(f"Bet for {game[3]} - {game[4]} was not placed because {bet_status}")
                            continue
                    
                    home_, away_ = map_from_rapidapi_to_bookmaker(game[3], game[4], league, bookmaker)
                    game_url = list(filter(lambda game_: game_['home']==home_ and game_['away']==away_, games_url))[0]
                    home_odds, draw_odds, away_odds = betting_bot.check_odds(game_url['url'], logger, game_id=game[0])
                    logger.info(f"{bookmaker} odds for {game[3]} - {game[4]}: H: {home_odds:.2f} | D: {draw_odds:.2f} | A: {away_odds:.2f}")

                    home_proba, draw_proba, away_proba = round(float(Decimal(1./home_odds)), 2), round(float(Decimal(1./draw_odds)), 2), round(float(Decimal(1./away_odds)), 2)
                    logger.info(f"{bookmaker} implied proba for {game[3]} - {game[4]}: H: {home_proba*100:.2f}% | D: {draw_proba*100:.2f}% | A: {away_proba*100:.2f}%")

                    vig = calculate_vig(home_proba, draw_proba, away_proba)*100
                    logger.info(f"{bookmaker} vig for {game[3]} - {game[4]}: {vig:.2f}%")

                    strategy = strategy_factory.select_strategy(betting_strategy, data, league, strat_config, staking_strategy, home_odds=home_odds, draw_odds=draw_odds, away_odds=away_odds, season=season)
                    
                    home_, away_ = map_from_rapidapi_to_hist_data(game[3], game[4], league)
                    values = strategy.compute(home_, away_, betting_strategy, logger)

                    if not values:
                        logger.info(f"Computation for {game[3]} - {game[4]} failed because of an error in {betting_strategy} strategy module")
                        messages.append(f"Computation for {game[3]} - {game[4]} failed because of an error in {betting_strategy} strategy module")
                        continue
                    
                    status = get_status(betting_bot, bookmaker, values, game_url, logger)

                    if status == 'SUCCESS':
                        placed += 1

                    match betting_strategy:
                        case 'match_ratings':
                            pre_computed_values = [
                                game[0], 
                                game[1], 
                                game[3], 
                                game[4], 
                                season,
                                league, 
                                league_name,
                                game[2],
                                game[5],
                                game[6],
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

                            flag = values.pop('flag')

                            if flag:
                                curr_bal -= values['stake']
                                consolidated += values['stake']
                                total_staked += values['stake']

                            additional_values = [status, curr_bal]

                            final_values = pre_computed_values + list(values.values()) + additional_values
                            final_values = tuple(final_values)
                        case _:
                            final_values = ()

                    bets.append(final_values)

                    logger.info(f"{game[3]} - {game[4]}: Bet: {values['bet']} | Odds: {values['bet_odds']} | Stake: ${values['stake']} | Status: {status}")
                    messages.append(f"{game[3]} - {game[4]}: Bet: {values['bet']} | Odds: {values['bet_odds']} | Stake: ${values['stake']} | Status: {status}\n")

                strat_config[league]['bankroll'] -= consolidated
                update_config(strat_config, config_path)

                messages.append(f"Amount wagered for {league_name}: ${consolidated:.2f}")
                logger.info(f"Amount wagered for {league_name}: ${consolidated:.2f}")
                messages.append(f"Final bankroll for {league_name}: ${strat_config[league]['bankroll']:.2f}\n")
                logger.info(f"Final bankroll for {league_name}: ${strat_config[league]['bankroll']:.2f}")
            
            if len(bets) > 0:
                final_bk = consolidated_starting-total_staked

                messages.append(f"Total amount wagered: ${total_staked:.2f}")
                messages.append(f"Consolidated starting bankroll: ${consolidated_starting:.2f}")
                messages.append(f"Consolidated ending bankroll: ${final_bk:.2f}\n")

                logger.info(f"Total amount wagered: ${consolidated:.2f}")
                logger.info(f"Consolidated starting bankroll: ${consolidated_starting:.2f}")
                logger.info(f"Consolidated ending bankroll: ${final_bk:.2f}")

                execute_many(insert_new_bets_query, bets)
            
            messages.append(f'Total: {placed} bet(s) placed\n')
            logger.info(f'Total: {placed} bet(s) placed')
            
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

def get_status(betting_bot: BettingBot, bookmaker, values, game_url, logger):
    min_stake, max_stake = betting_bot.get_max_min_stake(game_url, values['bet'], values['bet_odds'], logger, today=today)
    if values['stake'] >= min_stake and values['flag']:
        betting_bot.simulate_human_behavior() 
        curr_bal = betting_bot.check_balance(logger, today=today) 
        if curr_bal > values['stake']:
            betting_bot.simulate_human_behavior()

            if values['stake'] > max_stake:
                logger.info(f"Original stake of ${values['stake']} too high as per {bookmaker} limits. Updating to ${max_stake}")
                values['stake'] = max_stake

            success = betting_bot.place_bet(values['bet_odds'], values['stake'], values['bet'], game_url, min_stake, logger)
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
