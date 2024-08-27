from datetime import datetime, timedelta
import json
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import os

import requests
from requests.exceptions import RetryError

from bot.betting_bot import BettingBot
from utils.utils import american_to_decimal, generate_uuid

load_dotenv(override=True)

PINNACLE_TRUST_CODE = os.environ['PINNACLE_TRUST_CODE']
PINNACLE_API = os.environ['PINNACLE_API']

class PinnacleBettingBot(BettingBot):
    def __init__(self):
        super().__init__(PINNACLE_API)
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'x-api-key': 'CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R',
            'Origin': 'https://www.pinnacle.com',
            'x-device-uuid': '2d48ff69-f28214f0-be75ed89-e341243e'
        }
    
    def login(self, username, password):
        login_url = f"{self.base_url}/sessions"
        payload = {
            'username': username,
            'password': password,
            'trustCode': PINNACLE_TRUST_CODE,
            'geolocation': ''
        }
        payload = json.dumps(payload)

        try:
            response = self.session.post(login_url, data=payload, headers=self.headers)
            data = response.json()
            with open('src/responses/login.json', 'w') as f:
                json.dump(data, f)

            response.raise_for_status()
            self.headers['X-Session'] = data.get('token', '')
            self.base_url = PINNACLE_API
        except requests.HTTPError as http_err:
            print(f"Login failed | HTTP error occurred: {http_err} ")
        except RetryError as err:
            print(f"Login failed | Retry Error: {err}")
        except Exception as err:
            print(f"login(): Other error occurred: {err.with_traceback()}")
        else:
            print("Login successful")
            return True
    
    def check_balance(self):
        balance_url = f"{self.base_url}/wallet/balance"
        response = self.session.get(balance_url, headers=self.headers)
        balance = 0.0

        try:
            data = response.json()
            with open('src/responses/check_balance.json', 'w') as f:
                json.dump(data, f)

            response.raise_for_status()
            balance = float(data['amount'])
        except requests.HTTPError as http_err:
            print(f"Failed to check balance | HTTP error occurred: {http_err} ")
        except RetryError as err:
            print(f"Failed to check balance | Retry Error: {err}")
        except Exception as err:
            print(f"check_balance(): Other error occurred: {err.with_traceback()}")
        finally:
            return balance
    
    def get_game_urls(self, league):
        try:
            params = {'brandId': 0}
            response = self.session.get(f'{self.base_url}/leagues/{league}/matchups', headers=self.headers, params=params)
            data = response.json()
            with open('src/responses/get_game_urls.json', 'w') as f:
                json.dump(data, f)

            response.raise_for_status()
            today = (datetime.now()+timedelta(1)).strftime('%Y-%m-%d')

            games = [value['parent'] for value in data]
            games = [game for game in games if game is not None]
        
            today_games = [game for game in games if datetime.fromisoformat(game['startTime']).astimezone(ZoneInfo("America/New_York")).strftime('%Y-%m-%d') == today]
            unique_games = {game['id']: game for game in today_games}
            games_filtered = list(unique_games.values())
            games_urls  =[{'id': game['id'], 'startTime': game['startTime'], 'url': f"{self.base_url}/matchups/{game['id']}/markets/related/straight", 'home': game['participants'][0]['name'], 'away': game['participants'][1]['name']} for game in games_filtered]
        except requests.HTTPError as http_err:
            print(f"Failed to retrieve games for {today} | HTTP error occurred: {http_err} ")
            return []
        except RetryError as err:
            print(f"Failed to retrieve games for {today} | Retry Error: {err}")
            return []
        except Exception as err:
            print(f"get_game_urls(): Other error occurred: {err.with_traceback()}")
            return []
        else:
            return games_urls
        
    def check_odds(self, url):
        try:
            response = self.session.get(url, headers=self.headers)
            data = response.json()
            with open('src/responses/check_odds.json', 'w') as f:
                json.dump(data, f)
            
            response.raise_for_status()

            straight_market = [market['prices'] for market in data if market['key']=='s;0;m' and 'isAlternate' in market.keys()]
            straight_market = straight_market[0]
            straight_market = {market['designation']: american_to_decimal(market['price']) for market in straight_market}
            odds = float(straight_market['home']), float(straight_market['draw']), float(straight_market['away'])
        except requests.HTTPError as http_err:
            print(f"Failed to retrieve the odds | HTTP error occurred: {http_err} ")
        except RetryError as err:
            print(f"Failed to retrieve the odds | Retry Error: {err}")
        except Exception as err:
            print(f"check_odds(): Other error occurred: {err.with_traceback()}")
        else:
            return odds
        
    def place_bet(self, odds, stake, outcome, game_info):
        try:
            # odds = self.check_odds(odds_url)
            if not odds:
                print("Unable to place bet - odds not found")
                return False

            if odds * stake - stake < .41 or stake < .41:
                print(f"Stake of {stake} too low, can't place bet on {game_info['home']} - {game_info['away']}")
                return False

            bet_url = f"{self.base_url}/bets/straight"
            payload = {
                "oddsFormat": "decimal",
                'requestId': generate_uuid(),
                "acceptBetterPrices": True,
                "class": "Straight",
                "selections": [
                    {
                        "matchupId": game_info['id'],
                        "marketKey": "s;0;m",
                        "designation": outcome,
                        "price": odds
                    }
                ],
                "stake": stake,
                "originTag": "l:bsd",
                "acceptBetterPrice": True
            }
            payload = json.dumps(payload)
            response = self.session.post(bet_url, data=payload, headers=self.headers)
            data = response.json()
            with open('src/responses/place_bet.json', 'w') as f:
                json.dump(data, f)
            
            response.raise_for_status()
        except requests.HTTPError as http_err:
            print(f"Failed to place bet | HTTP error occurred: {http_err}")
        except RetryError as err:
            print(f"Failed to place bet | Retry Error: {err}")
        except Exception as err:
            print(f"place_bet(): Other error occurred: {err.with_traceback()}")
        else:
            print(f"Bet placed successfully: {outcome} for {game_info['home']} - {game_info['away']}")
            return True
        