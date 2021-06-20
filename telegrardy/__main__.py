#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Play the J! Archive as a Telegram Bot

Usage:
See README
"""

import os
import logging
import random
import sqlite3
import re

from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    PicklePersistence,
)
from telegram.ext.filters import MergedFilter
from telegram import ParseMode

# Configurables
HINT_TIME = 20  # Time between each hint. 1/3 of round length.


# Enable logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

logger = logging.getLogger(__name__)


# Stickers
STICKER_CORRECT = [
    "CAACAgIAAxkBAAJSeF5Sx9p2bi5G_3cyKJSUcYLCW-FeAAL1AAPtuN8KXRvw26jzLsIYBA",
    "CAACAgIAAxkBAAJShF5SyFpQ6tVhvqiWQeuRnGSTWB5SAAKDOgAC4KOCB1SRzGnF4yiuGAQ",
    "CAACAgIAAxkBAAJSh15SyHNdnpHdEflJLb3EFPYBg1zrAAJ0OgAC4KOCB47dXJW0xkd_GAQ",
    "CAACAgIAAxkBAAJSil5SyIVm5CCNVHR0iMmfkx3-C2SVAAL-SgAC4KOCB6EttTVVFWl1GAQ",
    "CAACAgIAAxkBAAJSjV5SyJKUvkTBZTBBWpGeyhUzLFi4AAIYAQAC7bjfCm0ZdOkaW95CGAQ",
]
STICKER_INCORRECT = [
    "CAACAgIAAxkBAAJSe15Sx-6uV_6MmbOBGbG9iU5AiB35AAL2AAPtuN8KIM8EQoBuMkQYBA",
    "CAACAgIAAxkBAAJSkF5SyJ6ixnOAlo5zPx1OcJRJvdUXAAIKAQAC7bjfCpSVxdA3xIbNGAQ",
    "CAACAgIAAxkBAAJSk15SyLvjlnu6mCxRaLBAmez_v_wfAAL-AAPtuN8Kbz6GfiLA87cYBA",
    "CAACAgIAAxkBAAJSll5SyNFbDJx1fiR8uasjLpPQyoldAAJtOgAC4KOCB4S4QaXnOEWHGAQ",
]
STICKER_ERROR = (
    "CAACAgIAAxkBAAJSfl5SyAbGce8ZVwiHHAABZD-9RU98dAACFwEAAu243wpXxgT5_08N5xgE"
)
STICKER_QUESTION = [
    "CAACAgIAAxkBAAJSgV5SyEmOE5Iwyeuti6t8wohqmd1yAAJuOgAC4KOCB77pR2Nyg3apGAQ",
    "CAACAgIAAxkBAAJSmV5Syt_34HKUVWm05vAC__OODIDvAAL4AAPtuN8KBIJRy2NIxsAYBA",
]


def start(update, context):
    """Begin a round of the quiz."""
    # TODO: Make the round length configurable, with a maximum.
    if "current_question" not in context.chat_data:
        update.message.reply_text("Okay, starting a game!")
        context.chat_data["current_scores"] = {}
        context.chat_data["questions_completed"] = 0
        progress_game(update, context)
    else:
        update.message.reply_text("You're already in a round!")


def progress_game(update, context):
    """The current question is over, progress the game."""
    if context.chat_data["questions_completed"] == 5:
        end(update, context)
    else:
        context.chat_data["questions_completed"] += 1
        with sqlite3.connect("clues.db") as con:
            cur = con.cursor()
            cur.execute(
                """
                SELECT clues.id, clue, answer, category, value
                FROM clues
                JOIN documents ON clues.id = documents.id
                JOIN classifications ON clues.id = classifications.clue_id
                JOIN categories ON classifications.category_id = categories.id
                ORDER BY RANDOM()
                LIMIT 1
                """
            )
            clue = cur.fetchone()
            context.chat_data["current_question"] = clue[1]
            context.chat_data["current_value"] = clue[4]
            # Strips the alternate answers and whitespace.
            # TODO: Get rid of "a" or "the" at the beginning.
            # TODO: Also remove periods.
            context.chat_data["current_answer"] = (
                re.sub(r"\([^)]*\)", "", clue[2]).strip().lower()
            )
            context.chat_data["current_hint"] = re.sub(
                r"\w", "-", context.chat_data["current_answer"]
            )
            context.chat_data["current_category"] = clue[3]
            context.chat_data["hint_level"] = 0
        update.message.reply_sticker(random.choice(STICKER_QUESTION), quote=False)
        # TODO: How do you make this indent not look super weird.
        question_ann = f"""🗂️Category: {context.chat_data['current_category']}
