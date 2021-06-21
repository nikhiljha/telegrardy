# telegrardy

/[ˈteləˌɡrärdiː](http://ipa-reader.xyz/?text=ˈteləˌ%C9%A1rärdi%CB%90)/ - Play the [J! Archive](https://j-archive.com) as a Telegram Bot

![issues badge](https://img.shields.io/github/issues/nikhiljha/telegrardy)
![forks badge](https://img.shields.io/github/forks/nikhiljha/telegrardy)
![stars badge](https://img.shields.io/github/stars/nikhiljha/telegrardy)
![license badge](https://img.shields.io/github/license/nikhiljha/telegrardy)

## Features

- Telegrardy automatically generates additional hints when people aren't getting the answer.
- Telegrardy uses the real question point values from the game of Jeopardy! where the clue was shown.
- Telegrardy has fun stickers to tell you when you're right or wrong!
- The J! Archive is a fan website with the most complete collection of Jeopardy! clues and answers.
- The Jeopardy! game show and all elements thereof, including but not limited to copyright and trademark thereto, are the property of Jeopardy Productions, Inc. and are protected under law. This project is not affiliated with, sponsored by, or operated by Jeopardy Productions, Inc.

## Usage

1. Ask [@BotFather](https://t.me/Botfather) to make you a bot, and set the key as `TELEGRAM_TOKEN` in your environment.
2. Use the [J! Archive scraper](https://github.com/nikhiljha/jeopardy-parser) to obtain the Jeopardy clue database.
3. Put the `clues.db` that you scraped into this folder.
4. Install requirements: `pip install -r requirements.txt`
5. Run the bot: `python telegrardy.py`

## Configuration

You can set the `TG_SINGLE_CHAT` environment variable to the chat ID of your choice to only enable the bot in a single chat or for a single user.
