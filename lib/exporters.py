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


class PdfMergeExporter(Exporter):
	def __init__(self, doc_path):
		# test whether mupdf is installed
		self.fitz = None
		try:
			import fitz
			self.fitz = fitz
		except ImportError as err:
			print("[Error] 'PyMuPDF' is required for the PdfMergeExporter.")
			raise err
		# parse document paths
		self.doc_path = doc_path

	def __call__(self, documents):
		assert len(documents) == 1, f"[Error] PdfMergeExporter can only process one document at a time (received {len(documents)})."

		pdf_bytes = self._merge_document(documents[list(documents.keys())[0]], self.doc_path)

		return pdf_bytes

	def __repr__(self):
		return f'<PdfMergeExporter:  "{self.doc_path}">'

	def _get_page_text(self, page):
		page_txt = ''
		page_txt_raw = page.getText()
		raw_idx_map = []

		cursor_idx = 0
		while cursor_idx < len(page_txt_raw):
			# retrieve current character
			cur_char = page_txt_raw[cursor_idx]
			# check for '-\n' sequence
			if cur_char == '-':
				if (cursor_idx + 1 < len(page_txt_raw)) and (page_txt_raw[cursor_idx + 1] == '\n'):
					# skip additional character
					cursor_idx += 1
			# check for '\n'
			elif cur_char == '\n':
				page_txt += ' '
				raw_idx_map.append(cursor_idx)
			# append all other characters as is
			else:
				page_txt += cur_char
				raw_idx_map.append(cursor_idx)

			cursor_idx += 1

		return page_txt, page_txt_raw, raw_idx_map

	def _search_page(self, page, clipping, min_query_len=0):
		results = []

		# first, find the longest textual equivalent from the raw PDF text
		# extract and clean text from pdf
		page_txt, page_txt_raw, raw_idx_map = self._get_page_text(page)
		# start with full clipping content as query and remove '-'
		clipping_txt = clipping.content.replace('-', '')
		page_query = clipping_txt

		query_len = len(clipping_txt)
		while query_len > min_query_len:
			ambiguous_match = False
			start_idx = 0
			while (start_idx + query_len) <= len(clipping_txt):
				cur_query = clipping_txt[start_idx:start_idx+query_len]
				pattern = re.compile(re.escape(cur_query))

				matches = [m for m in pattern.finditer(page_txt)]
				# if there is a single unambiguous match, use it
				if len(matches) == 1:
					# TODO improve capturing cleaner starts and ends of text spans when cleaned and raw text have different lengths
					txt_start_idx = matches[0].start() - start_idx
					txt_end_idx = txt_start_idx + len(clipping_txt)
					page_query = page_txt_raw[raw_idx_map[txt_start_idx]:raw_idx_map[txt_end_idx]]
					break
				# if there are multiple matches, print warning and exit
				elif len(matches) > 0:
					ambiguous_match = True
				start_idx += 1

			# if a single unambiguous match was found, use it
			if len(matches) == 1:
				break

			# if no unambiguous match was found with the current query_len, there's no point making it even less specific, so exit
			if ambiguous_match:
				return []

			query_len -= 1

		# if there are no matches, print warning and exit
		if len(matches) == 0:
			return []

		# next, search the actual PDF using the best textual match
		query_len = len(page_query)
		while query_len > min_query_len:
			start_idx = 0
			while (start_idx + query_len) <= len(page_query):
				cur_query = page_query[start_idx:start_idx+query_len]
				results = page.searchFor(cur_query)
				# expects resulting Rects to be of the single correct textual match
				if len(results) > 0:
					break
				start_idx += 1
			if len(results) > 0:
				break
			query_len -= 1

		return results

	def _merge_document(self, document, doc_path):
		pdf_doc = self.fitz.open(doc_path)

		for clipping in sorted(document.get_clippings()):
			if 'highlight' in clipping.clip_type.split('+'):
				contents = clipping.content if clipping.is_merged() else [clipping]
				# process highlights
				top_left = None
				for highlight in [c for c in contents if c.clip_type == 'highlight']:
					# retrieve rectangles from PDF to highlight
					page_idx = highlight.get_position(as_type=int)[0] - 1
					page = pdf_doc[page_idx]
					results = self._search_page(page, highlight)
					# skip clipping if it could not matched to the PDF
					if len(results) < 1:
						continue
					# add highlight annotation using the resulting rectangles
					page.addHighlightAnnot(results)
					# get top right point of highlight annotation
					for rect in results:
						if (top_left is None) or ((rect.top_left.x < top_left.x) and (rect.top_left.y < top_left.y)):
							top_left = rect.top_left
				# if no highlight was matched, fall back to (0,0) origin
				if top_left is None:
					top_left = self.fitz.Point()

				# process notes, if there are any
				for note in [c for c in contents if c.clip_type == 'note']:
					# shift top left by the size of the note icon
					top_left.x = max(0, top_left.x - 20)
					top_left.y = max(0, top_left.y - 20)
					# add textual annotation at top right point of the highlight
					page.addTextAnnot(top_left, note.content)

		return pdf_doc.write(clean=True, deflate=True)

	def write(self, documents, path):
		# convert file and write to specified path
		with open(path, 'wb') as file:
			file.write(self(documents))


EXPORTER_MAP = {
	'json': JsonExporter,
	'markdown': MarkdownExporter,
	'pdfmerge': PdfMergeExporter
}