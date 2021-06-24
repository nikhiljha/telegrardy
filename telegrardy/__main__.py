#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import click
from loguru import logger
from telegrardy import bot as botmodule
from telegrardy.clues import clues


@click.group()
@logger.catch
def main():
    pass


@click.command()
def bot():
    """run the telegram bot"""
    if not os.path.isfile("clues.db"):
        logger.critical(
            "The database (clues.db) was not found in your current directory. Please generate it first."
        )
        exit(1)

    botmodule.poll()


if __name__ == "__main__":
    main.add_command(bot)
    main.add_command(clues)
    main()
