import click
from telegrardy.clues import downloader, parser


@click.group()
def clues(**kwargs):
    """tools related to downloading from the jeopardy archive"""
    pass


@clues.command()
def download(**kwargs):
    """download webpages from the J! archive"""
    downloader.create_archive_dir()
    downloader.download_pages()


@clues.command()
def parse(**kwargs):
    """parse webpages from the J! archive into clues.db"""
    parser.parse()
