from datetime import datetime, timedelta
import json
import random
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import os

import requests
from requests.exceptions import RetryError

from bot.betting_bot import BettingBot
from utils.utils import american_to_decimal, create_dir, generate_uuid

load_dotenv(override=True)

PINNACLE_TRUST_CODE = os.environ['PINNACLE_TRUST_CODE']
PINNACLE_GUEST_API = os.environ['PINNACLE_GUEST_API']
PINNACLE_API = os.environ['PINNACLE_API']

class PinnacleBettingBot(BettingBot):
    def __init__(self):
        super().__init__(PINNACLE_GUEST_API)
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'x-api-key': 'CmX2KcMrXuFmNg6YFbmTxE0y9CIrOi0R',
            'Origin': 'https://www.pinnacle.com',
            'x-device-uuid': '2d48ff69-f28214f0-be75ed89-e341243e'
        }
    
    def login(self, credentials, logger, **kwargs):
        today = kwargs.get('today', generate_uuid())
        login_url = f"{self.base_url}/sessions"
        payload = {
            'username': credentials['username'],
            'password': credentials['password'],
            'trustCode': PINNACLE_TRUST_CODE,
            'geolocation': ''
        }
        payload = json.dumps(payload)

        try:
            response = self.session.post(login_url, data=payload, headers=self.headers)
            data = response.json()

            directory_path = f'src/responses/{today}/login.json'

            create_dir(directory_path)

            with open(directory_path, 'w') as f:
                json.dump(data, f)

            response.raise_for_status()
            self.headers['X-Session'] = data.get('token', '')
            self.base_url = PINNACLE_API
        except requests.HTTPError as http_err:
            logger.error(f"Login failed | HTTP error occurred: {http_err}")
        except RetryError as err:
            logger.error(f"Login failed | Retry Error: {err}")
        except Exception as err:
            logger.error(f"login(): Other error occurred: {err}")
        else:
            return True
    
    def check_balance(self, logger, **kwargs):
        today = kwargs.get('today', generate_uuid())
        balance_url = f"{self.base_url}/wallet/balance"
        response = self.session.get(balance_url, headers=self.headers)
        balance = 0

        try:
            data = response.json()

            directory_path = f'src/responses/{today}/check_balance.json'

            create_dir(directory_path)

            with open(directory_path, 'w') as f:
                json.dump(data, f)

            response.raise_for_status()
            balance = float(data['amount'])
        except requests.HTTPError as http_err:
            logger.error(f"Failed to check balance | HTTP error occurred: {http_err} ")
        except RetryError as err:
            logger.error(f"Failed to check balance | Retry Error: {err}")
        except Exception as err:
            logger.error(f"check_balance(): Other error occurred: {err}")
        finally:
            logger.info(f'Current balance: {balance}')
            return balance
    
    def get_game_urls(self, league, logger, **kwargs):
        try:
            today = kwargs.get('today', generate_uuid())
            params = {'brandId': 0}
            response = self.session.get(f'{self.base_url}/leagues/{league}/matchups', headers=self.headers, params=params)
            data = response.json()

            directory_path = f'src/responses/{today}/get_game_urls_{league}.json'

            create_dir(directory_path)

            with open(directory_path, 'w') as f:
                json.dump(data, f)

            response.raise_for_status()

            games = [value['parent'] for value in data]
            games = [game for game in games if game is not None]
        
            today_games = [game for game in games if datetime.fromisoformat(game['startTime']).astimezone(ZoneInfo("America/New_York")).strftime('%Y-%m-%d') == today]
            unique_games = {game['id']: game for game in today_games}
            games_filtered = list(unique_games.values())
            games_urls  =[{'id': game['id'], 'startTime': game['startTime'], 'url': f"{self.base_url}/matchups/{game['id']}/markets/related/straight", 'home': game['participants'][0]['name'], 'away': game['participants'][1]['name']} for game in games_filtered]
        except requests.HTTPError as http_err:
            logger.error(f"Failed to retrieve games for date {today} | HTTP error occurred: {http_err} ")
            return []
        except RetryError as err:
            logger.error(f"Failed to retrieve games for date {today} | Retry Error: {err}")
            return []
        except Exception as err:
            logger.error(f"get_game_urls(): Other error occurred: {err}")
            return []
        else:
            logger.info(f'Games urls: {games_urls}')
            return games_urls
        
    def check_odds(self, url, logger, **kwargs):
        try:
            odds = 0
            today = kwargs.get('today', generate_uuid())
            game_id = kwargs.get('game_id', random.randint(0, 999_999))

            response = self.session.get(url, headers=self.headers)
            data = response.json()

            directory_path = f'src/responses/{today}/check_odds_{game_id}.json'
            create_dir(directory_path)

            with open(directory_path, 'w') as f:
                json.dump(data, f)
            
            response.raise_for_status()

            straight_market = [market['prices'] for market in data if market['key']=='s;0;m' and 'isAlternate' in market.keys()]
            straight_market = straight_market[0]
            straight_market = {market['designation']: american_to_decimal(market['price']) for market in straight_market}
            odds = float(straight_market['home']), float(straight_market['draw']), float(straight_market['away'])
        except requests.HTTPError as http_err:
            logger.error(f"Failed to retrieve the odds | HTTP error occurred: {http_err} ")
        except RetryError as err:
            logger.error(f"Failed to retrieve the odds | Retry Error: {err}")
        except Exception as err:
            logger.error(f"check_odds(): Other error occurred: {err}")
        else:
            return odds
    
    def get_max_min_stake(self, game_info, selection, odds, logger, **kwargs):
        try:
            logger = kwargs['logger']
            today = kwargs.get('today', generate_uuid())

            url = f"{self.base_url}/bets/straight/quote"
            payload = {
                        "oddsFormat": "decimal", 
                       "selections":[
                           {"matchupId": game_info['id'],
                            "marketKey":"s;0;m",
                            "designation": selection,
                            "price": odds}]
                        }
            payload = json.dumps(payload)
            response = self.session.post(url, data=payload, headers=self.headers)
            data = response.json()
            with open(f"src/responses/get_min_stake_{game_info['id']}_{today}.json", 'w') as f:
                json.dump(data, f)

            min_stake = 0
            max_stake = 10_000
            
            response.raise_for_status()

            limits = data['limits']
            for limit in limits:
                if limit['type'] == 'minRiskStake':
                    min_stake = float(limit['amount'])
                elif limit['type'] == 'maxRiskStake':
                    max_stake = float(limit['amount'])
        except requests.HTTPError as http_err:
            logger.error(f"Failed to get minimum stake | HTTP error occurred: {http_err}")
        except RetryError as err:
            logger.error(f"Failed to get minimum stake | Retry Error: {err}")
        except Exception as err:
            logger.error(f"get_min_stake(): Other error occurred: {err}")
        else:
            logger.info(f"Minimum stake for game {game_info['home']} - {game_info['away']}: {min_stake}")
            return min_stake, max_stake
        
    def place_bet(self, odds, stake, outcome, game_info, min_stake, logger, **kwargs):
        try:
            today = kwargs.get('today', generate_uuid())
            # odds = self.check_odds(odds_url)
            # if not odds:
            #     print("Unable to place bet - odds not found")
            #     return False

            if stake < min_stake:
                logger.info(f"Stake of {stake} too low, can't place bet on {game_info['home']} - {game_info['away']}")
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
            with open(f"src/responses/place_bet_{game_info['id']}_{today}.json", 'w') as f:
                json.dump(data, f)
            
            response.raise_for_status()
        except requests.HTTPError as http_err:
            logger.error(f"Failed to place bet | HTTP error occurred: {http_err}")
        except RetryError as err:
            logger.error(f"Failed to place bet | Retry Error: {err}")
        except Exception as err:
            logger.error(f"place_bet(): Other error occurred: {err}")
        else:
            logger.info(f"Bet placed successfully: {outcome} for {game_info['home']} - {game_info['away']}")
            return True
        