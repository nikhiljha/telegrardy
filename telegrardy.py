#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Play the J! Archive as a Telegram Bot

Usage:
TBD
"""

import os
import logging
import sqlite3
import re

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, PicklePersistence

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update, context):
    """Begin a round of the quiz."""
    if "current_question" not in context.chat_data:
        update.message.reply_text("Okay, starting a game!")
        context.chat_data["questions_completed"] = 0
        progress_game(update, context)
    else:
        update.message.reply_text("You're already in a round!")


def progress_game(update, context):
    if context.chat_data["questions_completed"] == 5:
        stop(update, context)
    else:
        with sqlite3.connect("clues.db") as con:
            cur = con.cursor()
            cur.execute("""
                SELECT clues.id, clue, answer
                FROM clues
                JOIN documents ON clues.id = documents.id
                ORDER BY RANDOM()
                LIMIT 1
                """)
            clue = cur.fetchone()
            context.chat_data["current_question"] = clue[1]
            # Strips the alternate answers and whitespace.
            context.chat_data["current_answer"] = re.sub(
                r'\([^)]*\)', '', clue[2]).rstrip().lower()
            context.chat_data["hint_level"] = 0
        update.message.reply_text(context.chat_data["current_question"] + f" (Answer: {context.chat_data['current_answer']})")


def stop(update, context):
    """Begin a round of the quiz."""
    if "current_question" not in context.chat_data:
        update.message.reply_text("You're not in a round.")
    else:
        del context.chat_data["current_question"]
        update.message.reply_text("Game over!")
        # TODO: Print scores.


def check(update, context):
    """Check if the message matched the answer."""
    if "current_question" in context.chat_data:
        # TODO: Sanity Check: Make sure current answer exists.
        # If not, reset state because things are BROKEN.
        if context.chat_data["current_answer"] in update.message.text.lower():
            update.message.reply_text("Correct!")
            # TODO: Add points to person who got it right.
            context.chat_data["questions_completed"] += 1
            progress_game(update, context)


def timeout(update, context):
    """End the question if timeout is reached."""
    update.message.reply_text(f"No one got it. The answer was {context.chat_data['current_answer']}.")
    progress_game(update, context)


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Use Persistence
    persistence = PicklePersistence(filename='data.pkl')

    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(os.getenv('TELEGRAM_TOKEN'),
                      persistence=persistence, use_context=True)

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(CommandHandler("stop", stop))

    # on noncommand i.e message - check if it was correct
    dp.add_handler(MessageHandler(Filters.text, check))

    # log all errors
    dp.add_error_handler(error)

    # Start the Bot
    updater.start_polling()

    # Run the bot until you press Ctrl-C or the process receives SIGINT,
    # SIGTERM or SIGABRT. This should be used most of the time, since
    # start_polling() is non-blocking and will stop the bot gracefully.
    updater.idle()


if __name__ == '__main__':
    main()
