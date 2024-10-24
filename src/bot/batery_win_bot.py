import datetime
import json
from logging import Logger
import random

import requests
from requests.exceptions import RetryError
from bot.betting_bot import BettingBot

from dotenv import load_dotenv
import os

from utils.utils import RESPONSES_DIR, create_dir, gen_hmac_sha512_hash, gen_pbkdf2_sha512_hash, gen_sha512_hash

load_dotenv(override=True)

BATERY_WIN_API_URL = os.environ['BATERY_WIN_API_URL']
DEVICE_ID = os.environ['DEVICE_ID']

today = datetime.datetime.now().strftime('%Y-%m-%d')

class BateryWinBot(BettingBot):
    def __init__(self, name):
        super().__init__(BATERY_WIN_API_URL)
        self.headers = {
            # 'Content-Type': 'application/json',
            # 'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://batery.win',
            "Referer": 'https://batery.win/',
            "Sec-Ch-Ua": '"Microsoft Edge";v="129","Not=A?Brand";v="8","Chromium"=;v="129"',
            "Sec-Ua-Platform": "Windows"
        }
        self.name = name
        self.responses_directory_path = f'{RESPONSES_DIR}/{name}/{today}'
        create_dir(self.responses_directory_path)
    
    def login(self, credentials, logger: Logger, **kwargs):
        login_url = f"{self.base_url}/session/login/createProcess"
        pwd = credentials['password']
        payload = {
            'appVersion': f'1.39.91, Fri, 18 Oct 2024 10:54:14 GMT',
            # 'password': credentials['password'],
            'deviceId': DEVICE_ID,
            'sysId': 21,
            "scopeMarket": "2100",
            'lang': 'en',
            'loginMethod': 'email',
            'loginIdent': credentials['username'],
            'timestamp': datetime.datetime.now(tz=datetime.timezone.utc).strftime('%Y-%m-%d %H:%M:%S'),
            'random': f'{random.random()} ;-)',
            'sign': 'secret password',
        }

        p = json.dumps(payload)

        pwd = gen_sha512_hash(p)
        # sign = gen_pbkdf2_sha512_hash(pwd, p, 12)
        sign = gen_hmac_sha512_hash(pwd, p)

        payload['sign'] = sign
        # payload.update({
        #     # 'appVersion': f'1.39.91, {datetime.datetime.now(tz=datetime.timezone.utc).strftime("%a, %d %b %Y %H:%M:%S GMT")}',
        #     'appVersion': f'1.39.91, Fri, 18 Oct 2024 10:54:14 GMT',
        #     # 'password': credentials['password'],
        #     'deviceId': f'{DEVICE_ID}',
        #     'sysId': 21,
        #     "scopeMarket": "2100",
        # })

        print('Payload:', payload)
        payload = json.dumps(payload)

        try:
            response = self.session.post(login_url, data=payload, headers=self.headers)
            data = response.json()

            with open(f'{self.responses_directory_path}/login.json', 'w') as f:
                json.dump(data, f, indent=4)

            response.raise_for_status()

            print('Response headers:', response.headers)
            print('Request headers', response.request.headers)
            print('Cookies', response.cookies)
            # self.headers['X-Session'] = data.get('token', '')
            # self.base_url = PINNACLE_API_URL

            # logger.info(data)
        except requests.HTTPError as http_err:
            logger.error(f"Login failed | HTTP error occurred: {http_err}")
        except RetryError as retry_err:
            logger.error(f"Login failed | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"login(): Other error occurred: {err}")
        else:
            return True

    
    def check_balance(self, logger: Logger, **kwargs):
        pass
    
    
    def get_game_urls(self, league, logger: Logger, **kwargs):
        pass

    
    def check_odds(self, url, logger: Logger, **kwargs):
        pass
    
    
    def get_max_min_stake(self, game_info, selection, odds, logger, **kwargs):
        pass

    
    def place_bet(self, odds, stake, outcome, game_info, logger: Logger, **kwargs):
        pass
    
    
    def logout(self, logger: Logger, **kwargs):
        try:
            success = False
            payload = {'did': None, 'p': 1}

            res = self.session.post(f'{self.base_url}/logout?userDetails', headers=self.headers, data=payload, cookies=self.cookies)

            res.raise_for_status()

            success = True

            logger.info(f'Logged out successfully, code: {res.status_code}')

        except requests.HTTPError as http_err:
            logger.error(f"Logout failed | HTTP error occurred: {http_err}")
        except RetryError as retry_err:
            logger.error(f"Logout failed | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"logout(): Other error occurred: {err}")
        finally:
            return success