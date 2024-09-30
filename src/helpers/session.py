import pickle
import os
import requests
from requests.adapters import HTTPAdapter
from urllib3.util import Retry

class SessionManager:
    def __init__(self, session_file='session.pkl'):
        self.session_file = session_file
        self.session = self.load_session()

    def load_session(self):
        if os.path.exists(self.session_file):
            with open(self.session_file, 'rb') as f:
                return pickle.load(f)
        return self.create_new_session()

    def create_new_session(self):
        session = requests.Session()
        retry = Retry(total=3, backoff_factor=0.1, status_forcelist=[500, 502, 503, 504])
        adapter = HTTPAdapter(max_retries=retry)
        session.mount('http://', adapter)
        session.mount('https://', adapter)
        return session

    def save_session(self):
        with open(self.session_file, 'wb') as f:
            pickle.dump(self.session, f)

    def get_session(self):
        return self.session
    
    # def __del__(self):
    #     self.save_session()