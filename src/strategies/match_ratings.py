from logging import Logger
import os
from dotenv import load_dotenv

from typing import Dict, List
from staking.staking_factory import StakingFactory
from strategies.strategy import Strategy

from decimal import getcontext, Decimal

from pandas import DataFrame

load_dotenv(override=True)

class MatchRatingsStrategy(Strategy):
    possible_results = ['home', 'draw', 'away']
    config_path = os.environ['MATCH_RATING_CONFIG_FILE']
    
    def __init__(self, data, league, staking_strategy, config, **kwargs) -> None:
        super(Strategy, self).__init__(data, league, staking_strategy, config)
        self.home_odds = kwargs.get('home_odds', 0)
        self.draw_odds = kwargs.get('draw_odds', 0)
        self.away_odds = kwargs.get('away_odds', 0)

    def compute(self, home: str, away: str, betting_strategy: str, logger: Logger):
        getcontext().prec = 3
        df = self.data.copy()
        df.reset_index()
        df = df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG']]
        lst = get_teams_list(df)
        teams = group_data_by_teams(df, lst)
        self.home_rating, self.away_rating, self.match_rating = compute_ratings(teams, home, away)
        home_win_coeffs, away_win_coeffs = get_coeffs()
        self.hwtp = float((Decimal(home_win_coeffs['beta_coeff']) * Decimal(self.match_rating) + Decimal(home_win_coeffs['constant'])) / Decimal(100))
        self.awtp = float((Decimal(away_win_coeffs['beta_squared_coeff']) * Decimal(self.match_rating**2) + Decimal(away_win_coeffs['beta_coeff'] * self.match_rating) + Decimal(home_win_coeffs['constant'])) / Decimal(100))
        self.dtp = 1 - self.hwtp - self.awtp

        if self.hwtp > 0:
            self.hwto = float(Decimal(1) / Decimal(self.hwtp))
        else:
            self.hwto = self.home_odds
        if self.awtp > 0:
            self.awto = float(Decimal(1) / Decimal(self.awtp))
        else:
            self.awto = self.away_odds
        if self.dtp > 0:
            self.tdo = float(Decimal(1) / Decimal(self.dtp))
        else:
            self.tdo = self.draw_odds

        self.hv = float(Decimal(self.hwtp) * Decimal(self.home_odds) - 1)
        self.dv = float(Decimal(self.dtp) * Decimal(self.draw_odds) - 1)
        self.av = float(Decimal(self.awtp) * Decimal(self.away_odds) - 1)

        staking_factory = StakingFactory()
        self.h = staking_factory.select_staking_strategy(self.bankroll[self.league]['bankroll'], self.staking_strategy, odds=self.home_odds, value=self.hv).compute()
        self.d = staking_factory.select_staking_strategy(self.bankroll[self.league]['bankroll'], self.staking_strategy, odds=self.draw_odds, value=self.dv).compute()
        self.a = staking_factory.select_staking_strategy(self.bankroll[self.league]['bankroll'], self.staking_strategy, odds=self.away_odds, value=self.av).compute()
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

            True Home Win Proba: {self.hwtp}
            True Draw Proba: {self.dtp}
            True Away Proba: {self.awtp}

            True Home Win Odds: {self.hwtp}
            True Draw Win Odds: {self.hwtp}
            True Away Win Odds: {self.hwtp}

            Home Win Value: {self.hv}
            Draw Value: {self.dv}
            Away Win Value: {self.av}

            Home Win Stake: {self.hv}
            Draw Stake: {self.dv}
            Away Win Stake: {self.av}
        """)

        return {
            'home_rating': self.home_rating,
            'away_rating': self.away_rating,
            'match_rating': self.match_rating,
            'hwto': self.hwto,
            'tdo': self.tdo,
            'awto': self.awto,
            'hwtp': self.hwtp,
            'dtp': self.dtp,
            'awtp': self.awtp,
            'hv': self.hv,
            'dv': self.dv,
            'av': self.av,
            'h': self.h,
            'd': self.d,
            'a': self.a,
            'bet': self.bet,
            'bet_odds': self.bet_odds,
            'value': self.value,
            'stake': self.stake,
            'flag': True if self.bet == 'home' else False
        }
    
def get_coeffs(config: dict, league: str):
    home_win_coeffs = config[league]['home']
    away_win_coeffs = config[league]['away']
    return home_win_coeffs, away_win_coeffs

def get_teams_list(df: DataFrame):
    lst = list(df.HomeTeam.unique())
    return lst

def group_data_by_teams(df: DataFrame, lst: List[str], curr_season: str):
    teams = {}
    for el in lst:
        teams[el] = df[(df.HomeTeam == el) | (df.AwayTeam == el)].copy()
        teams[el]['Season'] = curr_season
        teams[el]['Team'] = el
        games = [i for i in range(1, int(teams[el].count().iloc[0]) + 1)]
        teams[el]['Round'] = games.copy()
        teams[el].sort_values(by='Round', inplace=True)
        teams[el].loc[teams[el].HomeTeam == el, 'Rating'] = teams[el]['FTHG'] - teams[el]['FTAG']
        teams[el].loc[teams[el].AwayTeam == el, 'Rating'] = teams[el]['FTAG'] - teams[el]['FTHG']
        teams[el]['Rolling Average'] = teams[el]['Rating'].shift().rolling(6).sum()
    return teams
    
def compute_ratings(teams: Dict[str, DataFrame], home, away):
    home_rating = teams[home]['Rating'].rolling(6).sum().iloc[-1]
    away_rating = teams[away]['Rating'].rolling(6).sum().iloc[-1]

    if not home_rating or not away_rating:
        raise ValueError(f'Not enough data to execute match_ratings strategy for {home} - {away}.')
    
    match_rating = home_rating - away_rating
    return home_rating, away_rating, match_rating

def get_value(values, *args):
    val = max(args)
    
    if val == args[0]:
        return values[0]
    elif val == args[1]:
        return values[1]
    else:
        return values[2]


