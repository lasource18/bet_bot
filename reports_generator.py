#!/usr/bin/python3

from logging import Logger
import sys
import os
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
def load_data(query):
    with sqlite3.connect(DB_FILE) as conn:
        df = pd.read_sql_query(query, conn)
        df['game_date'] = pd.to_datetime(df['game_date'])
        df.set_index('game_date', inplace=True)

    return df

# def resample_data(df: pd.DataFrame, period):
#     today = datetime.today()

#     if period == 'daily':
#         resampled_df = df.copy()
#     elif period == 'weekly':
#         resampled_df = df.resample('W').agg({
#             'profit': 'sum', 
#             'bankroll': 'mean', 
#             'stake': 'sum',
#             'vig': 'mean',
#             'match_rating': 'mean',
#             'yield': 'mean'
#         })
#     elif period == 'monthly':
#         resampled_df = df.resample('M').agg({
#             'profit': 'sum', 
#             'bankroll': 'mean', 
#             'stake': 'sum',
#             'vig': 'mean',
#             'match_rating': 'mean',
#             'yield': 'mean'
#         })
#     elif period == 'quarterly':
#         resampled_df = df.resample('Q').agg({
#             'profit': 'sum', 
#             'bankroll': 'mean', 
#             'stake': 'sum',
#             'vig': 'mean',
#             'match_rating': 'mean',
#             'yield': 'mean'
#         })
#     elif period == 'year-to-date':
#         # Resample by year-to-date and aggregate
#         start_date = datetime(today.year, 1, 1)
#         resampled_df = df[df.index >= start_date].resample('D').agg({
#             'profit': 'sum', 
#             'bankroll': 'mean', 
#             'stake': 'sum',
#             'vig': 'mean',
#             'match_rating': 'mean',
#             'yield': 'mean'
#         })
#     elif period == 'annual':
#         resampled_df = df.resample('A').agg({
#             'profit': 'sum', 
#             'bankroll': 'mean', 
#             'stake': 'sum',
#             'vig': 'mean',
#             'match_rating': 'mean',
#             'yield': 'mean'
#         })
#     else:
#         raise ValueError(f"Unknown period: {period}")
    
#     return resampled_df