🤑Value: {context.chat_data['current_value']}
🙋Answer: {context.chat_data['current_question']}
🤔Hint: `{context.chat_data['current_hint']}`"""
        update.message.reply_text(
            question_ann, quote=False, parse_mode=ParseMode.MARKDOWN
        )
        # TODO: There has to be a better way to send context and update...
        context.job_queue.run_once(
            give_hint, HINT_TIME, context=(context, update), name=update.message.chat_id
        )


def stop(update, context):
    """Stop the quiz."""
    if "current_question" not in context.chat_data:
        update.message.reply_text("You're not in a round.")
    else:
        cancel_hints(update, context)
        del context.chat_data["current_question"]
        update.message.reply_text(
            f"Game over! The question was **{context.chat_data['current_answer']}**.",
            quote=False,
            parse_mode=ParseMode.MARKDOWN,
        )
        print_score(update, context)


def end(update, context):
    """Gracefully end the quiz."""
    cancel_hints(update, context)
    del context.chat_data["current_question"]
    update.message.reply_text(f"Game over!", quote=False)


def calcpoints(hint_level):
    """Calculate how many points to give."""
    levels = {0: 1.00, 1: 0.80, 2: 0.60}
    return levels.get(hint_level, 0)


def give_hint(context):
    """Print the current hint in the chat."""
    # TODO: Find a fast (non-loopy) way
    ans = context.job.context[0].chat_data["current_answer"]
    anslen = len(ans) // 3
    if anslen == 0:
        anslen = 1
    for _ in range(anslen):
        letter = random.randrange(0, len(ans))
        context.job.context[0].chat_data["current_hint"] = (
            context.job.context[0].chat_data["current_hint"][:letter]
            + context.job.context[0].chat_data["current_answer"][letter]
            + context.job.context[0].chat_data["current_hint"][letter + 1 :]
        )
    context.job.context[0].chat_data["hint_level"] += 1
    context.bot.send_message(
        chat_id=context.job.name,
        text="`" + context.job.context[0].chat_data["current_hint"] + "`",
        parse_mode=ParseMode.MARKDOWN,
    )
    if context.job.context[0].chat_data["hint_level"] > 1:
        context.job_queue.run_once(
            timeout, HINT_TIME, context=context.job.context, name=context.job.name
        )
    else:
        context.job_queue.run_once(
            give_hint, HINT_TIME, context=context.job.context, name=context.job.name
        )


def cancel_hints(update, context):
    """Cancel all scheduled tasks for the chat."""
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
            update.message.reply_sticker(random.choice(STICKER_CORRECT), quote=False)
            update.message.reply_text(
                f"✅Correct! The question was **{context.chat_data['current_answer']}**.",
                parse_mode=ParseMode.MARKDOWN,
            )
            pts = calcpoints(context.chat_data["hint_level"])
            if update.effective_user.first_name in context.chat_data["current_scores"]:
                context.chat_data["current_scores"][
                    update.effective_user.first_name
                ] += (pts * context.chat_data["current_value"])
            else:
                context.chat_data["current_scores"][
                    update.effective_user.first_name
                ] = (pts * context.chat_data["current_value"])
            print_score(update, context)
            progress_game(update, context)


def print_score(update, context):
    """Print the scores."""
    message = "💯Current scores..."
    for x in context.chat_data["current_scores"]:
        message += f"\n {x}: {context.chat_data['current_scores'][x]} points"
    if len(context.chat_data["current_scores"]) == 0:
        message += "\n No one has scored yet. 👀"
    update.message.reply_text(message, quote=False)


def timeout(context):
    """End the question if timeout is reached."""
    cancel_hints(context.job.context[1], context.job.context[0])
    context.job.context[1].message.reply_sticker(
        random.choice(STICKER_INCORRECT), quote=False
    )
    context.job.context[1].message.reply_text(
        f"❌No one got it. The question was **{context.job.context[0].chat_data['current_answer']}**.",
        quote=False,
        parse_mode=ParseMode.MARKDOWN,
    )
    print_score(context.job.context[1], context.job.context[0])
    progress_game(context.job.context[1], context.job.context[0])


def error(update, context):
    """Log Errors caused by Updates."""
    logger.warning('Update "%s" caused error "%s"', update, context.error)


def main():
    """Start the bot."""
    # Chat whitelist.
    whitelist = None
    if os.getenv("TG_SINGLE_CHAT"):
        whitelist = Filters.chat(chat_id=int(os.getenv("TG_SINGLE_CHAT")))

    # Use Persistence
    persistence = PicklePersistence(filename="data.pkl")

    # Create the Updater and pass it your bot's token.
    # Make sure to set use_context=True to use the new context based callbacks
    # Post version 12 this will no longer be necessary
    updater = Updater(
        os.getenv("TELEGRAM_TOKEN"), persistence=persistence, use_context=True
    )

    # Get the dispatcher to register handlers
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start, filters=whitelist))
    dp.add_handler(CommandHandler("stop", stop, filters=whitelist))

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


if __name__ == "__main__":
    main()
