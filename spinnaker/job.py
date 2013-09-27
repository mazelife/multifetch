import sys
import time
import requests
from requests.exceptions import ConnectionError
import multiprocessing as mproc

from downloader import Downloader
from reader import Reader

class URLWorker(mproc.Process):

    def __init__(self, htdocs, tasks, results):
        self.tasks = tasks
        self.results = results
        super(URLWorker, self).__init__()
        sys.stdout.write('I')
        self.downloader = Downloader(htdocs)

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
                import traceback
                print traceback.format_exc()
                sys.stdout.write('E')
                break

            sys.stdout.flush()
            time.sleep(1)

    def fetch(self, url):
        self.downloader.load(url)
        if not self.downloader.load_succeeded:
            return 0
        else:
            self.downloader.write()
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
        try:
            response = requests.head(self.downloader.url, headers=headers)
        except ConnectionError:
            return 0
        # Per the HTTP spec, all webservers are required to support HEAD
        # however, some do not. A second GET request should be very rare.
        if response.status_code == 501:
            response = requests.get(self.downloader.url, headers=headers)
        return response.status_code


class FetchJob(object):

    WORKER_CLASS       = URLWorker

    def __init__(self, whitelist, htdocs, **kwargs):
        self.htdocs    = htdocs
        self.whitelist = Reader(whitelist)
        self.tasks     = mproc.Queue()
        self.results   = mproc.Queue()
        self.numprocs  = kwargs.get('numprocs', mproc.cpu_count())
        self.numprocs  = 4
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
