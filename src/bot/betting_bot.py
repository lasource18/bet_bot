from abc import abstractmethod

import time
import random

import sys
sys.path.append()

from helpers.session import SessionManager

class BettingBot:
    def __init__(self, base_url):
        self.base_url = base_url
        self.session_manager = SessionManager()
        self.session = self.session_manager.get_session()

    @abstractmethod
    def login(self, username, password):
        raise NotImplementedError('Method is required!')

    @abstractmethod
    def check_balance(self):
        raise NotImplementedError('Method is required!')
    
    @abstractmethod
    def get_game_urls(self, league, **params):
        raise NotImplementedError('Method is required!')

    @abstractmethod
    def check_odds(self, url):
        raise NotImplementedError('Method is required!')

    @abstractmethod
    def place_bet(self, odds, stake, outcome, game_info):
        raise NotImplementedError('Method is required!')

    def simulate_human_behavior(self):
        time.sleep(random.uniform(1, 3))

    # def __del__(self):
    #     self.session_manager.savep12 _session()

# Usage example
# if __name__ == "__main__":
#     bot = BettingBot("https://guest.api.arcadia.pinnacle.com/0.1")
#     if bot.login("cmguinan@yahoo.fr", "raxnux-Pehmac-fycbo5"):
#         bot.simulate_human_behavior()
        
#         balance = bot.check_balance()
#         if balance:
#             print(f"Current balance: ${balance}")

#         bot.simulate_human_behavior()

#         games = bot.get_game_urls('https://api.arcadia.pinnacle.com/0.1/leagues/1980/matchups', brandId=0)

#         game = [game for game in games if game['home']=='Manchester City']
#         print(game)
        
#         odds = bot.check_odds(game[0]['url'])
#         if odds:
#             print(f"Odds: {odds}")

#         bot.simulate_human_behavior()
        
#         bot.place_bet(odds[0], 1, 'home', game[0])