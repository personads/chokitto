import copy, datetime, re

from collections import defaultdict

from lib.data import *

def parse_filters(filter_strs):
	filters = []

	for filter_str in filter_strs:
		filter_match = re.match(r'^([a-zA-Z0-9_\-]+)(\((.*)\))?$', filter_str)
		# check if filter syntax is correct
		if filter_match is None:
			print(f"[Warning] Unknown filter syntax '{filter_str}'. Skipped.")
			continue
		# filter name should always be present
		filter_type = filter_match[1]
		filter_args = tuple()
		# parse arguments if any
		if filter_match[3]:
			for filter_arg_str in re.split(r",\s*(?=')", filter_match[3]):
				filter_args += (filter_arg_str[1:-1], ) # remove surrounding quotes and add
		# check if filter exists
		if filter_type not in FILTER_MAP:
			print(f"[Warning] Unknown filter '{filter_type}'. Skipped.")
			continue
		# try to construct filter
		try:
			filters.append(FILTER_MAP[filter_type](*filter_args))
		# catch error for missing arguments
		except TypeError as err:
			print(f"[Warning] Filter '{filter_type}' could not be constructed ({err}). Skipped.")
			continue

	return filters

def apply_filters(documents, filters):
	filtered_documents = {}
	# iterate over documents
	for title, author in documents:
		filtered_document = copy.deepcopy(documents[(title, author)])
		# filter on document level
		doc_filters = [doc_filt for doc_filt in filters if doc_filt.data_type == Document]
		if doc_filters and not all([doc_filt(filtered_document) for doc_filt in doc_filters]):
			continue
		# reset document clippings
		filtered_document.del_clippings()
		# iterate over clippings
		for clipping in documents[(title, author)].get_clippings():
			# filter on clipping level
			clip_filters = [clip_filt for clip_filt in filters if clip_filt.data_type == Clipping]
			if clip_filters and not all([clip_filt(clipping) for clip_filt in clip_filters]):
				continue
			filtered_document.add_clipping(clipping)
		# if document has clippings, add to results
		if len(filtered_document.clippings) > 0:
			filtered_documents[(title, author)] = filtered_document
	return filtered_documents

class Filter:
	def __init__(self, data_type=None):
		self.data_type = data_type

	def __call__(self, data):
		pass

#
# string filters
#

class StringFilter(Filter):
	def __init__(self, field, match, mode='exact', data_type=None):
		super(StringFilter, self).__init__(data_type=data_type)
		self.field = field
		self.match = match
		mode = mode.lower()
		assert mode in ['exact', 'regex'], f"Unsupported filter mode '{mode}'."
		self.mode = mode
		if self.mode == 'regex':
			pattern = re.compile(self.match)
			self.matcher = pattern.search
		else:
			self.matcher = lambda s: s == self.match

	def __call__(self, data):
		if self.data_type and not isinstance(data, self.data_type):
			return False
		return self.matcher(self.field(data))

	def __repr__(self):
		return '<%s: %s"%s", %s mode>' % (
			self.__class__.__name__,
			f'{self.data_type.__name__}, ' if self.data_type else '',
			self.match,
			self.mode
		)

class TitleFilter(StringFilter):
	def __init__(self, match, mode='exact'):
		super(TitleFilter, self).__init__(field=lambda d: d.title, match=match, mode=mode, data_type=Document)

class AuthorFilter(StringFilter):
	def __init__(self, match, mode='exact'):
		super(AuthorFilter, self).__init__(field=lambda d: d.author, match=match, mode=mode, data_type=Document)

class TypeFilter(StringFilter):
	def __init__(self, match, mode='exact'):
		super(TypeFilter, self).__init__(field=lambda c: c.clip_type, match='+'.join(sorted(match.lower().split('+'))), mode=mode, data_type=Clipping)

#
# comparison filters
#

class ComparisonFilter(Filter):
	def __init__(self, field, reference, mode, data_type=None):
		super(ComparisonFilter, self).__init__(data_type=data_type)
		self.field = field
		self.reference = reference
		assert mode in ['=', '<', '>'], f"Unsupported filter mode '{mode}'." 
		self.mode = mode

	def __call__(self, data):
		if self.data_type and not isinstance(data, self.data_type):
			return False
		if self.mode == '=':
			return self.field(data) == self.reference
		elif self.mode == '<':
			return self.field(data) < self.reference
		elif self.mode == '>':
			return self.field(data) > self.reference
		return False

	def __repr__(self):
		return '<%s: %s%s "%s">' % (
			self.__class__.__name__,
			f'{self.data_type.__name__}, ' if self.data_type else '',
			self.mode,
			self.reference
		)

class AfterFilter(ComparisonFilter):
	def __init__(self, ref_datetime):
		ref_datetime = datetime.datetime.strptime(ref_datetime, '%Y-%m-%d %H:%M:%S')
		super(AfterFilter, self).__init__(field=lambda c: c.datetime, reference=ref_datetime, mode='>', data_type=Clipping)

class BeforeFilter(ComparisonFilter):
	def __init__(self, ref_datetime):
		ref_datetime = datetime.datetime.strptime(ref_datetime, '%Y-%m-%d %H:%M:%S')
		super(BeforeFilter, self).__init__(field=lambda c: c.datetime, reference=ref_datetime, mode='<', data_type=Clipping)


FILTER_MAP = {
	# string filters
	'title': TitleFilter,
	'author': AuthorFilter,
	'type': TypeFilter,
	# time filters
	'after': AfterFilter,
	'before': BeforeFilter
}