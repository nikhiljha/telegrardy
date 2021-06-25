import random
from telegrardy import strings
from telegrardy.bot import clues
from jinja2 import Environment
import os

from loguru import logger
from prometheus_client import Gauge, Counter
from prometheus_client import start_http_server as prometheus_server
from telegram import ParseMode
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    PicklePersistence,
)

tpl = Environment()
stickers = strings["stickers"]

# Configurables
HINT_TIME = 20  # Time between each hint. 1/3 of round length.

# Monitoring
g_inprog = Gauge("games_in_progress", "number of games in progress")
c_errors = Counter('games_failed_updates', "telegram update errors")

def start(update, context):
    """Begin a round of the quiz."""
    # TODO: Make the round length configurable, with a maximum.
    if "question" not in context.chat_data:
        update.message.reply_text(strings["game_start"])
        context.chat_data["scores"] = {}
        context.chat_data["questions_completed"] = 0
        progress_game(update, context)
        g_inprog.inc()
    else:
        update.message.reply_text(strings["game_start_err"])


def progress_game(update, context):
    """The current question is over, progress the game."""
    if context.chat_data["questions_completed"] == 5:
        end(update, context)
    else:
        context.chat_data["questions_completed"] += 1
        context.chat_data.update(clues.random_question())
        context.chat_data["hint_level"] = 0
        update.message.reply_sticker(random.choice(stickers["question"]), quote=False)
        question_ann = tpl.from_string(strings["question_ann"]).render(
            data=context.chat_data
        )
        update.message.reply_text(
            question_ann, quote=False, parse_mode=ParseMode.MARKDOWN
        )
        # TODO: There has to be a better way to send context and update...
        context.job_queue.run_once(
            give_hint,
            HINT_TIME,
            context=(context, update),
            name=str(update.message.chat.id),
        )


def stop(update, context):
    """Stop the quiz."""
    if "question" not in context.chat_data:
        update.message.reply_text(strings["game_stop_err"])
    else:
        g_inprog.dec(1)
        cancel_hints(update, context)
        del context.chat_data["question"]
        update.message.reply_text(
            tpl.from_string(strings["game_stop"]).render(data=context.chat_data),
            quote=False,
            parse_mode=ParseMode.MARKDOWN,
        )
        print_score(update, context)


def end(update, context):
    """Gracefully end the quiz."""
    g_inprog.dec(1)
    cancel_hints(update, context)
    del context.chat_data["question"]
    update.message.reply_text(strings["game_end"], quote=False)


def calcpoints(hint_level):
    """Calculate how many points to give."""
    levels = {0: 1.00, 1: 0.80, 2: 0.60}
    return levels.get(hint_level, 0)


def give_hint(context):
    """Print the current hint in the chat."""
    # TODO: Find a fast (non-loopy) way
    ans = context.job.context[0].chat_data["answer"]
    anslen = len(ans) // 3
    if anslen == 0:
        anslen = 1
    for _ in range(anslen):
        letter = random.randrange(0, len(ans))
        context.job.context[0].chat_data["hint"] = (
            context.job.context[0].chat_data["hint"][:letter]
            + context.job.context[0].chat_data["answer"][letter]
            + context.job.context[0].chat_data["hint"][letter + 1 :]
        )
    context.job.context[0].chat_data["hint_level"] += 1
    context.bot.send_message(
        chat_id=context.job.name,
        text="`" + context.job.context[0].chat_data["hint"] + "`",
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
    q = context.job_queue.get_jobs_by_name(str(update.message.chat.id))
    for x in q:
        x.schedule_removal()


def check(update, context):
    """Check if the message matched the answer."""
    if "question" in context.chat_data:
        # TODO: Sanity Check: Make sure current answer exists.
        # If not, reset state because things are BROKEN.
        if context.chat_data["answer"] in update.message.text.lower():
            cancel_hints(update, context)
            update.message.reply_sticker(
                random.choice(stickers["correct"]), quote=False
            )
            update.message.reply_text(
                tpl.from_string(strings["question_correct"]).render(
                    data=context.chat_data
                ),
                parse_mode=ParseMode.MARKDOWN,
            )
            pts = calcpoints(context.chat_data["hint_level"])
            if update.effective_user.first_name in context.chat_data["scores"]:
                context.chat_data["scores"][update.effective_user.first_name] += int(
                    pts * int(context.chat_data["value"])
                )
            else:
                context.chat_data["scores"][update.effective_user.first_name] = int(
                    pts * int(context.chat_data["value"])
                )
            print_score(update, context)
            progress_game(update, context)


def print_score(update, context):
    """Print the scores."""
    message = strings["score_display"]
    for x in context.chat_data["scores"]:
        message += tpl.from_string(strings["score_template"]).render(
            name=x, points=context.chat_data["scores"][x]
        )
    if len(context.chat_data["scores"]) == 0:
        message += strings["score_null"]
    update.message.reply_text(message, quote=False)


def timeout(context):
    """End the question if timeout is reached."""
    cancel_hints(context.job.context[1], context.job.context[0])
    context.job.context[1].message.reply_sticker(
        random.choice(stickers["incorrect"]), quote=False
    )
    context.job.context[1].message.reply_text(
        tpl.from_string(strings["question_timeout"]).render(
            data=context.job.context[0].chat_data
        ),
        quote=False,
        parse_mode=ParseMode.MARKDOWN,
    )
    print_score(context.job.context[1], context.job.context[0])
    progress_game(context.job.context[1], context.job.context[0])


def handle_error(update, context):
    logger.error(f"(on update {update}) {context.error}")
    c_errors.inc()

def poll():
    # monitoring
    prometheus_server(8080)

    # chat whitelist
    whitelist = None
    if os.getenv("TG_SINGLE_CHAT"):
        whitelist = Filters.chat(chat_id=int(os.getenv("TG_SINGLE_CHAT")))

    persistence = PicklePersistence(filename="data.pkl")
    updater = Updater(os.getenv("TG_TOKEN"), persistence=persistence)
    dp = updater.dispatcher

    # on different commands - answer in Telegram
    dp.add_handler(CommandHandler("start", start, filters=whitelist))
    dp.add_handler(CommandHandler("stop", stop, filters=whitelist))

    # on noncommand i.e message - check if it was correct
    dp.add_handler(MessageHandler(Filters.text, check))

    # log all errors
    dp.add_error_handler(
        lambda update, context: logger.error(f"(on update {update}) {context.error}")
    )

    # start the bot
    updater.start_polling()
    updater.idle()
