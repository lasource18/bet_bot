from datetime import datetime
from fractions import Fraction
import os
from typing import List
from bs4 import BeautifulSoup
from dotenv import load_dotenv

from logging import Logger
import requests
from requests.exceptions import RetryError
from requests_toolbelt import MultipartEncoder
from bot.betting_bot import BettingBot
from utils.utils import convert_odds, create_dir, extract_time

load_dotenv(override=True)

WILLIAM_HILL_BASE_URL = os.environ['WILLIAM_HILL_BASE_URL']
WILLIAM_HILL_SPORTS_URL = os.environ['WILLIAM_HILL_SPORTS_URL']
WILLIAM_HILL_AUTH_URL1 = os.environ['WILLIAM_HILL_AUTH_URL1']
WILLIAM_HILL_AUTH_URL2 = os.environ['WILLIAM_HILL_AUTH_URL2']
WILLIAM_HILL_TRANSACT_API = os.environ['WILLIAM_HILL_TRANSACT_API']

today = datetime.now().strftime('%Y-%m-%d')

class WilliamHillBot(BettingBot):
    def __init__(self, name):
        super().__init__(WILLIAM_HILL_BASE_URL)
        self.headers = {
            # 'Content-Type': 'application/json',
            # 'User-Agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Mobile Safari/537.36',
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Origin': 'https://www.sports.williamhill.com/betting/en-gb',
            "Referer": 'https://duckduckgo.com/',
            "Sec-Ch-Ua": '"Microsoft Edge";v="129","Not=A?Brand";v="8","Chromium"=;v="129"',
            "Sec-Ua-Platform": "Windows"
        }
        self.name = name
        # self.responses_directory_path = f'{RESPONSES_DIR}/{name}/{today}'
        # create_dir(self.responses_directory_path)

    def _get_cookie(self, logger):
        try:
            res = self.session.get(self.base_url, headers=self.headers)

            res.raise_for_status()

            req_cookies = res.cookies

            self.cookies = req_cookies

            # html = res.content
            # soup = BeautifulSoup(html, 'html.parser')

            # with open('./bookmakers_tests/test.html', mode='w', encoding='utf-8') as f:
            #     f.write(str(soup.prettify()))

        except requests.HTTPError as http_err:
            logger.error(f"Login failed | HTTP error occurred: {http_err}")
        except RetryError as retry_err:
            logger.error(f"Login failed | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"login(): Other error occurred: {err}")
        finally:
            self.base_url = WILLIAM_HILL_AUTH_URL1
    
    def login(self, credentials, logger, **kwargs):
        self._get_cookie(logger)

        if not self.cookies:
            logger.error('Failed to generate cokkies')

        try:
            login_url = f'{self.base_url}/login'

            self.headers['Content-Type'] = 'application/json'
            res1 = self.session.get(login_url, headers=self.headers, cookies=self.cookies)

            print('Hello')
            res1.raise_for_status()

            res_headers = res1.headers
            req_headers = res1.request.headers
            req_cookies = res1.cookies
            print('Response headers:', res_headers, 'Request headers:', req_headers, 'Response cookies:', req_cookies)

            req_id = res1.headers['RequestId']

            # data = res1.json()

            # {
            #     "recoverLoginUrl": "https://myaccount.williamhill.com/recovery/",
            #     "form_defaults": {
            #         "executionKey": "7c74ccf3-21b1-446e-a6da-466ded602ef4_ZXlKaGJHY2lPaUpJVXpVeE1pSXNJblI1Y0NJNklrcFhWQ0lzSW10cFpDSTZJamM0WXpNeE5UbG1MVFl3WlRFdE5HVmhOeTA1T1RJeUxXVmlNalkwTURsa01XTmhZeUo5LkozTEsxU212VGNqQUgtR2w1X3FodnhySm1PNU51dXlsZFhrcGF5Zk9rTU1VM3hkSU0xUUd0NXhlX2V6N0xVREdlekEzTEYtbUk4Vk5zcXhFNmdBS0RWbGRSUjdJTnhqYnZLV3h4V1I3RHcxbEtyM0JCYlpLeU5HUlBNTGQzampFeVg3UUJvT21tVHlvRHZ3aFB0c19Kd3NURnJxc2J2bmRTUkxVaFBQTUxwRHNnWVVYdHpoNnpZbk9YR3dGWVk3MUtnU0VGaW84dkdtTHhBTkVHWmpfc2lIOURwMXpzR29zMWwzYjhpRHNVcGp1WF9ib2FxendHSFduRW92TldvWEY0V091Rko5VHpIT0haYk5HR3VZQTJnczFpWXpmRzBCZWhORWFjRS1OaGY1VjlPTzEtM1UzbzVtQjFFVGRfcmJmZzRfMFp0Ny1kazB4VEVYVjRJMExQNVdTTnZpSncydU85X1JFaXAwakdwTC1TZkdkZzI3NjgtOU1nVURWb2RyclNBa3UzRXVhSU92LUFhamxpVDdCcmszQUtUdjlCZEJxbF9lVzlabHB0SnBHM1pZWG5WTG1yMlVUa2FFdFdjZ3JoWGxaQXEzUnFKQ0tPQ0hUZDNaNVZoNHlLUDVCQTJodHh5eTJuNWNGM2wzYkVJbnl5QzNCT3pRQ01melk3akVjXy1jblV1VHpoRTFFR0hYMnVKQTZ0Vjc0ZEFzVklaWlVralNxUmNuQm5fNVFvejNrT19rWVVHRXZMNlVYTjRrTE1xX2dHTk9Nc3RiR1V6anRDOWxneHdXZmdyWnBWSGVGeTV2QWVZa0tTVktvZzhuSERCeWd2dEJ0czhiLWFYZVJ1c045NVF2Q0Y4MWNNMllYUGx3MDdDX2hydlJ6cVdGQThsY2NjdUU4dm94d0RhX0h4enp6dW5QU0NCcHdNamtaYVp6dkc3aXpSbE5ZT2RiRkJYRG9OSnFrZjUycVlMNDZVcHk0WVhIX2tEVkhtLWNWTFZSSEtycDRwajN1WVRRWU1aWGh3OTlqZzZxbVREbWtiMTNOcm9lOUhOUmYyZV9ndkJvVXlTUVYtS2cyUnFlcGJOeTFpdDVIQUpZQUx6R0J0ZkpFRzA0RmxLMTc1ZnF5OW4zcU1BeFEya2lYMmlHbHItdkFHSnBfa09ZMXVWeTVjTVVycVNyX0stRkw4X3NJc3FPWUFod280UERPRHpSSFB2Q1hwQ2xSeERQRlkwejNTZXdQVnFXR1czeEoxcEhZVmpJZ0ttYWhsUG9CRVlZamVMcWUzWW1SczJDSVU0eWtRbTVOSVoyTHFNelhBUVQ1UHFZVkVfOFBpM09EMGcyQzVBbkFjVlViYlpIb1lMQU80S1RYeTRlR3VpeTRKWmIyNjdUcXIyTW5sOTdwR2JqanM5bXJqQ0RxMkFTd2t5RTJaVzM5bXZLLXhlZUpaTEVEaUxhZnR0dkt0S19ta1BxeTd2R05mak5Dc3RFSDhVakRVbDVCWks2WE1qMl90NlV3TlJQX2d5U2o4bW9jUlpPalUtSkNBVWI1d01FdW1KYldUYnIxd25Sc3p0U0k3ajN6b0pRV3RkRDk0QmFOLVNYRGsybk5WbEp4a3FQVWRSX2JxZzRkTE5nd3JaU1NvaWh1WExrc1JfT1ZBRTRydG5fd2VPcWUyaEtXOFpuTGxsdW5XMTN5eEdhNnJmMHhWUHQ4VnBKekJQMjZDdmxzOXA4N2prQlZlZ0s4VFNwSm90VFBJQ0tFaEMzRTNJdE9fZ29ILTNLSE1jdzFuQWs0SzMyYkhoeUljclpmNmVvX05ZSFEuS3Nyc2JUaHdaWHAyOEdJRldDU2x4VlgwSHZLS25UYloyQk9vUkRYSTF5cFdHcnNNRlZDNHUtVHFuVGdEY01RM1RpQ1NTOHBDNXc5cHFmSTJIalBoSkE=",
            #         "username": "lasource18",
            #         "password": "",
            #         "lt": "1",
            #         "rememberUsername": true,
            #         "keepMeLoggedIn": false,
            #         "_eventId": "submit"
            #     }
            # }

            logger.info(f'GET /login succeeded, code: {res1.status_code}. Trying to send form data now...')

            self.cookies = res1.cookies

            # res2 = self.session.get()

            form_data = MultipartEncoder(
                fields={
                    'username': credentials['username'],
                    'password': credentials['password'],
                    'rememberMe': 'false',
                    'rememberUsername': 'true',
                    '_rememberUsername': 'on',
                    '_rememberMe': 'off',
                    'lt': '1',
                    # 'execution': '',
                    '_eventId': 'submit'
                }
            )

            logger.info('Form data generated')

            self.headers['Content-Type'] = form_data.content_type

            res3 = self.session.post(login_url, headers=self.headers, cookies=self.cookies, data=form_data)

            res3.raise_for_status()

            self.cookies = res3.cookies

            logger.info(f'POST /login succeeded, code: {res3.status_code}')

            self.headers.pop('Content-Type')
            self.base_url = WILLIAM_HILL_SPORTS_URL
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
        try:
            today_ = kwargs.get('today', today)
            teams: List[str] = kwargs.get('teams', [])
            teams.append('Draw')

            league_name = kwargs.get('name', '')
        
            self.base_url['Referer'] = f'{self.base_url}/betting/en-gb/football/competitions/{league}/{league_name}/OB_MGMB/Match-Betting'
            url = f'{self.base_url}/data/foo01/wn-gb/pages/competitions/{league}/matches'

            games_urls = []

            res = self.session.get(url, headers=self.headers)

            res.raise_for_status()

            data = res.json()
            selections: dict = data['data']['selections']
            events: dict = data['data']['events']

            games: dict = {game['name']: game for game_id, game in selections.items() if selections[game_id]['name'] in teams} 
            games_urls = [{'id': game['id'], 'startTime': extract_time(game['startDateTime']), 'url': game['eventUrl'], 'home': game['name'].split('v')[0].trim(), 'away': game['name'].split('v')[1].trim()} for game in events.values()]
            
            id_mapping = {list(item.keys())[0]: list(item.values())[0]['id'] for item in games}

            # Now update each dictionary in list2 with the corresponding 'id' from list1

            for game_url in games_urls:
                home = games.get(game_url['home'], '')
                if home:
                    game_url['home_id'] = home['id'].replace('OB_OU', '')
                    game_url['home_odds'] = convert_odds(Fraction(home['currentPriceNum'], home['currentPriceDen']), 'fraction', 'decimal')
                
                draw = games.get('Draw', '')
                if draw:
                    game_url['draw_id'] = draw['id'].replace('OB_OU', '')
                    game_url['draw_odds'] = convert_odds(Fraction(draw['currentPriceNum'], draw['currentPriceDen']), 'fraction', 'decimal')
                
                away = games.get(game_url['away'], '')
                if away:
                    game_url['away_id'] = away['id'].replace('OB_OU', '')
                    game_url['away_odds'] = convert_odds(Fraction(away['currentPriceNum'], away['currentPriceDen']), 'fraction', 'decimal')

        except requests.HTTPError as http_err:
            logger.error(f"Failed to retrieve games for date {today_} | HTTP error occurred: {http_err} ")
        except RetryError as retry_err:
            logger.error(f"Failed to retrieve games for date {today_} | Retry Error: {retry_err}")
        except Exception as err:
            logger.error(f"get_game_urls(): Other error occurred: {err}")
        finally:
            logger.info(f'Games urls: {games_urls}')
            return games_urls

    def check_odds(self, url, logger: Logger, **kwargs):
        games_urls = kwargs.get('games_urls', [])
        home = kwargs.get('home', '')
        away = kwargs.get('away', '')

        if len(games_urls) == 0:
            logger.error(f'Failed to retrieve odds for {home} - {away}')
            return 0., 0., 0.
        
        game = next(game_url for game_url in games_urls if game_url['home']==home and game_url['away']==away)
        return game.get('home_odds', 0.),  game.get('draw_odds', 0.), game.get('away_odds', 0.)
    
    def get_max_min_stake(self, game_info, selection, odds, logger, **kwargs):
        return 1., 10_0000.0

    def place_bet(self, odds, stake, outcome, game_info, logger: Logger, **kwargs):
        # {"channel": "I", "selectionIds": [["24244114"]], "byoSelections": []}
        pass

    def logout(self, logger, **kwargs):
        try:
            success = False
            res = self.session.get(f'{self.base_url}/logout', headers=self.headers, cookies=self.cookies)

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
            