from selenium import webdriver
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
import time
import random
import string

class BettingBot:
    def __init__(self, username, password):
        self.username = username
        self.password = password
        self.driver = self.setup_driver()

    def setup_driver(self):
        options = webdriver.ChromeOptions()
        
        # Randomize user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/14.1.1 Safari/605.1.15",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/92.0.4515.107 Safari/537.36"
        ]
        options.add_argument(f'user-agent={random.choice(user_agents)}')
        
        # Randomize window size
        window_sizes = [(1366, 768), (1920, 1080), (1440, 900)]
        window_size = random.choice(window_sizes)
        options.add_argument(f"window-size={window_size[0]},{window_size[1]}")
        
        # Disable automation flags
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)

        #
        # options.add_argument('--headless')  # Run in background
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        
        # Randomize HTTP headers
        options.add_argument(f"--accept-language={'en-US,en;q=0.9,' + ','.join([f'{random.choice(string.ascii_lowercase)}{random.choice(string.ascii_lowercase)};q=0.{random.randint(1,9)}' for _ in range(3)])}")
        
        driver = webdriver.Chrome(options=options)
        
        # Set random referer
        referers = [
            "https://www.google.com/",
            "https://www.bing.com/",
            "https://www.yahoo.com/",
            "https://www.reddit.com/"
        ]
        driver.execute_cdp_cmd('Network.setExtraHTTPHeaders', {"headers": {"Referer": random.choice(referers)}})
        
        return driver
    # https://guest.api.arcadia.pinnacle.com/0.1/sessions
    # https://api.arcadia.pinnacle.com/0.1/wallet/balance
    # 77c2157704026e08e2556ce8c0ce84e3751bb0680d93245bfc7b604a8c8c13de
    # WxlhYQHWMF7KSG8LrRk5gWUR28kIDnnF
    def human_like_input(self, element, text):
        # action = ActionChains(self.driver)
        # action.move_to_element(element)
        # action.click(element).perform()
        if element.is_enabled():
            for char in text:
                element.send_keys(char)
                time.sleep(random.uniform(0.1, 0.3))

    def human_like_mouse_movement(self, element):
        action = ActionChains(self.driver)
        action.move_by_offset(random.randint(-100, 100), random.randint(-100, 100))
        action.move_to_element(element)
        action.perform()

    def random_scroll(self):
        self.driver.execute_script(f"window.scrollTo(0, {random.randint(100, 500)});")
        time.sleep(random.uniform(0.5, 2))

    def simulate_tab_switching(self):
        current_handle = self.driver.current_window_handle
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        time.sleep(random.uniform(2, 5))
        self.driver.close()
        self.driver.switch_to.window(current_handle)

    def wait_for_element(self, by, value, timeout=10):
        return WebDriverWait(self.driver, timeout).until(
            EC.element_to_be_clickable((by, value))
        )



# Usage example
# if __name__ == "__main__":
#     bot = PinnacleBettingBot("your_username", "your_password")
#     bot.login()
#     odds = bot.check_odds("Team1", "Team2", "2024-08-21")
#     if odds:
#         print(f"Odds: {odds}")
#         bot.place_bet("Team1", "Team2", "2024-08-21", "Home", 10)