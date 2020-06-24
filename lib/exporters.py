import datetime, re

from collections import OrderedDict

def parse_exporter(exporter_str):
	exporter = None
	exporter_match = re.match(r'^([a-zA-Z0-9_\-]+)(\((.*)\))?$', exporter_str)
	# check if exporter syntax is correct
	assert exporter_match is not None, f"Unknown exporter syntax '{exporter_str}'."
	# exporter name should always be present
	exporter_type = exporter_match[1]
	exporter_args = tuple()
	# parse arguments if any
	if exporter_match[3]:
		for exporter_arg_str in re.split(r",\s*(?=')", exporter_match[3]):
			exporter_args += (exporter_arg_str[1:-1], ) # remove surrounding quotes and add
	# check if exporter exists
	assert exporter_type in EXPORTER_MAP, f"Unknown exporter '{exporter_type}'."
	# construct exporter
	exporter = EXPORTER_MAP[exporter_type](*exporter_args)
	return exporter


class Exporter:
	def write(self, documents, path):
		# convert file and write to specified path
		with open(path, 'w', encoding='utf8') as file:
			file.write(self(documents))


class JsonExporter(Exporter):
	def __init__(self, date_format='%Y-%m-%d %H:%M:%S'):
		self.date_format = date_format

	def __call__(self, documents):
		import json

		res = []

		# iterate over documents
		for title, author in documents:
			res.append(self._document_to_json(documents[(title, author)]))

		# reduce to single object if results contain only one document
		res = res[0] if len(res) == 1 else res

		return json.dumps(res, indent=4)

	def __repr__(self):
		return '<JsonExporter: dateformat "%s">' % self.date_format

	def _document_to_json(self, document):
		res = OrderedDict()

		res['title'] = document.title
		res['author'] = document.author
		res['clippings'] = []

		# iterate over clippings
		for clipping in sorted(document.get_clippings()):
			res['clippings'].append(self._clipping_to_json(clipping))

		return res

	def _clipping_to_json(self, clipping):
		res = OrderedDict()

		res['type'] = clipping.clip_type
		res['page'] = None
		if clipping.page:
			res['page'] = clipping.page[0] if clipping.page[0] == clipping.page[1] else list(clipping.page)
		res['location'] = None
		if clipping.location:
			res['location'] = clipping.location[0] if clipping.location[0] == clipping.location[1] else list(clipping.location)
		res['datetime'] = clipping.datetime.strftime(self.date_format)

		# parse merged clipping
		if type(clipping.content) is list:
			res['content'] = [f'[{c.clip_type}] {c.content}' for c in sorted(clipping.content, key=lambda el: el.datetime)]
		else:
			res['content'] = clipping.content

		return res


class MarkdownExporter(Exporter):
	def __init__(self, date_format='%Y-%m-%d %H:%M:%S'):
		self.date_format = date_format

	def __call__(self, documents):
		res = ''
		# determine heading level
		heading_level = ''
		if len(documents) > 1:
			heading_level = '#'
			res = f'# Clippings for {len(documents)} Documents\n\n'

		# iterate over titles
		for title, author in sorted(documents):
			res += self._document_to_markdown(documents[(title, author)], heading_level)

		return res

	def __repr__(self):
		return '<MarkdownExporter: dateformat "%s">' % self.date_format

	def _document_to_markdown(self, document, heading_level=''):
		# create title '# TITLE'
		res = '%s# %s\n\n' % (heading_level, document.title)

		# add author if available
		res += '%s\n\n' % document.author if document.author else ''

		for clip_type in sorted(document.get_clipping_types(), ):
			# add type title
			res += '%s## %s\n\n' % (heading_level, ' + '.join([ct.title() + 's' for ct in clip_type.split('+')]))
			# iterate over clippings sorted by position
			for clipping in sorted(document.get_clippings(clip_type)):
				res += self._clipping_to_markdown(clipping, heading_level)
		return res

	def _clipping_to_markdown(self, clipping, heading_level=''):
		res = ''

		position = clipping.get_position()
		res += '%s### %s\n\n' % (heading_level, position)
		
		# add content
		if clipping.content:
			# process merged content
			if type(clipping.content) is list:
				# sort content by datetime
				for mi, mc in enumerate(sorted(clipping.content, key=lambda el: el.datetime)):
					# TODO merge identical or overlapping content
					# produce quote blocks for each content '> [TYPE] CONTENT'
					res += '>[%s] %s\n\n' % (mc.clip_type.title(), mc.content)
					# add datetime
					if len(self.date_format) > 0:
						# check if difference to next content is > 30 seconds
						if (mi == len(clipping.content) - 1) or ((clipping.content[mi+1].datetime - mc.datetime) > datetime.timedelta(seconds=30)):
							res += 'Added around %s.\n\n' % clipping.datetime.strftime(self.date_format)
			# standard procedure
			else:
				res += '> %s\n\n' % clipping.content
				# add datetime
				if len(self.date_format) > 0:
					res += 'Added on %s.\n\n' % clipping.datetime.strftime(self.date_format)
		return res


EXPORTER_MAP = {
	'json': JsonExporter,
	'markdown': MarkdownExporter
}