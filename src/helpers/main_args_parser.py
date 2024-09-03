#!/usr/bin/python3

from optparse import OptionParser

def args_parser():
    parser = OptionParser('bet_bot_main -B <betting_strategy> -S <staking_strategy> -K <bookmaker>')
    parser.add_option("-B", dest="betting_strategy", type='string', help="specify betting strategy")
    parser.add_option("-S", dest="staking_strategy", type='string', help="specify staking strategy")
    parser.add_option("-K", dest="bookmaker", type='string', help="specify bookmaker")

    (options, args) = parser.parse_args()

    if (options.betting_strategy == None) | (options.staking_strategy == None) | (options.bookmaker == None):
        print(f'Usage: {parser.usage}')
        exit(1)

    return options
