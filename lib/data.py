import copy, datetime

from collections import defaultdict

class Document:
	def __init__(self, title, author=None):
		self.title = title
		self.author = author
		self.clippings = []
		# internal housekeeping
		self._type_idx_map = defaultdict(list)

	def __repr__(self):
		return '<Document: "%s"%s, %d clippings>' % (
				self.title,
				' by "%s"' % self.author if self.author else '',
				len(self.clippings)
			)

	def add_clipping(self, clipping):
		# store clipping and get index
		self.clippings.append(clipping)
		clip_idx = len(self.clippings) - 1
		# store index in type map
		self._type_idx_map[clipping.clip_type].append(clip_idx)

	def get_clippings(self, clip_type=None):
		# return all indices is no type is specified
		if clip_type is None:
			clip_idcs = list(range(len(self.clippings)))
		# if type is specified, return only the relevant indices
		else:
			clip_idcs = self._type_idx_map[clip_type]
		# yield clipping at index in each iteration
		for clip_idx in clip_idcs:
			yield self.clippings[clip_idx]

	def del_clippings(self):
		self.clippings = []
		self._type_idx_map = defaultdict(list)

	def get_clipping_types(self):
		return list(self._type_idx_map.keys())

	def merge_clippings(self):
		clippings = sorted(self.get_clippings())
		del_idcs = set()
		# iterate over all clippings and find overlapping entries
		for clip_idx, clipping in enumerate(clippings):
			# skip clip if it was previously merged
			if clip_idx in del_idcs:
				continue
			clip_start, clip_end = clipping.get_position(prefer_location=True, as_type=int)
			# initialize merged clipping as current one
			merged_clipping = copy.deepcopy(clipping)
			# perform lookahead
			for next_idx in range(clip_idx + 1, len(clippings)):
				next_clipping = clippings[next_idx]
				next_start, next_end = next_clipping.get_position(prefer_location=True, as_type=int)
				# check if lookahead exceeds clipping range
				if next_start > clip_end:
					break
				# if clipping subsumes its successor or vice versa, merge
				if merged_clipping.subsumes(next_clipping) or next_clipping.subsumes(merged_clipping):
					# add lookahead clipping to new, merged clipping
					merged_clipping = merged_clipping.merge(next_clipping)
					# update clipping range to reflect potentially larger or smaller span
					clip_start, clip_end = merged_clipping.get_position(prefer_location=True, as_type=int)
					# add current and merged indices to deletion queue
					del_idcs.add(clip_idx)
					del_idcs.add(next_idx)
			# add merged clipping to document
			if clip_idx in del_idcs:
				self.add_clipping(merged_clipping)
		
		# rebuild clippings list and remove merged entries
		new_clippings = []
		new_type_idx_map = defaultdict(list)
		new_clip_idx = 0
		for clip_idx, clipping in enumerate(self.clippings):
			# skip old clippings which were merged
			if clip_idx in del_idcs:
				continue
			new_clippings.append(clipping)
			new_type_idx_map[clipping.clip_type].append(new_clip_idx)
			new_clip_idx += 1
		self.clippings = new_clippings
		self._type_idx_map = new_type_idx_map

	def deduplicate_clippings(self):
		for clipping in self.get_clippings():
			if not clipping.is_merged():
				continue
			clipping.deduplicate()

	def to_markdown(self, heading_level='', exclude_datetime=False):
		# create title '# TITLE'
		res = '%s# %s\n\n' % (heading_level, self.title)

		# add author if available
		res += '%s\n\n' % self.author if self.author else ''

		for clip_type in sorted(self.get_clipping_types(), ):
			# add type title
			res += '%s## %s\n\n' % (heading_level, ' + '.join([ct.title() + 's' for ct in clip_type.split('+')]))
			# iterate over clippings sorted by position
			for clipping in sorted(self.get_clippings(clip_type)):
				res += clipping.to_markdown(heading_level, exclude_datetime)
		return res


