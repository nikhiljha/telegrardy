# source: https://github.com/whymarrh/jeopardy-parser

import os
import urllib.request, urllib.error, urllib.parse
import time
import concurrent.futures as futures
from loguru import logger

current_working_directory = os.getcwd()
archive_folder = os.path.join(current_working_directory, "j-archive")
SECONDS_BETWEEN_REQUESTS = 2
ERROR_MSG = "ERROR: No game"
NUM_THREADS = 2  # Be conservative


def create_archive_dir():
    if not os.path.isdir(archive_folder):
        logger.info(f"creating {archive_folder} folder")
        os.mkdir(archive_folder)


def download_pages():
    page = 1
    with futures.ThreadPoolExecutor(max_workers=NUM_THREADS) as executor:
        # We submit NUM_THREADS tasks at a time since we don't know how many
        # pages we will need to download in advance
        while True:
            l = []
            for i in range(NUM_THREADS):
                f = executor.submit(download_and_save_page, page)
                l.append(f)
                page += 1
            # Block and stop if we're done downloading the page
            if not all(f.result() for f in l):
                break


def download_and_save_page(page):
    new_file_name = "%s.html" % page
    destination_file_path = os.path.join(archive_folder, new_file_name)
    if not os.path.exists(destination_file_path):
        html = download_page(page)
        if ERROR_MSG in html:
            # Now we stop
            logger.info("thread finished downloading! ready to parse.")
            return False
        elif html:
            save_file(html, destination_file_path)
            time.sleep(SECONDS_BETWEEN_REQUESTS)  # Remember to be kind to the server
    else:
        logger.warning(f"already downloaded {destination_file_path}, skipping")
    return True


def download_page(page):
    url = "http://j-archive.com/showgame.php?game_id=%s" % page
    html = None
    try:
        response = urllib.request.urlopen(url)
        if response.code == 200:
            logger.info(f"downloading {url}")
            html = response.read().decode('utf-8')
        else:
            logger.error(f"invalid URL: {url}")
    except urllib.error.HTTPError:
        logger.error(f"failed to open {url}")
    return html


def save_file(html, filename):
    try:
        with open(filename, "w") as f:
            f.write(html)
    except IOError:
        logger.critical(f"failed to write to file {filename}")
