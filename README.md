Multifetch
===========

Fetch pages with a headless browser.


The recommended browser is PhantomJS, a fast webkit-based headless browser.
It's easy to install with Homebrew::

    ?> brew install phantomjs

Then install the requirements::

    ?> pip install -r requirements.txt

Then run the fetch command in the ``bin`` directory::

    ?> ./spin fetch /path/to/product_detail.tsv --htdocs=/path/to/htdocs

