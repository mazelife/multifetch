from bs4 import BeautifulSoup as Soup
import codecs
import os
import re
import sys
import time
import requests
import logging
import w3lib.url as urls
import urlparse
import multiprocessing as mproc

from downloader import Downloader
from reader import Reader


refresh = re.compile(r"^refresh$", re.I)
content = re.compile(r"^(\d+);\s*url=(.+)$", re.I)

class URLWorker(mproc.Process):

    def __init__(self, htdocs, tasks, results):
        self.htdocs = htdocs
        self.tasks = tasks
        self.results = results
        super(URLWorker, self).__init__()
        sys.stdout.write('I')
        self.downloader = Downloader()

    def run(self):
        while True:
            try:
                task = self.tasks.get()
                if not task:
                    # Poison pill means to exit!
                    sys.stdout.write('Q')
                    break
                status = self.fetch(task)
                if status == 200:
                    self.download()
                    sys.stdout.write('.')
                elif status >= 300 and status <= 399:
                    sys.stdout.write('R')
                elif status >= 400 and status <= 499:
                    sys.stdout.write('M')
                elif status >= 500 and status <= 599:
                    sys.stdout.write('X')
                else:
                    sys.stdout.write('?')

            except Exception as e:
                print e
                sys.stdout.write('E')
                continue

            sys.stdout.flush()

    def fetch(self, url):
        self.downloader.load(url)
        if not self.downloader.load_succeeded:
            return 0
        # It's necessary to do a second request to the URL to get a
        # real status code. The reason is that it is impossible to 
        # get a status code from selenium itself. This is a concious
        # decision on the part of the selenium devs. http://bit.ly/nlMvIM.
        # So, it's necessary to check the status of the last URL in the 
        # headless browser to make sure we are not saving a 3/4/500 page. 
        headers = {'User-Agent': (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/2"
            "9.0.1547.65 Safari/537.36"
        )}
        response = requests.head(self.downloader.url, headers=headers)
        # Per the HTTP spec, all webservers are required to support HEAD
        # however, some do not. A second GET request should be very rare.
        if response.status_code == 501:
            response = requests.get(self.downloader.url, headers=headers)
        return response.status_code

        

    def filededup(self, path, count=0):
        # This is the easy case- no duplication.
        if not os.path.exists(path):
            return path

        # Set up work variables
        count     += 1
        dirp, name = os.path.split(path)
        root, ext  = os.path.splitext(name)

        # Ensure a number hasn't already been added to the name
        if count > 1 and '-' in root and root[-1].isdigit():
            root = '-'.join(root.split('-')[:-1])

        name = "%s-%i%s" % (root, count, ext)

        return self.filededup(os.path.join(dirp, name), count)

    def download(self):
        safe_url = urls.safe_download_url(self.downloader.url)
        scheme, netloc, path, query, _ = urlparse.urlsplit(safe_url)
        path = os.path.join(self.htdocs, netloc, path[1:])

        if path.endswith('/'): path += "index.html"

        # Replace this with mimetypes
        if '.' not in os.path.basename(path):
            path = os.path.join(path, "index.html")

        pathdir = os.path.dirname(path)
        if not os.path.exists(pathdir):
            os.makedirs(pathdir)

        # Increment duplication
        path = self.filededup(path)

        with codecs.open(path, 'w', encoding="utf-8") as out:
            out.write(self.downloader.annotated_source)


class FetchJob(object):

    WORKER_CLASS       = URLWorker

    def __init__(self, whitelist, htdocs, **kwargs):
        self.htdocs    = htdocs
        self.whitelist = Reader(whitelist)
        self.tasks     = mproc.Queue()
        self.results   = mproc.Queue()
        self.numprocs  = kwargs.get('numprocs', mproc.cpu_count() * 2)
        self._workers  = []

    @property
    def workers(self):
        if not self._workers:
            kwargs = {
                'htdocs':  self.htdocs,
                'tasks':   self.tasks,
                'results': self.results,
            }
            self._workers = [self.WORKER_CLASS(**kwargs) for x in xrange(self.numprocs)]
        return self._workers

    def execute(self):
        # Start all the workers
        for worker in self.workers: worker.start()

        # Enqueue the jobs
        for name, url in self.whitelist:
            self.tasks.put(url)

        # Add a poison pill for each consumer
        for idx in xrange(self.numprocs): self.tasks.put(None)

        # Join on all the sails
        for worker in self.workers: worker.join()

        # Clear stdout
        sys.stdout.write('\n')
