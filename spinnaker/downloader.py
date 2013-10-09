import base64
import codecs
import os
import re
import string
from urllib2 import URLError
import urlparse

import pyhash
from selenium import webdriver
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.desired_capabilities import DesiredCapabilities
import w3lib.url as urls


class Downloader(object):

    def __init__(self, htdocs, driver="Chrome", timeout=30):

        self.htdocs = htdocs
        self._driver  = driver
        self._browser = self._create_browser(driver)
        self._browser.set_page_load_timeout(timeout)
        self._current_url = ""
        self._hasher = pyhash.murmur2_x64_64a()
        self._filename_translation = string.maketrans("/=", "_-")
        self._trailing_dash = re.compile("[-]+$")


    def __del__(self):
        self._destroy_browser()

    def _create_browser(self, driver_name=None):
        """
        Return a new browser object using the specified driver.
        """

        driver_name = driver_name or self._driver
        driver = getattr(webdriver, driver_name, None)
        if not driver:
            raise ImportError("Could not import selenium.webdriver.{0}.".format(driver_name))
        desired_capabilities = dict(getattr(DesiredCapabilities, driver_name.upper()))
        usr_agent = "{0}.page.settings.userAgent".format(driver_name.lower())
        desired_capabilities[usr_agent] = (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_8_5) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/30.0.1599.66 Safari/537.36"
        )
        return driver(desired_capabilities=desired_capabilities)

    def _destroy_browser(self):
        """
        Quit the current browser and allow the object to be gc'd.
        """
        if self._browser:
            self._browser.quit()
            self._browser = None

    def load(self, url):
        """
        Load the given url into the selenium browser.
        """
        if not self._browser:
            self._browser = self._create_browser(self._driver)
        self._current_url = url
        try:
            self._browser.get(url)
        except TimeoutException:
            self._current_url = None
        except URLError:  # Selenium has lost contact with the web browser.
            print "Browser crapped out..."
            self._destroy_browser()
            self.load(url)
            return
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

    def get_file_name(self, path):
        # This is the easy case- no duplication, file name can stay as-is.
        if not os.path.exists(path):
            return path
        # Use the murmur hash algorithm to get a 64-bit hash of the page's 
        # contents. Base 64 encode this and translate filename-unsafe chars.
        dirp, name = os.path.split(path)
        _, ext  = os.path.splitext(name)
        page_hash  = self._hasher(self.source)
        root = base64.b64encode(str(page_hash))
        root = root.translate(self._filename_translation)
        root = self._trailing_dash.sub("", root)
        filename = "".join([root, ext])
        return os.path.join(dirp, filename)

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

        # Handle file naming.
        path = self.get_file_name(path) 

        with codecs.open(path, 'w', encoding="utf-8") as out:
            out.write(self.source)
        return path


if __name__ == "__main__":
    url = (
        "http://click.linksynergy.com/link?id=J7fouUe6AiE&"
        "offerid=256004.2419&type=15&murl=http%3A%2F%2Fwww."
        "7forallmankind.com%2Fpd%2Fp%2F2419.html"
    )
    d = Downloader("../htdocs")
    d._browser.get('http://httpbin.org/headers')
    print(d._browser.page_source)
