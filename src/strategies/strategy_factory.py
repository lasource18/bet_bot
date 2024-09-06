from strategies.match_ratings import MatchRatingsStrategy

class StrategyFactory(object):
    def select_strategy(self, method, data, league, config, staking_strategy: str = 'kelly', **kwargs):
        strategy = get_betting_strategy(method)
        return strategy(data, league, staking_strategy, config, kwargs)
    
    def get_config(self, method):
        strategy = get_betting_strategy(method)
        return strategy.config_path

def get_betting_strategy(method: str):
    if method == 'match_ratings':
        return MatchRatingsStrategy
    else:
        raise ValueError(f'Wrong straregy {method} chosen')
    