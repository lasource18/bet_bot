#!/usr/bin/python3

from optparse import OptionParser

def args_parser():
    parser = OptionParser('bet_bot_reports_generator -B <betting_strategy> -P <period>')
    parser.add_option("-B", dest="betting_strategy", type='string', help="specify betting strategy")
    parser.add_option("-B", dest="period", type='string', help="specify the period")

    (options, args) = parser.parse_args()

    if (options.betting_strategy == None) | (options.period == None):
        print(f'Usage: {parser.usage}')
        exit(1)

    return options