# Function to generate and save reports
def generate_reports(df: pd.DataFrame, report_path, logger: Logger):
    # resampled_df = resample_data(df, period)
    df = df[(df['result'] == 'W') | (df['result'] == 'L')].round(2)

    # Overall stats
    overall_stats = df.describe()

    logger.info('Generating grouped stats')

    # Grouped stats
    numeric_cols = ['profit', 'vig', 'stake', 'match_rating', 'yield']
    bookmaker_stats = df.groupby('bookmaker')[numeric_cols].agg(['mean', 'sum', 'min', 'max', 'count']).round(2)
    match_rating_stats = df.groupby('match_rating')[numeric_cols].agg(['mean', 'sum', 'min', 'max', 'count']).round(2)
    league_stats = df.groupby('league_code')[numeric_cols].agg(['mean', 'sum', 'min', 'max', 'count']).round(2)

    # Generate plots
    sns.set_theme(style="whitegrid")

    logger.info('Generating horizontal bar chart for average stake per league_code')

    # Horizontal bar chart for average stake per league_code
    plt.figure(figsize=(10, 6))
    avg_stake = df.groupby('league_code')['stake'].mean().round(2).sort_values()
    ax = avg_stake.plot(kind='barh', color='skyblue')

    # Add the value of each bar on the chart
    for index, value in enumerate(avg_stake):
        ax.text(value, index, f'{value:.2f}', va='center')  # Annotate each bar with its value

    plt.title(f'Average Stake per League')
    plt.xlabel('Average Stake')
    plt.ylabel('League')
    plt.tight_layout()
    plt.savefig(f'{report_path}/charts/average_stake_per_league.png')
    plt.close()

    logger.info('Generating bar chart of profit by league')

    # Bar chart of profit by league
    plt.figure(figsize=(10, 6))
    # sns.barplot(data=bookmaker_stats.reset_index(), x='bookmaker', y=('profit', 'sum'))
    profit_sum = df.groupby('league_code')['profit'].sum().round(2).sort_values()
    ax = profit_sum.plot(kind='bar', color='grey')

    # Add the value of each bar on the chart
    for index, value in enumerate(profit_sum):
        ax.text(value, index, f'{value:.2f}', va='center')  # Annotate each bar with its value

    plt.title(f'Profit by League')
    plt.tight_layout()
    plt.savefig(f'{report_path}/charts/profit_by_league.png')
    plt.close()

    logger.info('Generating bar chart of yield by bookmaker')

    # Bar chart of yield by bookmaker
    plt.figure(figsize=(10, 6))
    # sns.barplot(data=bookmaker_stats.reset_index(), x='bookmaker', y=('yield', 'mean'))
    avg_yield = df.groupby('bookmaker')['yield'].mean().round(2).sort_values()
    ax = avg_yield.plot(kind='bar', color='yellow')

    # Add the value of each bar on the chart
    for index, value in enumerate(avg_yield):
        ax.text(index, value, f'{value:.2f}%', ha='center')

    plt.title(f'Yield by Bookmaker')
    plt.tight_layout()
    plt.savefig(f'{report_path}/charts/avg_yield_by_bookmaker.png')
    plt.close()

    logger.info('Generating bar chart of vig by bookmaker')

    # Bar chart of vig by bookmaker
    plt.figure(figsize=(10, 6))
    # sns.barplot(data=bookmaker_stats.reset_index(), x='bookmaker', y=('vig', 'mean'))
    avg_vig = df.groupby('bookmaker')['vig'].mean().round(2).sort_values()
    ax = avg_vig.plot(kind='barh', color='red')

    # Add the value of each bar on the chart
    for index, value in enumerate(avg_vig):
        ax.text(value, index, f'{value:.2f}%', va='center')  # Annotate each bar with itVig by Bookmaker')
    plt.title(f'Average vig by Bookmaker')
    plt.tight_layout()
    plt.savefig(f"{report_path}/charts/avg_vig_by_bookmaker.png")
    plt.close()

    logger.info('Generating boxplot of match_ratings by league_code')
    # Generate boxplot of match_ratings by league_code
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='league_code', y='match_rating')
    plt.title(f'Match Ratings Dispersion by League')
    plt.tight_layout()
    plt.savefig(f"{report_path}/charts/match_ratings_dispersion_by_league.png")
    plt.close()

    logger.info('Generating boxplot of profit by league_code')

    # Generate boxplot of profit by league_code
    plt.figure(figsize=(10, 6))
    sns.boxplot(data=df, x='league_code', y='profit')
    plt.title(f'Profit Dispersion by League')
    plt.tight_layout()
    plt.savefig(f"{report_path}/charts/profit_dispersion_by_league.png")
    plt.close()

    logger.info('Generating pie chart of bets by league_code')

    # Pie chart of bets by league_code
    plt.figure(figsize=(8, 8))
    df['league_code'].value_counts().plot.pie(autopct='%1.1f%%')
    plt.title(f'Bets by League')
    plt.tight_layout()
    plt.savefig(f"{report_path}/charts/bets_by_league.png")
    plt.close()

    logger.info('Generating win rate by league_code')

    # Win rate per league_code
    plt.figure(figsize=(10, 6))
    total_bets = df.groupby('league_code')['result'].count()
    success_bets = df[df['result'] == 'W']
    success_count = success_bets.groupby('league_code')['result'].count()
    win_rate_per_league = (success_count / total_bets) * 100
    win_rate_per_league.fillna(0, inplace=True)
    ax = win_rate_per_league.round(2).sort_values().plot(kind='barh', color='lightgreen')

    # Add the percentage on the chart
    for index, value in enumerate(win_rate_per_league.sort_values()):
        ax.text(value, index, f'{value:.2f}%', va='center')  # Annotate each bar with its win rate

    plt.title('Win Rate per League (%)')
    plt.xlabel('Win Rate (%)')
    plt.ylabel('League')
    plt.tight_layout()
    plt.savefig(f'{report_path}/charts/win_rate_per_league_percentage.png')
    plt.close()

    logger.info('Saving stats to csv')

    # Save stats to CSV files
    league_stats.T.to_csv(f'{report_path}/reports/league_stats.csv')
    overall_stats.T.to_csv(f'{report_path}/reports/overall_stats.csv')
    bookmaker_stats.T.to_csv(f'{report_path}/reports/bookmaker_stats.csv')
    match_rating_stats.T.to_csv(f'{report_path}/reports/match_rating_stats.csv')

    wr = round(success_bets['result'].count() / df.shape[0] * 100, 2)
    profit = df['profit'].sum().round(2)

    return wr, profit

# Main function to run all reports
def main(args):
    try:
        betting_strategy = args.betting_strategy.lower()

        today = (datetime.now()).strftime('%Y-%m-%d')

        config = read_config(CONFIG_FILE)
        season = config.get('season', '2024-2025')
        strategies_list = config.get('strategies', [])

        if betting_strategy in strategies_list:
            log_path = f'{LOGS}/{betting_strategy}/reports/{season}'
            create_dir(log_path)
            logger = setup_logger('reports_generator', f'{log_path}/{today}_reports_generator.log' )

            logger.info(f'Starting bet_bot:reports_generator {betting_strategy}')

            match betting_strategy:
                case 'match_ratings':
                    query = configs.get('GENERATE_MATCH_RATINGS_REPORTS').data.replace('\"', '')
                case _:
                    raise ValueError('Unknown betting strategy selected')

            df = load_data(query)

            if len(df) == 0:
                raise ValueError('Not enough data to generate report')

            logger.info(f'Generating reports and charts')

            report_path = f"{REPORTS_DIR}/{betting_strategy}/{season}"
            create_dir(report_path)

            wr, profit = generate_reports(df, report_path, logger)

            subject = f'Reports generated for {betting_strategy} on {today}'
            messages = [f'Current win rate: {wr}%', f'Current profit: ${profit}\n\n', 'Reports attached herein:\n']
            files = get_files_list(report_path)

            logger.info(f'Files list: {files}')

            send_email(messages, subject, logger, files)
        else:
            print('Unknown betting strategy or empty strategies list from config')
            exit(1)
    except Exception as e:
        e_type, e_object, e_traceback = sys.exc_info()
        e_filename = os.path.split(
            e_traceback.tb_frame.f_code.co_filename
        )[1]
        e_line_number = e_traceback.tb_lineno
        logger.error(f'{e}, type: {e_type}, filename: {e_filename}, line: {e_line_number}')
    else:
        logger.info(f'Successfully generated all the reports.')

if __name__ == "__main__":
    args = args_parser()
    main(args)
