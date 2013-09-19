#!/usr/bin/env python

import os
import baker

from job import FetchJob
from reader import Reader

@baker.command
def fetch(whitelist, htdocs=None, verbose=True):
    """
    Goes through a whitelist file and fetches them to disk.

    If you don't specify an HTDOCs path, the script will fetch the urls
    to the current working directory, in a folder called htdocs.

    :param whitelist: The path to a TSV whitelist on disk.
    :param htdocs: The path to store the downloads
    :param verbose: Print verbosity to disk!
    """

    # Deal with the HTDOCs directory
    htdocs = htdocs or os.path.join(os.getcwd(), 'htdocs')
    if os.path.exists(htdocs) and not os.path.isdir(htdocs):
        if verbose:
            print "Invalid path to an htdocs directory"
        return
    elif not os.path.exists(htdocs):
        if verbose:
            print "Making directory '%s'" % htdocs
        os.makedirs(htdocs)

    # Validate the Whitelist
    if validate(whitelist):
        if verbose:
            print "Whitelist is valid! Beginning fetch..."
    else:
        return

    # Execute the fetcher
    job = FetchJob(whitelist, htdocs)
    job.execute()

@baker.command
def validate(whitelist, verbose=True):
    """
    Ensures that a whitelist is a valid tsv.

    :param whitelist: The path to a TSV whitelist on disk.
    :param verbose: Print verbosity to disk!
    """
    if not os.path.exists(whitelist) or not os.path.isfile(whitelist):
        if verbose:
            print "Invalid path to whitelist"
        return False

    reader = Reader(whitelist)
    errors = list(reader.errors())

    if errors:
        if verbose:
            print "There were %i errors in the whitelist:" % len(errors)
            for error in errors:
                print "    Line %(lineno)i: %(error)s" % error
        return False

    if verbose:
        print "There were no errors found in whitelist!"
    return True

if __name__ == "__main__":
    baker.run()
