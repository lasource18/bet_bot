from abc import abstractmethod

from logging import Logger
import time
import random

from helpers.session import SessionManager

class BettingBot:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session_manager = SessionManager()
        self.session = self.session_manager.get_session()

    @abstractmethod
    def login(self, credentials, logger: Logger, **kwargs):
        raise NotImplementedError('Method is required!')

    @abstractmethod
    def check_balance(self, logger: Logger, **kwargs):
        raise NotImplementedError('Method is required!')
    
    @abstractmethod
    def get_game_urls(self, league, logger: Logger, **kwargs):
        raise NotImplementedError('Method is required!')

    @abstractmethod
    def check_odds(self, url, logger: Logger, **kwargs):
        raise NotImplementedError('Method is required!')
    
    @abstractmethod
    def get_max_min_stake(self, game_info, selection, odds, logger, **kwargs):
        raise NotImplementedError('Method is required!')

    @abstractmethod
    def place_bet(self, odds, stake, outcome, game_info, logger: Logger, **kwargs):
        raise NotImplementedError('Method is required!')
    
    @abstractmethod
    def logout(self, logger: Logger, **kwargs):
        raise NotImplementedError('Method is required!')

    def simulate_human_behavior(self):
        time.sleep(random.uniform(1, 3))

    # def __del__(self):
    #     self.session_manager.save_session()
