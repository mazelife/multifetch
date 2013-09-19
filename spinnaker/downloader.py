import os
import codecs
import urlparse

import w3lib.url as urls
from selenium import webdriver
from selenium.common.exceptions import TimeoutException

class Downloader(object):

    def __init__(self, htdocs, driver="PhantomJS", timeout=30):
        self.htdocs = htdocs

        self._driver  = driver
        self._browser = self._create_browser(driver)
        self._browser.set_page_load_timeout(timeout)
        self._current_url = ""

    def __del__(self):
        self._browser.quit()

    def _create_browser(self, driver=None):
        driver = driver or self._driver
        driver = getattr(webdriver, driver, None)
        if not driver:
            raise ImportError("Could not import selenium.webdriver.{0}.".format(driver))
        return driver()

    @property
    def annotated_source(self):
        """
        The HTML source with an added comment preceeding
        everything containing the URL of the page.
        """
        return "".join(("<!-- ", self._current_url, " -->", self.source))

    def load(self, url):
        """
        Load the given url into the selenium browser.
        """
        self._current_url = url
        try:
            self._browser.get(url)
        except TimeoutException:
            self._browser.quit()
            self._current_url = None
        self._current_url = self._browser.current_url

    @property
    def source(self):
        """
        The HTML source of the page.
        """
        return self._browser.page_source

    @property
    def load_succeeded(self):
        if not self.url or self.url.startswith(u"data:text/html"):
            return False
        return True

    @property
    def url(self):
        return self._current_url

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

    def write(self):
        safe_url = urls.safe_download_url(self.url)
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
            out.write(self.annotated_source)


if __name__ == "__main__":
    url = (
        "http://click.linksynergy.com/link?id=J7fouUe6AiE&"
        "offerid=256004.2419&type=15&murl=http%3A%2F%2Fwww."
        "7forallmankind.com%2Fpd%2Fp%2F2419.html"
    )
    d = Downloader('../htdocs/')
    d.load(url)
    d.write()
    d.source()
