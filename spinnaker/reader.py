import unicodecsv as csv
import w3lib.url as urls

class Reader(object):

    def __init__(self, path, sep='\t'):
        self.path = path
        self.sep  = sep

    def rows(self):
        with open(self.path, 'r') as data:
            for row in csv.reader(data, delimiter=self.sep):
                yield row

    def errors(self):
        lineno = 0
        for row in self:
            lineno += 1
            if len(row) != 2:
                yield {'lineno': lineno, 'error': 'Row was not delimited correctly', 'row':row}
                continue

            if not urls.is_url(row[1]):
                yield {'lineno': lineno, 'error': 'Invalid URL', 'row': row}

    def seek(self, lineno=1):
        curline = 0
        for row in self:
            curline += 1
            if curline == lineno:
                return row
        return None

    def __iter__(self):
        return self.rows()
