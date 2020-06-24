import re

from lib.data import *

class KindleParser:
	def __init__(self, verbose=False):
		self.verbose = verbose

	def parse(self, path):
		'''Returns a dict of clippings sorted by title.

		Returns:
			dict: {('title', 'author'): Document, ...}
		'''
		# set up output datastructures
		documents = {}
		stats = defaultdict(int)

		with open(path, 'r', encoding='utf8') as cf:
			clip_line = 0
			for line in cf:
				line = line.replace('\ufeff', '').strip()
				# end of clipping
				if line == '==========':
					if clip_line > 0:
						# add document to output dictionary if new
						doc_key = (title, author)
						if doc_key not in documents:
							documents[doc_key] = Document(title, author)
						# add clipping to document
						documents[doc_key].add_clipping(
							Clipping(
								page=page,
								location=location,
								datetime=date_time,
								content=clip_content,
								clip_type=clip_type
							)
						)
						# add to stats
						stats[clip_type] += 1
					# reset clipping line counter
					clip_line = 0
					continue
				# skip if irrelevant
				if clip_line < 0:
					continue

				# parse title
				if clip_line == 0:
					title_author_match = re.match(r'(.+) \((.+, .+)\)', line)
					if title_author_match:
						title = title_author_match.group(1).strip()
						author = title_author_match.group(2)
					else:
						title = line.strip()
						author = None

				# parse type and position
				if clip_line == 1:
					# parse clipping type
					type_match = re.match(r'- Your (.+?) on', line)
					# skip if unknown
					if not type_match:
						clip_line = -1
						continue
					clip_type = type_match.group(1).lower()

					# parse position
					position_match = re.match(r'.+?(page ([\w\d\-]+) \| )?([Ll]ocation ([\d\-]+) \| )?(Added.+)', line)
					if position_match:
						# parse page to start and end integers
						page = None
						# if page string was found and it contains any digit (i.e. exclude 'page VI')
						if position_match.group(2) and any([c.isdigit() for c in position_match.group(2)]):
							page = position_match.group(2)
							# remove any strings besides '-'
							page = re.sub(r'[^\d\-]', '', page)
							if '-' in page:
								page_start = int(page.split('-')[0])
								page_end = int(page.split('-')[1])
							else:
								page_start, page_end = int(page), int(page)
							page = (page_start, page_end)
						# parse location to start and end integers
						location = position_match.group(4)
						if location:
							if '-' in location:
								location_start = int(location.split('-')[0])
								location_end = int(location.split('-')[1])
							else:
								location_start, location_end = int(location), int(location)
							location = (location_start, location_end)

						# parse datetime
						date_time = datetime.datetime.strptime(position_match.group(5), 'Added on %A, %B %d, %Y %I:%M:%S %p')

				# parse clipping content
				if clip_line == 3:
					clip_content = line

				# increment clipping internal counter
				clip_line += 1

		# print stats
		if self.verbose:
			print("Statistics ('%s'):" % path)
			stats['document'] = len(documents.keys())
			for stat in sorted(stats):
				print('  %d %s%s' % (stats[stat], stat.title(), '' if stats[stat] == 1 else 's'))

		return documents

# name to constructor map
PARSER_MAP = {
	'kindle': KindleParser
}
