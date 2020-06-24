#!/usr/bin/python3

import argparse, os

from collections import defaultdict

from lib.data import *
from lib.exporters import *
from lib.filters import *
from lib.parsers import *

def parse_arguments():
    arg_parser = argparse.ArgumentParser(description='chokitto')
    arg_parser.add_argument('input', help='path to clippings file')
    arg_parser.add_argument('-o', '--output', help='path to output file (default: STDOUT)')
    arg_parser.add_argument('-p', '--parser', default='kindle', choices=list(PARSER_MAP.keys()), help='parser for clippings file (default: kindle)')
    arg_parser.add_argument('-e', '--exporter', default='markdown', help='clipping exporter (default: markdown)')
    arg_parser.add_argument('-m', '--merge', action='store_true', help='merge clippings of different types if they occur at the same location (default: False)')
    arg_parser.add_argument('-f', '--filters', nargs='*', help='list of filters to apply (default: None, format: "filter(\'arg\',\'arg\')")')
    arg_parser.add_argument('-ls', '--list', action='store_true', help='list titles of documents in clippings file and exit (default: False)')
    arg_parser.add_argument('-v', '--verbose', action='store_true', help='set verbosity (default: False)')
    return arg_parser.parse_args()

def get_user_input(prompt, options=['y', 'n']):
	ans = None
	while ans not in options:
		ans = input(f"{prompt} [{'/'.join(options)}] ")
	return ans

def main():
	args = parse_arguments()

	# parse clippings
	parser = PARSER_MAP[args.parser](verbose=args.verbose)
	documents = parser.parse(args.input)

	# merge and deduplicate clippings
	if args.merge:
		for title, author in documents:
			documents[(title, author)].merge_clippings()
			documents[(title, author)].deduplicate_clippings()

	# set up filters
	filters = parse_filters(args.filters) if args.filters else []
	if filters:
		# print filters
		if args.verbose:
			print("Filters (%d total):" % len(filters))
			for filt in filters:
				print("  %s" % filt)
		# apply filters
		documents = apply_filters(documents, filters)

	# list documents (and exit if list flag was used)
	if args.verbose or args.list:
		print("Documents (%d total):" % len(documents))
		for title, author in sorted(documents):
			print("  %s" % documents[(title, author)])
		if args.list: return

	# set up exporter
	exporter = parse_exporter(args.exporter)
	if args.output:
		# check if file already exists
		if os.path.exists(args.output):
			ans = get_user_input(f"File '{args.output}' already exists. Overwrite?")
			if ans == 'n':
				return
		exporter.write(documents, args.output)
		if args.verbose: print(f"Output:\n  Output was saved to '{args.output}' using {exporter}.")
	else:
		if args.verbose: print("Output:\n")
		print(exporter(documents))

if __name__ == '__main__':
	main()
