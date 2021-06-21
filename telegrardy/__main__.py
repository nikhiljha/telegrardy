#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import click
from loguru import logger
from telegrardy import bot
from telegrardy.jarchive import jarchive


@click.group()
@logger.catch
def main():
    pass


@click.command()
def run():
    """run the telegram bot"""
    if not os.path.isfile("clues.db"):
        logger.critical(
            "The database (clues.db) was not found in your current directory. Please generate it first."
        )
        exit(1)

    bot.poll()


if __name__ == "__main__":
    main.add_command(jarchive)
    main.add_command(run)
    main()
