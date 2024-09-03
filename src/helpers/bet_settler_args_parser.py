#!/usr/bin/python3

from optparse import OptionParser

def args_parser():
    parser = OptionParser('bet_bot_main -B <betting_strategy>')
    parser.add_option("-B", dest="betting_strategy", type='string', help="specify betting strategy")

    (options, args) = parser.parse_args()

    if (options.betting_strategy == None):
        print(f'Usage: {parser.usage}')
        exit(1)

    return options
