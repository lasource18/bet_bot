from bot.pinnacle_bot import PinnacleBettingBot
from bot.william_hill_bot import WilliamHillBot

class BettingBotFactory(object):
    def select_betting_bot(self, choice: str = 'pinnacle', **kwargs):
        betting_bot = get_betting_bot(choice)
        return betting_bot(choice)

def get_betting_bot(choice: str):
    if choice.lower() == 'pinnacle':
        return PinnacleBettingBot
    elif choice.lower() == 'william_hill':
        return WilliamHillBot
    else:
        raise ValueError(f'Unknown bookmaker {choice} selected')
    