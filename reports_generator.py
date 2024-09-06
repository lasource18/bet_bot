#!/usr/bin/python3

import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from datetime import datetime, timedelta
from jproperties import Properties

from helpers.logger import setup_logger
from helpers.reports_generator_args_parser import args_parser
from helpers.send_email import send_email
from utils.utils import DB_FILE, LOGS, REPORTS_DIR, SQL_PROPERTIES, CONFIG_FILE, create_dir, get_files_list, read_config

configs = Properties()
with open(SQL_PROPERTIES, 'rb') as config_file:
    configs.load(config_file)

# Function to load data from the database
def load_data(betting_strategy):
    match betting_strategy:
        case 'match_ratings':
            query = configs.get('GENERATE_MATCH_RATINGS_REPORTS').data
        case _:
            raise ValueError('Unknown betting strategy selected')

    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(query, conn)
        df['game_date'] = pd.to_datetime(df['game_date'])

    return df

# Function to filter data based on time periods
def filter_data(df: pd.DataFrame, period='daily'):
    today = datetime.today()
    if period == 'daily':
        start_date = today - timedelta(days=1)
    elif period == 'weekly':
        start_date = today - timedelta(weeks=1)
    elif period == 'monthly':
        start_date = today - timedelta(days=30)
    elif period == 'quarterly':
        start_date = today - timedelta(days=90)
    elif period == 'ytd':
        start_date = datetime(today.year, 1, 1)
    elif period == 'annual':
        start_date = today - timedelta(days=365)
    else:
        start_date = df['game_date'].min()

    filtered_df = df[df['game_date'] >= start_date]
    return filtered_df

# Function to generate and save reports
def generate_consolidated_reports(filtered_df: pd.DataFrame, period, betting_strategy, league_code, season):
    # Overall stats
    overall_stats = filtered_df.describe()

    # Grouped stats
    bookmaker_stats = filtered_df.groupby('bookmaker').agg(['mean', 'sum', 'min', 'max', 'count'])
    season_stats = filtered_df.groupby('season').agg(['mean', 'sum', 'min', 'max', 'count'])
    match_rating_stats = filtered_df.groupby('match_rating').agg(['mean', 'sum', 'min', 'max', 'count'])

    # Generate plots
    sns.set_theme(style="whitegrid")

    report_path = f"{REPORTS_DIR}/{betting_strategy}/{league_code}/{season}"
    create_dir(report_path)

    # Line chart of bankroll over time
    plt.figure(figsize=(10, 6))
    sns.lineplot(data=filtered_df, x='game_date', y='bankroll')
    plt.title(f'{period.capitalize()} Bankroll Over Time')
    plt.savefig(f'{report_path}/{period}_bankroll_over_time.png')
    plt.close()

    # Bar chart of profit by bookmaker
    plt.figure(figsize=(10, 6))
    sns.barplot(data=filtered_df, x='bookmaker', y='profit')
    plt.title(f'{period.capitalize()} Profit by Bookmaker')
    plt.savefig(f'{report_path}/{period}_profit_by_bookmaker.png')
    plt.close()

    # Save stats to CSV files
    overall_stats.to_csv(f'{report_path}/{period}_overall_stats.csv')
    bookmaker_stats.to_csv(f'{report_path}/{period}_bookmaker_stats.csv')
    season_stats.to_csv(f'{report_path}/{period}_season_stats.csv')
    match_rating_stats.to_csv(f'{report_path}/{period}_match_rating_stats.csv')

def generate_by_league_reports(filtered_df: pd.DataFrame, period, betting_strategy, league_code, season):
    # Grouped stats
    league_stats = filtered_df.groupby('league_code').agg(['mean', 'sum', 'min', 'max', 'count'])
    league_round_stats = filtered_df.groupby(['league_code', 'round']).agg(['mean', 'sum', 'min', 'max', 'count'])

    # Generate plots
    sns.set_theme(style="whitegrid")

    report_path = f"{REPORTS_DIR}/{betting_strategy}/{league_code}/{season}"
    create_dir(report_path)

    # Bar chart of profit by league_code
    plt.figure(figsize=(10, 6))
    sns.barplot(data=filtered_df, x='league_code', y='profit')
    plt.title(f'{period.capitalize()} Profit by League')
    plt.savefig(f"{report_path}/{period}_profit_by_league.png")
    plt.close()

    # Pie chart of bets by league_code
    plt.figure(figsize=(8, 8))
    filtered_df['league_code'].value_counts().plot.pie(autopct='%1.1f%%')
    plt.title(f'{period.capitalize()} Bets by League')
    plt.savefig(f"{report_path}/{period}_bets_by_league.png")
    plt.close()

    # Save stats to CSV files
    league_stats.to_csv(f'{report_path}/{period}_league_stats.csv')
    league_round_stats.to_csv(f'{report_path}/{period}_league_round_stats.csv')

# Main function to run all reports
def main(args):
    try:
        period = args.period.lower()
        betting_strategy = args.betting_strategy.lower()

        today = datetime.now().strftime('%Y-%m-%d')

        config = read_config(CONFIG_FILE)
        leagues = config.get('leagues', {})
        season = config.get('season', '2024-2025')

        log_file = f'{LOGS}/{betting_strategy}/reports/{season}/{today}_reports_generator.log'
        create_dir(log_file)
        logger = setup_logger('reports_generator', log_file)

        logger.info(f'Starting bet_bot:reports_generator {period} {betting_strategy}')

        df = load_data(betting_strategy)
        filtered_df = filter_data(df, period)
        
        for league in leagues.keys():
            logger.info(f'Generating reports for {league}')
            generate_by_league_reports(filtered_df, period, betting_strategy, league, season)
        logger.info(f'Generating consolidated report')
        generate_consolidated_reports(filtered_df, period, betting_strategy, 'Consolidated', season)

        subject = f'Reports generated for {betting_strategy} on {today}'
        messages = ['Reports attached herein:\n']
        files = get_files_list(f'{REPORTS_DIR}/{betting_strategy}')

        send_email(subject, messages, logger, files)

    except Exception as e:
        logger.error(e)
    else:
        logger.info(f'Successfully generated all the reports.')

if __name__ == "__main__":
    args = args_parser()
    main(args)
