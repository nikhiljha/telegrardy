#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Play the J! Archive as a Telegram Bot

Usage:
TBD
"""

import os
import logging
import random
import sqlite3
import re

from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, PicklePersistence
from telegram import ParseMode

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

logger = logging.getLogger(__name__)


def start(update, context):
    """Begin a round of the quiz."""
    if "current_question" not in context.chat_data:
        update.message.reply_text("Okay, starting a game!")
        context.chat_data["current_scores"] = {}
        context.chat_data["questions_completed"] = 0
        progress_game(update, context)
    else:
        update.message.reply_text("You're already in a round!")


def progress_game(update, context):
    if context.chat_data["questions_completed"] == 5:
        stop(update, context)
    else:
        # TODO: List the topic.
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
            # TODO: Get rid of "a" or "the" at the beginning.
            # TODO: Also remove periods.
            context.chat_data["current_answer"] = re.sub(
                r'\([^)]*\)', '', clue[2]).rstrip().lower()
            context.chat_data["current_hint"] = re.sub(
                r'\w', '-', context.chat_data["current_answer"])
            context.chat_data["hint_level"] = 0
        update.message.reply_text(
            context.chat_data["current_question"] + f"\n(Hint: {context.chat_data['current_hint']})", quote=False)
        # TODO: There has to be a better way to send context and update...
        context.job_queue.run_once(
            give_hint, 15, context=(context, update), name=update.message.chat_id)


def stop(update, context):
    """Begin a round of the quiz."""
    if "current_question" not in context.chat_data:
        update.message.reply_text("You're not in a round.")
    else:
        cancel_hints(update, context)
        del context.chat_data["current_question"]
        update.message.reply_text("Game over!", quote=False)
        print_score(update, context)


def calcpoints(hint_level):
    """Calculate how many points to give."""
    levels = {
        0: 5,
        1: 3,
        2: 1
    }
    return levels.get(hint_level, 0)


def give_hint(context):
    # TODO: Find a fast (non-loopy) way
    ans = context.job.context[0].chat_data["current_answer"]
    anslen = len(ans) // 4
    if anslen == 0:
        anslen = 1
    for x in range(anslen):
        letter = random.randrange(0, len(ans))
        context.job.context[0].chat_data["current_hint"] = context.job.context[0].chat_data["current_hint"][:letter] + \
            context.job.context[0].chat_data["current_answer"][letter] + \
            context.job.context[0].chat_data["current_hint"][letter + 1:]
    context.job.context[0].chat_data["hint_level"] += 1
    context.bot.send_message(
        chat_id=context.job.name, text="`" + context.job.context[0].chat_data["current_hint"] + "`", parse_mode=ParseMode.MARKDOWN)
    if context.job.context[0].chat_data["hint_level"] > 1:
        context.job_queue.run_once(
            timeout, 15, context=context.job.context, name=context.job.name)
    else:
        context.job_queue.run_once(
            give_hint, 15, context=context.job.context, name=context.job.name)


def cancel_hints(update, context):
    q = context.job_queue.get_jobs_by_name(update.message.chat_id)
    for x in q:
        x.schedule_removal()


def check(update, context):
    """Check if the message matched the answer."""
    if "current_question" in context.chat_data:
        # TODO: Sanity Check: Make sure current answer exists.
        # If not, reset state because things are BROKEN.
        if context.chat_data["current_answer"] in update.message.text.lower():
            cancel_hints(update, context)
            update.message.reply_text("Correct!")
            pts = calcpoints(context.chat_data["hint_level"])
            if update.effective_user.first_name in context.chat_data["current_scores"]:
                context.chat_data["current_scores"][update.effective_user.first_name] += pts
            else:
                context.chat_data["current_scores"][update.effective_user.first_name] = pts
            context.chat_data["questions_completed"] += 1
            print_score(update, context)
            progress_game(update, context)


def print_score(update, context):
    """Print the scores."""
    message = "Current scores..."
    for x in context.chat_data["current_scores"]:
        message += f"\n {x}: {context.chat_data['current_scores'][x]} points"
    update.message.reply_text(message, quote=False)


def timeout(context):
    """End the question if timeout is reached."""
    cancel_hints(context.job.context[1], context.job.context[0])
    context.job.context[1].message.reply_text(
        f"No one got it. The answer was {context.job.context[0].chat_data['current_answer']}.", quote=False)
    print_score(context.job.context[1], context.job.context[0])
    progress_game(context.job.context[1], context.job.context[0])


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
