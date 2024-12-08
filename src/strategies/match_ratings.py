from logging import Logger
import sys
import os
from dotenv import load_dotenv

from typing import Dict, List

from filelock import FileLock
from staking.staking_factory import StakingFactory
from strategies.strategy import Strategy

from decimal import getcontext, Decimal

from pandas import DataFrame
import math

load_dotenv(override=True)

MISC_PATH = os.environ['MISC_PATH']

class MatchRatingsStrategy(Strategy):
    possible_results = ['home', 'draw', 'away']
    config_path = os.environ['MATCH_RATING_CONFIG_FILE']
    
    def __init__(self, data, league, strat_config, staking_strategy, **kwargs) -> None:
        super().__init__(data, league, strat_config, staking_strategy, **kwargs)
        self.home_odds = kwargs.get('home_odds', 0)
        self.draw_odds = kwargs.get('draw_odds', 0)
        self.away_odds = kwargs.get('away_odds', 0)
        self.season = kwargs.get('season', '2024-2025')

    def compute(self, home: str, away: str, betting_strategy: str, logger: Logger):
        try:
            getcontext().prec = 3

            r = {}

            df: DataFrame = self.data.copy()
            df = df[['Date', 'HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']]
            df.set_index('Date', inplace=True)
            lst = get_teams_list(df)
            teams = group_data_by_teams(df, lst, self.league, self.season, f'{MISC_PATH}/{betting_strategy}')
            self.home_rating, self.away_rating, self.match_rating = compute_ratings(teams, home, away)
            home_win_coeffs, away_win_coeffs = get_coeffs(self.strat_config, self.league)
            self.hwtp = (Decimal(home_win_coeffs['beta_coeff']) * Decimal(self.match_rating) + Decimal(home_win_coeffs['constant'])) / Decimal(100.)
            self.awtp = (Decimal(away_win_coeffs['beta_squared_coeff']) * Decimal(self.match_rating**2) + Decimal(away_win_coeffs['beta_coeff']) * Decimal(self.match_rating) + Decimal(away_win_coeffs['constant'])) / Decimal(100.)
            self.dtp = Decimal(1.) - (self.hwtp + self.awtp)
            
            if self.hwtp > 0:
                self.hwto = float(Decimal(1.) / Decimal(self.hwtp))
            else:
                self.hwto = self.home_odds

            if self.awtp > 0:
                self.awto = float(Decimal(1.) / Decimal(self.awtp))
            else:
                self.awto = self.away_odds

            if self.dtp > 0:
                self.tdo = float(Decimal(1.) / Decimal(self.dtp))
            else:
                self.tdo = self.draw_odds

            self.hv = float(Decimal(self.hwtp) * Decimal(self.home_odds) - 1)
            self.dv = float(Decimal(self.dtp) * Decimal(self.draw_odds) - 1)
            self.av = float(Decimal(self.awtp) * Decimal(self.away_odds) - 1)

            staking_factory = StakingFactory()
            self.h = staking_factory.select_staking_strategy(self.strat_config[self.league]['bankroll'], self.staking_strategy, odds=self.home_odds, value=self.hv).compute()
            self.d = staking_factory.select_staking_strategy(self.strat_config[self.league]['bankroll'], self.staking_strategy, odds=self.draw_odds, value=self.dv).compute()
            self.a = staking_factory.select_staking_strategy(self.strat_config[self.league]['bankroll'], self.staking_strategy, odds=self.away_odds, value=self.av).compute()
            self.bet = get_value(self.possible_results, self.h, self.d, self.a)
            self.bet_odds = self.home_odds if self.bet == 'home' else (self.away_odds if self.bet == 'away' else self.draw_odds)
            self.value = max(self.hv, self.dv, self.av)
            self.stake = max(self.h, self.d, self.a, 0)

            logger.info(
                f"""{betting_strategy}:
                {home} - {away}
                {'-' * (len(home)+len(away)+2)}

                {home} rating: {self.home_rating}
                {away} rating: {self.away_rating}
                Match rating: {self.match_rating}

                True Home Win Proba: {self.hwtp*100:.2f}%
                True Draw Proba: {self.dtp*100:.2f}%
                True Away Proba: {self.awtp*100:.2f}%

                True Home Win Odds: {self.hwto}
                True Draw Win Odds: {self.tdo}
                True Away Win Odds: {self.awto}

                Home Win Value: {self.hv}
                Draw Value: {self.dv}
                Away Win Value: {self.av}

                Home Win Stake: {self.h}
                Draw Stake: {self.d}
                Away Win Stake: {self.a}

                Pre-bet BK: ${self.strat_config[self.league]['bankroll']:.2f}
                
                Bet: {self.bet}""")

            r = {
                'home_rating': self.home_rating,
                'away_rating': self.away_rating,
                'match_rating': self.match_rating,
                'hwto': self.hwto,
                'tdo': self.tdo,
                'awto': self.awto,
                'hwtp': round(float(self.hwtp), 3),
                'dtp': round(float(self.dtp), 3),
                'awtp': round(float(self.awtp), 3),
                'hv': self.hv,
                'dv': self.dv,
                'av': self.av,
                'h': self.h,
                'd': self.d,
                'a': self.a,
                'bet': self.bet,
                'bet_odds': self.bet_odds,
                'value': self.value,
                'stake': round(self.stake, 1),
                'flag': True if (self.bet == 'home' and (0 < self.value) and self.stake > 1) else False
            }
        except Exception as e:
            e_type, e_object, e_traceback = sys.exc_info()
            e_filename = os.path.split(
                e_traceback.tb_frame.f_code.co_filename
            )[1]
            e_line_number = e_traceback.tb_lineno
            logger.error(f'{e}, type: {e_type}, filename: {e_filename}, line: {e_line_number}')
        finally:
            return r
    
