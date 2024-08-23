import sys
import subprocess
import os
import re
from dotenv import load_dotenv
from datetime import datetime
from decimal import getcontext, Decimal

load_dotenv(override=True)

from bot.betting_bot_factory import BettingBotFactory
from strategies.strategy_factory import StrategyFactory
from utils.utils import MATCH_RATINGS_PATTERN, calculate_vig, fetch_hist_data, fetch_upcoming_games, insert_new_bets, load_upcoming_games, read_config, update_config

MATCH_RATING_CONFIG_FILE = os.environ['MATCH_RATING_CONFIG_FILE']
CREDENTIALS_FILE = os.environ['CREDENTIALS_FILE']
HIST_DATA_PATH = os.environ['HIST_DATA_PATH']

leagues = {'E0': '39', 'T1': '203', 'B1': '78', 'L1': '61', 'P1': '94'}

today = datetime.now()

def main():
    try:
        betting_strategy = sys.argv[1].lower()
        staking_strategy = sys.argv[2].lower()
        bookmaker = sys.argv[3].lower()

        if re.match(MATCH_RATINGS_PATTERN, betting_strategy):
            process = subprocess.run(['./venv/bin/scrapy crawl', 'historical_data'], shell=True, capture_output=True, text=True)

            if process.returncode != 0:
                raise OSError('Sorry scrapy is not installed.')
            
            config = read_config(MATCH_RATING_CONFIG_FILE)
            credentials = read_config(CREDENTIALS_FILE)

            leagues = config['leagues']
            season = config['season']

            bets = []
            status = 'FAILED'

            getcontext().prec = 3

            for league, league_id in leagues.items():
                fetch_upcoming_games(league_id, today, season)
                data = fetch_hist_data(os.path.join(HIST_DATA_PATH, league + '.csv'))
                games = load_upcoming_games(today, config[league]['name'])

                for game in games:
                    strategy_factory = StrategyFactory()
                    betting_bot_factory = BettingBotFactory()
                    betting_bot = betting_bot_factory.select_betting_bot(credentials[bookmaker]['username'], credentials[bookmaker]['password'], bookmaker)
                    # Fetch bookie odds
                    home_odds, draw_odds, away_odds = betting_bot.check_odds(game['home_team'], game['away_team'], game['game_date'])
                    home_proba, draw_proba, away_proba = float(Decimal(1) / Decimal(home_odds*100)), float(Decimal(1) / Decimal(draw_odds*100)), float(Decimal(1) / Decimal(away_odds*100))
                    values = strategy_factory.get_values(betting_strategy, game['home_team'], game['away_team'], data, league, staking_strategy, config[league]['bankroll'], home_odds=home_odds, draw_odds=draw_odds, away_odds=away_odds)

                    if values['stake'] * home_odds > 1 and values['bet'] == 'home':
                        betting_bot.place_bet(game['home_team'], game['away_team'], today, game['home_team'], values['stake'])
                        status = 'PLACED'
                    elif values['home'] != 'home':
                        status = 'NOT A HOME GAME'
                    else:
                        status = 'STAKE TOO LOW'

                    pre_computed_values = [
                        game['game_id'], 
                        game['game_date'], 
                        game['home_team'], 
                        game['away_team'], 
                        season, 
                        league, 
                        game['round'],
                        None,
                        None,
                        None,
                        bookmaker,
                        home_odds,
                        draw_odds,
                        away_odds,
                        home_proba,
                        draw_proba,
                        away_proba,
                        float(Decimal(calculate_vig(home_proba, draw_proba, away_proba))*100)
                    ]

                    config[league]['bankroll'] = config[league]['bankroll'] - values['stake']

                    additional_values = [status, None, None, config[league]['bankroll']]

                    final_values = pre_computed_values + list(values.values()) + additional_values
                    final_values = tuple(final_values)
                    bets.append(final_values)

                update_config(config, MATCH_RATING_CONFIG_FILE)
            insert_new_bets(bets)

    except Exception as e:
        print(e)

if __name__ == '__main__':
    main()