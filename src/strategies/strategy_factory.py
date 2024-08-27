from strategies.match_ratings import MatchRatingsStrategy
from utils.utils import MATCH_RATINGS_PATTERN

import re

class StrategyFactory(object):
    def get_values(self, method, home, away, data, league, bankroll, config, staking_strategy: str = 'kelly', **kwargs):
        strategy = get_betting_strategy(method)
        return strategy(data, bankroll, league, staking_strategy, config, kwargs).compute(home, away)

def get_betting_strategy(method: str):
    if re.match(MATCH_RATINGS_PATTERN, method.lower()):
        return MatchRatingsStrategy
    else:
        raise ValueError(method)
    