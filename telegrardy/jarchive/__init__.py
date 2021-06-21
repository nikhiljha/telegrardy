import click
from telegrardy.jarchive import downloader, parser


@click.group()
def jarchive(**kwargs):
    """tools related to downloading from the jeopardy archive"""
    pass


@jarchive.command()
def download(**kwargs):
    """download webpages from the J! archive"""
    downloader.create_archive_dir()
    downloader.download_pages()


@jarchive.command()
def parse(**kwargs):
    """parse webpages from the J! archive into clues.db"""
    parser.parse()
