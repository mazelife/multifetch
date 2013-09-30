import sys
import time
import requests
from requests.exceptions import ConnectionError
import multiprocessing as mproc

from downloader import Downloader
import frontier
from reader import Reader


class URLWorker(mproc.Process):

    def __init__(self, htdocs, tasks, results, logs):
        self.logs = logs
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
            except (KeyboardInterrupt, SystemExit):
                break
            except Exception as e:
                sys.stdout.write('E')
                _, _, tb = sys.exc_info()
                import traceback
                traceback.print_tb(tb)
                break

            sys.stdout.flush()
            time.sleep(1)

    def fetch(self, url):
        self.downloader.load(url)
        if not self.downloader.load_succeeded:
            return 0
        else:
            dowloaded_file_path = self.downloader.write()
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
        frontier.log_visit(
            self.logs,
            url,
            self.downloader.url,
            response.status_code,
            dowloaded_file_path
        )
        return response.status_code


class FetchJob(object):

    WORKER_CLASS       = URLWorker

    def __init__(self, whitelist, htdocs, frontier_pth, **kwargs):
        self.htdocs    = htdocs
        self.whitelist = []
        self.tasks     = mproc.Queue()
        self.results   = mproc.Queue()
        self.logs      = mproc.Queue()
        self.numprocs  = kwargs.get('numprocs', mproc.cpu_count())
        self.numprocs  = 4
        self._workers  = []       
        frontier_file = frontier.FrontierFileHandler(frontier_pth)
        
        for name, url in Reader(whitelist):
            if url not in frontier_file:
                self.whitelist.append((name, url))
        if not self.whitelist:
            print >> sys.stderr, "No new URLs to crawl."
            sys.exit(0)
        print >> sys.stderr, "Preparing to crawl {0} URLs...".format(len(self.whitelist))
        # Spawn logging process.
        self.logger_listener = mproc.Process(
            args=(self.logs, frontier_pth),
            name="spinnaker_logger",
            target=frontier.log_listener,
        )

    @property
    def workers(self):
        if not self._workers:
            kwargs = {
                'htdocs':  self.htdocs,
                'tasks':   self.tasks,
                'results': self.results,
                'logs': self.logs,
            }
            self._workers = [self.WORKER_CLASS(**kwargs) for x in xrange(self.numprocs)]
        return self._workers

    def execute(self):
        # Start the log listener
        self.logger_listener.start()

        # Start all the workers
        for worker in self.workers:
            worker.start()
        # Enqueue the jobs
        for name, url in self.whitelist:
            self.tasks.put(url)
        # Add a poison pill for each consumer
        for idx in xrange(self.numprocs):
            self.tasks.put(None)
        # Join on all the sails
        for worker in self.workers:
            worker.join()
        # End the logger process when fetching is complete.
        self.logs.put(frontier.LOGGER_SENTINEL)
        self.logger_listener.join()       
        # Clear stdout
        sys.stdout.write('\n')
