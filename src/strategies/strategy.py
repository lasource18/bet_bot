from abc import abstractmethod

class Strategy(object):
    def __init__(self, data, league, strat_config, staking_strategy, **kwargs) -> None:
        self.data = data
        self.league = league
        self.strat_config = strat_config
        self.staking_strategy = staking_strategy

    @abstractmethod
    def compute(self, home: str, away: str, betting_strategy, logger):
        raise NotImplementedError('Method is required!')
    