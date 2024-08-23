from typing import Dict, List
from staking.staking_factory import StakingFactory
from strategies.strategy import Strategy

from decimal import getcontext, Decimal

from pandas import DataFrame

class MatchRatingsStrategy(Strategy):
    possible_results = ['home', 'draw', 'away']
    possible_values = ['HV', 'DV', 'AV']
    
    def __init__(self, data, league, staking_strategy, bankroll, config, **kwargs) -> None:
        super(Strategy, self).__init__(data, league, staking_strategy, bankroll, config)
        self.home_odds = kwargs['home_odds']
        self.draw_odds = kwargs['draw_odds']
        self.away_odds = kwargs['away_odds']

    def compute(self, home: str, away: str):
        getcontext().prec = 3
        df = self.data.copy()
        df.reset_index()
        df = df[['HomeTeam', 'AwayTeam', 'FTHG', 'FTAG', 'FTR']]
        lst = get_teams_list(df)
        teams = group_data_by_teams(df, lst)
        self.home_rating, self.away_rating, self.match_rating = compute_ratings(teams, home, away)
        home_win_coeffs, away_win_coeffs = get_coeffs()
        self.hwtp = round((home_win_coeffs['beta_coeff'] * self.match_rating + home_win_coeffs['constant']) / 100, 1)
        self.awtp = round((away_win_coeffs['beta_squared_coeff'] * self.match_rating**2 + away_win_coeffs['beta_coeff'] * self.match_rating + home_win_coeffs['constant']) / 100, 1)
        self.dtp = 1 - self.hwtp - self.awtp

        if self.hwtp > 0:
            self.thwo = float(Decimal(1) / Decimal(self.hwtp))
        else:
            self.thwo = self.home_odds
        if self.awtp > 0:
            self.tawo = float(Decimal(1) / Decimal(self.awtp))
        else:
            self.tawo = self.away_odds
        if self.dtp > 0:
            self.tdo = float(Decimal(1) / Decimal(self.dtp))
        else:
            self.tdo = self.draw_odds

        self.hv = float(Decimal(self.hwtp) * Decimal(self.home_odds) - 1)
        self.dv = float(Decimal(self.dtp) * Decimal(self.draw_odds) - 1)
        self.av = float(Decimal(self.awtp) * Decimal(self.away_odds) - 1)

        staking_factory = StakingFactory()
        self.h = staking_factory.get_stake(self.bankroll, self.staking_strategy, odds=self.home_odds, value=self.hv)
        self.d = staking_factory.get_stake(self.bankroll, self.staking_strategy, odds=self.draw_odds, value=self.dv)
        self.a = staking_factory.get_stake(self.bankroll, self.staking_strategy, odds=self.away_odds, value=self.av)
        self.bet = get_value(self.possible_results, self.h, self.d, self.a)
        self.value = get_value(self.possible_values, self.hv, self.dv, self.av)
        self.stake = max(self.h, self.d, self.a, 0)

        return {
            'home_rating': self.home_rating,
            'away_rating': self.away_rating,
            'match_rating': self.match_rating,
            'hwtp': self.hwtp,
            'dtp': self.dtp,
            'awtp': self.awtp,
            'thwo': self.thwo,
            'tdo': self.tdo,
            'tawo': self.tawo,
            'hv': self.hv,
            'dv': self.dv,
            'av': self.av,
            'h': self.h,
            'd': self.d,
            'a': self.a,
            'bet': self.bet,
            'value': self.value,
            'stake': self.stake
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
        teams[el]['Match Rating'] = 0
    return teams
    
def compute_ratings(teams: Dict[str, DataFrame], home, away):
    home_rating = teams[home]['Rating'].rolling(6).sum().iloc[-1]
    away_rating = teams[away]['Rating'].rolling(6).sum().iloc[-1]
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