class Clipping:
	def __init__(self, page, location, datetime, content, clip_type):
		self.clip_type = clip_type # 'TYPE' or 'TYPE+TYPE'
		self.page = page # (START, END) or None
		self.location = location # (START, END) or None
		self.datetime = datetime # datetime object
		self.content = content # 'CONTENT' or [Clipping, Clipping, ...]

	def __repr__(self):
		return f"<Clipping: {self.clip_type}, {self.get_position()}, {'content length %d' % len(self.content)}{' (merged)' if self.is_merged() else ''}>"

	def __lt__(self, other):
		assert isinstance(other, Clipping), "Cannot compare %s and %s." % (self, other)
		# compare normalized starting positions
		return self.get_position(prefer_location=True, as_type=int)[0] < other.get_position(prefer_location=True, as_type=int)[0]

	def subsumes(self, other):
		assert isinstance(other, Clipping), "%s cannot subsume and %s." % (self, other)
		position = self.get_position(prefer_location=True, as_type=int)
		other_position = other.get_position(prefer_location=True, as_type=int)
		return (position[0] <= other_position[0]) and (position[1] >= other_position[1])

	def merge(self, other):
		assert isinstance(other, Clipping), "Cannot merge %s and %s." % (self, other)
		merged = copy.deepcopy(self)

		# merge clip types
		merged.clip_type = '+'.join(sorted(set(self.clip_type.split('+') + other.clip_type.split('+'))))

		# merge pages
		if self.page and other.page:
			merged.page = (min(self.page[0], other.page[0]), max(self.page[1], other.page[1]))
		elif (self.page is None) and other.page:
			merged.page = other.page

		# merge location
		if self.location and other.location:
			merged.location = (min(self.location[0], other.location[0]), max(self.location[1], other.location[1]))
		elif (self.location is None) and other.location:
			merged.location = other.location

		# merge datetime
		if self.datetime and other.datetime:
			merged.datetime = max(self.datetime, other.datetime)
		elif (self.datetime is None) and other.datetime:
			merged.datetime = other.datetime

		# merge content into list
		merged.content = []
		merged.content += self.content if type(self.content) is list else [self]
		merged.content += other.content if type(other.content) is list else [other]

		return merged

	def deduplicate(self):
		if not self.is_merged(): return
		# gather newest clipping of each type
		new_content = {}
		for clipping in self.content:
			if clipping.clip_type in new_content:
				new_content[clipping.clip_type] = max(new_content[clipping.clip_type], clipping, key=lambda c: c.datetime if c.datetime else 0)
			else:
				new_content[clipping.clip_type] = clipping
		# update content and location
		self.content = list(new_content.values())
		if self.page:
			self.page = (min([c.page[0] for c in self.content]), max([c.page[0] for c in self.content]))
		if self.location:
			self.location = (min([c.location[0] for c in self.content]), max([c.location[0] for c in self.content]))
		# reduce list to single item if only one entry is left
		self.content = self.content[0] if len(self.content) == 1 else self.content

	def is_merged(self):
		return type(self.content) is list

	def get_position(self, prefer_location=False, as_type=str):
		position = None
		# construct position string
		if as_type is str:
			position_strs = []
			if self.page:
				# if single page
				if self.page[0] == self.page[1]:
					position_strs.append('Page %d' % self.page[0])
				# if page range
				else:
					print(self.page)
					position_strs.append('Pages %d-%d' % self.page)
			if self.location:
				# reset position string if location is preferred
				if prefer_location:
					position_strs = []
				# if single location
				if self.location[0] == self.location[1]:
					position_strs.append('Location %d' % self.location[0])
				# if location range
				else:
					position_strs.append('Location %d-%d' % self.location)
			position = ', '.join(position_strs)
		# construct position integer tuple
		elif as_type is int:
			position = tuple()
			if self.page:
				position += tuple(self.page)
			if self.location:
				if prefer_location:
					position = tuple(self.location)
				else:
					position += tuple(self.location)
		return position

	def to_markdown(self, heading_level='', exclude_datetime=False):
		res = ''

		position = self.get_position()
		res += '%s### %s\n\n' % (heading_level, position)
		
		# add content
		if self.content:
			# process merged content
			if type(self.content) is list:
				# sort content by datetime
				for mi, mc in enumerate(sorted(self.content, key=lambda el: el.datetime)):
					# TODO merge identical or overlapping content
					# produce quote blocks for each content '> [TYPE] CONTENT'
					res += '>[%s] %s\n\n' % (mc.clip_type.title(), mc.content)
					# add datetime
					if not exclude_datetime:
						# check if difference to next content is > 30 seconds
						if (mi == len(self.content) - 1) or ((self.content[mi+1].datetime - mc.datetime) > datetime.timedelta(seconds=30)):
							res += 'Added around %s.\n\n' % self.datetime
			# standard procedure
			else:
				res += '> %s\n\n' % self.content
				# add datetime
				if not exclude_datetime:
					res += 'Added on %s.\n\n' % self.datetime
		return res

