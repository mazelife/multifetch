from selenium import webdriver
from selenium.common.exceptions import TimeoutException


class Downloader(object):

    def __init__(self, driver="PhantomJS", timeout=30):
        driver = getattr(webdriver, driver, None)
        if not driver:
            raise ImportError("Could not import selenium.webdriver.{0}.".format(driver))
        self._browser = driver()
        self._browser.set_page_load_timeout(timeout)
        self._current_url = ""

    def __del__(self):
        self._browser.close()

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


if __name__ == "__main__":
    url = (
        "http://click.linksynergy.com/link?id=J7fouUe6AiE&"
        "offerid=256004.2419&type=15&murl=http%3A%2F%2Fwww."
        "7forallmankind.com%2Fpd%2Fp%2F2419.html"
    )
    d = Downloader()
    #d.load(url)