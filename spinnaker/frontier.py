import csv
from datetime import datetime
import os
from StringIO import StringIO


"""
A module for handling the frontier file. This is a file to which URL visits
are logged during the crawl. It is also read into spinnaker at the start of
a session and used to filter out URLs that have already been crawled.
"""


FIELDNAMES = ("date", "networkURL", "merchantURL", "status", "path")
LOGGER_SENTINEL = "Q"


class FrontierFileReader(csv.DictReader):

    def __init__(self, *args, **kwargs):
        kwargs["fieldnames"] = FIELDNAMES
        # Old-style class, so no ``super`` allowed.
        csv.DictReader.__init__(self, *args, **kwargs)


class FrontierFileWriter(csv.DictWriter):

    def __init__(self, *args, **kwargs):
        kwargs["fieldnames"] = FIELDNAMES
        # Old-style class, so no ``super`` allowed.
        csv.DictWriter.__init__(self, *args, **kwargs)


class FrontierFileHandler(object):

    visited_network_urls = set([])

    def __init__(self, path):
        # Read records if there is a pre-existing frontier file.
        self.mode = "a" if os.path.isfile(path) else "w"
        if self.mode == "a":
            with open(path, "r") as existing_file:
                reader = FrontierFileReader(existing_file)
                for row in reader:
                    if row["status"] == "200":
                        self.visited_network_urls.add(row["networkURL"])
        self.path = path

    def __contains__(self, value):
        """
        Was a visit to this URL already logged?

        >>> ffh = FrontierFileHandler("/path/to/file")
        >>> "http://www.google.com" in ffh
        True
        """
        return value in self.visited_network_urls


def log_listener(queue, frontier_pth):
    """
    The listener process target function. When visits are put
    into the queue by workers, this writes them out to the CSV.
    """
    # Uze a zero-width buffer, we want data immediately written
    # to file.
    with open(frontier_pth, "a", 0) as fh:
        writer = FrontierFileWriter(fh)
        while True:
            try:
                record = queue.get()
                if record == LOGGER_SENTINEL:
                    break
                writer.writerow(record)
            except (KeyboardInterrupt, SystemExit):
                raise
            except:
                import sys, traceback
                print >> sys.stderr, 'Logging error: '
                traceback.print_exc(file=sys.stderr)


def log_visit(queue, *args):
    """
    Create a dictionary suitable for a CSV Writer to consume and put
    it into the logging queue.
    """
    args = (datetime.now().strftime("%d/%b/%Y:%H:%M:%S"),) + args
    visit = dict(zip(FIELDNAMES, args))
    queue.put_nowait(visit)
