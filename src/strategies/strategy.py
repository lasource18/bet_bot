from abc import abstractmethod

class Strategy(object):
    def __init__(self, data, league, staking_strategy, bankroll, config) -> None:
        self.data = data
        self.league = league
        self.staking_strategy = staking_strategy
        self.bankroll = bankroll
        self.config = config

    @abstractmethod
    def compute(self, home: str, away: str):
        raise NotImplementedError('Method is required!')
    