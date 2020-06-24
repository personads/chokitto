# chokitto

Chokitto (チョキっと) is a minimal Python library for extracting highlights and annotations from your Kindle eReader.

* Create a neat overview of all your notes and highlights in [Markdown](#Markdown) or [JSON](#JSON)
* Export annotations from side-loaded documents and library books
* Use [filters](#Filters) to extract only the information you need (e.g. `title('Book No \d+', 'regex')`)
* Deduplicate entries and [merge](#Merge) matching highlights and notes

Store your annotations in a unified and cleaner way for future reference, book clubs and literature reviews. 📚

---

## Installation

Chokitto is written in Python3 (assumed to be the default interpreter for `python`) and only uses the standard library. Installation, merely involves cloning this repository:

```bash
git clone https://github.com/personads/chokitto
cd chokitto
```

## Usage

By default, chokitto requires the path to the clippings file (e.g. `/documents/My Clippings.txt` on Kindle). It is then [parsed](#Parsers), optionally [filtered](#Filters) and [exported](#Exporters) (default: Markdown) to standard output: 

```bash
python chokitto.py path/to/clippings
# for instance, a Kindle connected to a Mac
python chokitto.py "/Volumes/Kindle/documents/My Clippings.txt"
```
This will produce a Markdown document with all documents and their clippings sorted by type and location. The output can be written to a file by using a pipe or the `-o` / `--output` argument:

```bash
python chokitto.py path/to/clippings > path/to/output.md
python chokitto.py path/to/clippings -o path/to/output.md
```

The `-v` / `--verbose` option can be used to print additional parsing and filtering information. It is best used together with a pre-specified output file.

```bash
python chokitto.py path/to/clippings -o path/to/output.md -v
```
If you just want to take a quick look as to which documents the clipping file contains, use the `-ls` / `--list` option. 

```bash
python chokitto.py path/to/clippings -ls
```
Chokitto will then parse the data and output an alphabetically sorted list of documents before exiting.
```
Documents (42 total):
  <Document: "A Great Book" by "Lastname, Name", 6 clippings>
  <Document: "Another Great Book" by "Lastname, Name", 12 clippings>
  <Document: "Unauthored Document", 5 clippings>
  ...
```

For additional information regarding basic usage, please refer to the help text which can be accessed using the `-h` / `--help` flag.

```bash
python chokitto.py -h
```

### Parsers

Currently, only the `KindleParser` is available and enabled by default. It processes the `My Clippings.txt` file which contains the (slightly chaotic) highlights, annotations and bookmarks made in eBooks, PDFs and other documents on the eReader.

The parser can be explicitly specified by using the `-p` / `--parsers` argument:

```bash
python chokitto.py path/to/clippings -p "kindle" 
```

The library itself is written to accommodate any kind of parser which returns documents and clippings, so we hope to extend it in the future.

### Merging

Kindle's default behavior is to write every clipping action to the `My Clippings.txt` file. This means that changing the span of a highlight will be produce two entries in the file with different lengths. Furthermore, notes which are added to a highlighted section are stored as separate entries and can be difficult to match and find.

By using the `-m` / `--merge` option, chokitto can attempt to remove duplicate entries and reconnect separated highlights and notes:

```bash
python chokitto.py path/to/clippings -m
```

This will produce merged clippings such as `highlight+note` which appear in the output as follows:

```markdown
### Page 42, Location 4649-4650

>[Highlight] We are making a point here.

>[Note] They have a point.

Added around 2020-01-01 10:13:17.
```

### Filters

Filters can be used to specify which documents and clippings to include in the output. They are specified using the `filter('arg', 'arg')` syntax or simply as `filter` if there are no arguments or if they are left at their default values. Any number of them can be combined using the `-f` / `--filters` option:

```bash
python chokitto.py path/to/clippings -f \
"title('One Great Book')" \
"type('highlight')" \
"after('2020-01-01 00:00:00')"
```

This will produce output which only includes highlights from "One Great Book" which were made after the beginning of 2020.

#### Filter by String

String filters can be applied to document titles and authors as well as to clipping types. They follow the syntax `filter('Exact Match')` and can be used together with regular expressions such as `filter('One Great (Book|Document) \d+', 'regex')`.

**Filtering by Document Title** is done using `title('Title')`, e.g.:

```bash
python chokitto.py path/to/clippings -f "title('One Great Book')"
# filter for an entire series
python chokitto.py path/to/clippings -f "title('^Book No\. \d+', 'regex')"
```

**Filtering by Document Author** is done using `author('Author')`, e.g.:

```bash
python chokitto.py path/to/clippings -f "author('That Author')"
# filter for a family of authors
python chokitto.py path/to/clippings -f "author('Lastname, .+', 'regex')"
```

**Filtering by Clipping Type** is done using `type('type')`, e.g.:

```bash
python chokitto.py path/to/clippings -f "type('highlight')"
# use '+' to filter for merged types (remember to merge!)
python chokitto.py path/to/clippings -m -f "type('highlight+note')"
# use regular expressions to filter for multiple types
python chokitto.py path/to/clippings -f "type('(bookmark|note)', 'regex')"
```

#### Filter by Date and Time

Date filters can be useful for exporting more recent or older clippings depending on the time and date they were created. They follow the syntax `filter('yyy-mm-dd hh:mm:ss')`.

```bash
# only return clippings created after a certain date
python chokitto.py path/to/clippings -f "after('2020-01-01 00:00:00')"
# only return clippings created before a certain date
python chokitto.py path/to/clippings -f "before('2020-01-01 00:00:00')"
```

### Exporters

Exporters handle the formatting of the output. They are specified using the syntax `exporter` or `exporter('arg', 'arg')` if you want to change the default arguments. The default exporter is [Markdown](#Markdown) and it can be changed using the `-e` / `--exporter` option:

```bash
python chokitto.py path/to/clippings -e "markdown"
```

#### Markdown

The Markdown exporter will produce a document split into "# root → ## document → ### clipping type → #### clipping" sorted by location. If the output contains only a single document, the hierarchy shifts up one heading.

```markdown
# One Great Book

Lastname, Name

## Bookmarks

### Page 11, Location 48

## Highlights

### Page 25, Location 1602-1603

> This part was especially interesting.

Added on 2020-01-01 2020-01-01 9:41:53.

## Highlights + Notes

### Page 42, Location 4649-4650

>[Highlight] We are making a point here.

>[Note] They have a point.

Added around 2020-01-01 10:13:17.
```

If you would like to change the date formatting or omit it entirely, there's an argument for that:

```bash
python chokitto.py path/to/clippings -e "markdown('%m.%d at %H:%M')"
# omit the timestamp entirely
python chokitto.py path/to/clippings -e "markdown('')"
```

#### JSON

The JSON exporter will produce a list of document objects containing a list of clipping objects. If the output contains only a single document, the document object is returned directly.

```bash
python chokitto.py path/to/clippings -e "json"
```

This produces an output akin to:

```json
[
    {
        "title": "One Great Book",
        "author": "Lastname, Name",
        "clippings": [
            {
                "type": "bookmark",
                "page": 11,
                "location": 48,
                "datetime": "2020-01-01 8:20:12",
                "content": null,
            },
            {
                "type": "highlight",
                "page": 25,
                "location": [1602, 1603],
                "datetime": "2020-01-01 9:41:53",
                "content": "This part was especially interesting."
            }
        ]
    },
    {
        "title": "One More Great Book",
        "author": "Lastname, Name",
        "clippings": [
            {
                "type": "highlight+note",
                "page": 42,
                "location": [4649, 4650],
                "datetime": "2020-01-01 10:13:17",
                "content": [
                    "[highlight] We are making a point here.",
                    "[note] They have a point."
                ]
            }
        ]
    }
]
```

Similarly to the Markdown exporter, it is possible to change the date formatting or omit it entirely:

```bash
python chokitto.py path/to/clippings -e "json('%m.%d at %H:%M')"
# omit the timestamp entirely
python chokitto.py path/to/clippings -e "json('')"
```