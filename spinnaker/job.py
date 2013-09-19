import os
import re
import sys
import time
import requests
import logging
import w3lib.url as urls
import urlparse
import multiprocessing as mproc

from downloader import
from reader import Reader
from bs4 import BeautifulSoup as Soup

refresh = re.compile(r"^refresh$", re.I)
content = re.compile(r"^(\d+);\s*url=(.+)$", re.I)

class URLWorker(mproc.Process):

    def __init__(self, htdocs, tasks, results):
        self.htdocs = htdocs
        self.tasks = tasks
        self.results = results
        super(URLWorker, self).__init__()
        sys.stdout.write('I')

    def run(self):
        while True:
            try:
                task = self.tasks.get()
                if not task:
                    # Poison pill means to exit!
                    sys.stdout.write('Q')
                    break
                response = self.fetch(task)
                status   = response.status_code
                if status == 200:
                    self.download(response)
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
        headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/29.0.1547.65 Safari/537.36'}
        response = self.refresh(requests.get(url, headers=headers))
        import pdb; pdb.set_trace()
        return response

    def refresh(self, response):
        """
        Checks if there is a meta "refresh" tag in the 200 result.
        """
        html = Soup(response.text, "lxml")
        meta = html.find('meta', attrs={"http-equiv":refresh})

        if meta:
            attr = content.match(meta['content'])
            if attr:
                wait, url = attr.groups()
                time.sleep(int(wait))
                return self.fetch(url)
        return response

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

    def download(self, response):
        safe_url = urls.safe_download_url(response.url)
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

        with open(path, 'w') as out:
            out.write(response.text.encode(response.encoding))

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
