from bot.betting_bot import BettingBot

from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException
import random
import time

class PinnacleBettingBot(BettingBot):
    def __init__(self, username, password, **kwargs):
        super().__init__(username, password)
        self.base_url = "https://www.pinnacle.com/en/"

    def login(self):
        self.driver.get(f"{self.base_url}")
        try:
            username_field = self.wait_for_element(By.ID, "username")
            password_field = self.wait_for_element(By.ID, "password")
            # login_button = self.wait_for_element(By.ID, "login-button")
            login_button = self.wait_for_element(By.XPATH, '/html/body/div[2]/div[1]/div[1]/div[1]/div[3]/div[2]/div/div/div[4]/button')
            # self.random_scroll()
            # self.human_like_mouse_movement(username_field)
            self.human_like_input(username_field, self.username)
            print('Entered username')
            time.sleep(random.uniform(0.5, 1.5))
            
            # self.human_like_mouse_movement(password_field)
            self.human_like_input(password_field, self.password)
            print('Entered password')
            
            time.sleep(random.uniform(0.5, 1.5))
            
            # Simulate tab switching before clicking login
            self.simulate_tab_switching()
            
            self.human_like_mouse_movement(login_button)
            login_button.click()

            self.wait_for_element(By.ID, "account-menu")
            print("Login successful")
        except TimeoutException:
            print("Login failed - element not found")

    def check_odds(self, team1, team2, date):
        self.driver.get(f"{self.base_url}soccer/")

        try:
            search_box = self.wait_for_element(By.ID, "search-box")
            self.human_like_mouse_movement(search_box)
            self.human_like_input(search_box, f"{team1} vs {team2}")
            time.sleep(random.uniform(1.5, 3))

            match_link = self.wait_for_element(By.XPATH, f"//a[contains(text(), '{team1}') and contains(text(), '{team2}')]")
            self.human_like_mouse_movement(match_link)
            match_link.click()

            self.random_scroll()

            # Simulate tab switching while waiting for odds
            self.simulate_tab_switching()

            home_odds = self.wait_for_element(By.XPATH, "//div[contains(@class, 'home-team')]//span[contains(@class, 'odds')]")
            draw_odds = self.wait_for_element(By.XPATH, "//div[contains(@class, 'draw')]//span[contains(@class, 'odds')]")
            away_odds = self.wait_for_element(By.XPATH, "//div[contains(@class, 'away-team')]//span[contains(@class, 'odds')]")

            return (
                home_odds.text,
                draw_odds.text,
                away_odds.text
            )
        except TimeoutException:
            print("Failed to find match or odds")
            return None

    def place_bet(self, team1, team2, date, outcome, stake):
        odds = self.check_odds(team1, team2, date)
        if not odds:
            print("Unable to place bet - odds not found")
            return

        try:
            outcome_button = self.wait_for_element(By.XPATH, f"//div[contains(@class, '{outcome.lower()}')]//button")
            self.human_like_mouse_movement(outcome_button)
            outcome_button.click()

            stake_input = self.wait_for_element(By.ID, "stake-input")
            self.human_like_mouse_movement(stake_input)
            self.human_like_input(stake_input, str(stake))

            # Simulate tab switching before confirming bet
            self.simulate_tab_switching()

            confirm_button = self.wait_for_element(By.ID, "confirm-bet")
            self.human_like_mouse_movement(confirm_button)
            confirm_button.click()

            confirmation = self.wait_for_element(By.ID, "bet-confirmation")
            print("Bet placed successfully")
        except TimeoutException:
            print("Failed to place bet - element not found")

    def __del__(self):
        self.driver.quit()