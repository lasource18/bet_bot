import requests
from jproperties import Properties

from utils.utils import API_KEY, RAPIDAPI_HOST, DB_FILE, SQL_PROPERTIES

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

leagues = {'E0': '39', 'T1': '203', 'B1': '78', 'L1': '61', 'P1': '94'}

def main():
    for league, league_id in leagues.items():
        pass

if __name__ == '__main__':
    main()