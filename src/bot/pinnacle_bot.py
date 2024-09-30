from datetime import datetime, timedelta
import json
from logging import Logger
import random
from zoneinfo import ZoneInfo

from dotenv import load_dotenv
import os

import requests
from requests.exceptions import RetryError

from bot.betting_bot import BettingBot
from utils.utils import convert_odds, create_dir, extract_time, generate_uuid, DEVICE_UUID, RESPONSES_DIR

load_dotenv(override=True)

PINNACLE_TRUST_CODE = os.environ['PINNACLE_TRUST_CODE']
PINNACLE_GUEST_API_URL = os.environ['PINNACLE_GUEST_API_URL']
PINNACLE_API_URL = os.environ['PINNACLE_API_URL']
PINNACLE_API_KEY = os.environ['PINNACLE_API_KEY']

today = datetime.now().strftime('%Y-%m-%d')

class PinnacleBettingBot(BettingBot):
    def __init__(self, name):
        super().__init__(PINNACLE_GUEST_API_URL)
        self.headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'x-api-key': PINNACLE_API_KEY,
            'Origin': 'https://www.pinnacle.com',
            'x-device-uuid': DEVICE_UUID
        }
        self.name = name
        self.responses_directory_path = f'{RESPONSES_DIR}/{today}'
        create_dir(self.responses_directory_path)
    
    def login(self, credentials, logger: Logger, **kwargs):
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

            with open(f'{self.responses_directory_path}/{self.name}/login.json', 'w') as f:
                json.dump(data, f, indent=4)

            response.raise_for_status()
            self.headers['X-Session'] = data.get('token', '')
            self.base_url = PINNACLE_API_URL
        except requests.HTTPError as http_err:
            logger.error(f"Login failed | HTTP error occurred: {http_err}")
        except RetryError as retry_err:
            logger.error(f"Login failed | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"login(): Other error occurred: {err}")
        else:
            return True
    
    def check_balance(self, logger: Logger, **kwargs):
        try:
            balance = 0

            balance_url = f"{self.base_url}/wallet/balance"
            response = self.session.get(balance_url, headers=self.headers)
            data = response.json()

            with open(f'{self.responses_directory_path}/{self.name}/check_balance.json', 'w') as f:
                json.dump(data, f, indent=4)

            response.raise_for_status()
            balance = float(data['amount'])
        except requests.HTTPError as http_err:
            logger.error(f"Failed to check balance | HTTP error occurred: {http_err} ")
        except RetryError as retry_err:
            logger.error(f"Failed to check balance | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"check_balance(): Other error occurred: {err}")
        else:
            logger.info(f'Current balance: ${balance}')
        finally:
            return balance
    
    def get_game_urls(self, league, logger: Logger, **kwargs):
        games_urls = []

        try:
            today_ = kwargs.get('today', today)
            params = {'brandId': 0}
            response = self.session.get(f'{self.base_url}/leagues/{league}/matchups', headers=self.headers, params=params)
            data = response.json()

            with open(f'{self.responses_directory_path}/{self.name}/get_game_urls_{league}.json', 'w') as f:
                json.dump({'data': data}, f, indent=4)

            response.raise_for_status()

            games = [value['parent'] for value in data]
            games = [game for game in games if game is not None]
            games_ids = [game['id'] for game in games if game is not None]
            potentially_missed_games = [{'id': value['id'], 'participants': value['participants'], 'startTime': value['startTime']} for value in data if value['id'] not in games_ids and value['parlayRestriction']=='unique_matchups']
            games.extend(potentially_missed_games)
        
            today_games = [game for game in games if datetime.fromisoformat(game['startTime']).astimezone(ZoneInfo("America/New_York")).strftime('%Y-%m-%d') == today_]
            unique_games = {game['id']: game for game in today_games}
            games_filtered = list(unique_games.values())
            games_urls = [{'id': game['id'], 'startTime': extract_time(game['startTime']), 'url': f"{self.base_url}/matchups/{game['id']}/markets/related/straight", 'home': game['participants'][0]['name'], 'away': game['participants'][1]['name']} for game in games_filtered]
        except requests.HTTPError as http_err:
            logger.error(f"Failed to retrieve games for date {today} | HTTP error occurred: {http_err} ")
        except RetryError as retry_err:
            logger.error(f"Failed to retrieve games for date {today} | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"get_game_urls(): Other error occurred: {err}")
        finally:
            logger.info(f'Games urls: {games_urls}')
            return games_urls
        
    def check_odds(self, url, logger: Logger, **kwargs):
        try:
            odds = 0., 0., 0.
            game_id = kwargs.get('game_id', random.randint(0, 999_999))

            response = self.session.get(url, headers=self.headers)
            data = response.json()

            with open(f'{self.responses_directory_path}/{self.name}/check_odds_{game_id}.json', 'w') as f:
                json.dump({'data': data}, f, indent=4)
            
            response.raise_for_status()

            straight_market = [market['prices'] for market in data if market['key']=='s;0;m' and 'isAlternate' in market.keys()]
            straight_market = straight_market[0]
            straight_market = {market['designation']: convert_odds(market['price'], 'american', 'decimal') for market in straight_market}
            odds = float(straight_market['home']), float(straight_market['draw']), float(straight_market['away'])
        except requests.HTTPError as http_err:
            logger.error(f"Failed to retrieve the odds | HTTP error occurred: {http_err} ")
        except RetryError as retry_err:
            logger.error(f"Failed to retrieve the odds | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"check_odds(): Other error occurred: {err}")
        finally:
            return odds
    
    def get_max_min_stake(self, game_info, selection, odds, logger: Logger, **kwargs):
        try:
            min_stake = 1
            max_stake = 10_000

            game_id = game_info['id']

            url = f"{self.base_url}/bets/straight/quote"
            payload = {
                        "oddsFormat": "decimal", 
                       "selections":[
                           {"matchupId": game_id,
                            "marketKey":"s;0;m",
                            "designation": selection,
                            "price": odds}]
                        }
            payload = json.dumps(payload)
            response = self.session.post(url, data=payload, headers=self.headers)
            data = response.json()
            
            with open(f'{self.responses_directory_path}/{self.name}/get_min_max_stake_{game_id}.json', 'w') as f:
                json.dump(data, f, indent=4)
            
            response.raise_for_status()

            limits = data['limits']
            for limit in limits:
                if limit['type'] == 'minRiskStake':
                    min_stake = float(limit['amount'])
                elif limit['type'] == 'maxRiskStake':
                    max_stake = float(limit['amount'])
        except requests.HTTPError as http_err:
            logger.error(f"Failed to get minimum stake | HTTP error occurred: {http_err}")
        except RetryError as retry_err:
            logger.error(f"Failed to get minimum stake | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"get_min_stake(): Other error occurred: {err}")
        else:
            logger.info(f"Minimum stake for game {game_info['home']} - {game_info['away']}: {min_stake}")
        finally:
            return min_stake, max_stake
        
    def place_bet(self, odds, stake, outcome, game_info, min_stake, logger: Logger, **kwargs):
        try:
            # odds = self.check_odds(odds_url)
            # if not odds:
            #     print("Unable to place bet - odds not found")
            #     return False

            success = False

            if stake < min_stake:
                logger.info(f"Stake of {stake} too low, can't place bet on {game_info['home']} - {game_info['away']}")
                return success
            
            game_id = game_info['id']

            bet_url = f"{self.base_url}/bets/straight"
            payload = {
                "oddsFormat": "decimal",
                'requestId': generate_uuid(),
                "acceptBetterPrices": True,
                "class": "Straight",
                "selections": [
                    {
                        "matchupId": game_id,
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
            with open(f"{self.responses_directory_path}/{self.name}/place_bet_{game_id}.json", 'w') as f:
                json.dump(data, f, indent=4)
            
            response.raise_for_status()
        except requests.HTTPError as http_err:
            logger.error(f"Failed to place bet | HTTP error occurred: {http_err}")
        except RetryError as retry_err:
            logger.error(f"Failed to place bet | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"place_bet(): Other error occurred: {err}")
        else:
            logger.info(f"Bet placed successfully: {outcome} for {game_info['home']} - {game_info['away']}")
            success = True
        finally:
            return success
    
    def logout(self, logger: Logger, **kwargs):
        logout_url = f"{self.base_url}/sessions/{self.headers['X-Session']}"
        success = False

        try:
            response = self.session.delete(logout_url, headers=self.headers)
            data = response.json()

            with open(f'{self.responses_directory_path}/{self.name}/logout.json', 'w') as f:
                json.dump(data, f, indent=4)

            response.raise_for_status()

            success = True

        except requests.HTTPError as http_err:
            logger.error(f"Login failed | HTTP error occurred: {http_err}")
        except RetryError as retry_err:
            logger.error(f"Login failed | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"login(): Other error occurred: {err}")
        finally:
            return success
    