def get_coeffs(strat_config: dict, league: str):
    home_win_coeffs = strat_config[league]['home']
    away_win_coeffs = strat_config[league]['away']
    return home_win_coeffs, away_win_coeffs

def get_teams_list(df: DataFrame):
    lst = list(df.HomeTeam.unique())
    return lst

def group_data_by_teams(df: DataFrame, lst: List[str], league: str, curr_season: str, path: str):
    teams = {}
    for el in lst:
        teams[el] = df[(df.HomeTeam == el) | (df.AwayTeam == el)].copy()
        teams[el]['Season'] = curr_season
        teams[el]['Team'] = el
        teams[el]['League'] = league
        games = [i for i in range(1, int(teams[el].count().iloc[0]) + 1)]
        teams[el]['Round'] = games.copy()
        teams[el].sort_values(by='Round', inplace=True)
        teams[el].loc[teams[el].HomeTeam == el, 'Rating'] = teams[el]['FTHG'] - teams[el]['FTAG']
        teams[el].loc[teams[el].AwayTeam == el, 'Rating'] = teams[el]['FTAG'] - teams[el]['FTHG']
        teams[el]['Rolling Average'] = teams[el]['Rating'].shift().rolling(6).sum()

        transformed_hist_data = f'{path}/transformed_hist_data/{curr_season}/{league}'
        # if not os.path.exists(transformed_hist_data):
        os.makedirs(transformed_hist_data, exist_ok=True)

        file_path = f'{transformed_hist_data}/{el}.csv'
        lock_path = f'{path}/locks/{league}/{el}.csv.lock'  # Create a lock file path

        # Use a lock to ensure only one instance writes to the file at a time
        with FileLock(lock_path):
            teams[el].to_csv(file_path)
    return teams
    
def compute_ratings(teams: Dict[str, DataFrame], home, away):
    # home_rating = Decimal(teams[home]['Rolling Average'].iloc[-1])
    # away_rating = Decimal(teams[away]['Rolling Average'].iloc[-1])
    home_rating = Decimal(teams[home]['Rating'].rolling(6).sum().iloc[-1])
    away_rating = Decimal(teams[away]['Rating'].rolling(6).sum().iloc[-1])

    if math.isnan(home_rating) or math.isnan(away_rating):
        raise ValueError(f'Not enough data to execute match_ratings strategy for {home} - {away}. Home rating: {home_rating}, Away rating: {away_rating}')
    
    match_rating = home_rating - away_rating
    return float(home_rating), float(away_rating), float(match_rating)

def get_value(values, *args):
    val = max(args)
    
    if val == args[0]:
        return values[0]
    elif val == args[1]:
        return values[1]
    else:
        return values[2]
