from bot.pinnacle_bot import PinnacleBettingBot

class BettingBotFactory(object):
    def select_betting_bot(self, username, password, choice: str = 'pinnacle', **kwargs):
        betting_bot = get_betting_bot(choice)
        return betting_bot()

def get_betting_bot(choice: str):
    if choice.lower() == 'pinnacle':
        return PinnacleBettingBot
    else:
        raise ValueError(choice)