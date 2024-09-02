from abc import abstractmethod

class Strategy(object):
    def __init__(self, data, league, staking_strategy, config) -> None:
        self.data = data
        self.league = league
        self.staking_strategy = staking_strategy
        self.config = config

    @abstractmethod
    def compute(self, home: str, away: str, betting_strategy, logger):
        raise NotImplementedError('Method is required!')
    