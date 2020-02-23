# telegrardy
/[ˈteləˌɡrärdiː](http://ipa-reader.xyz/)/ - Play the J! Archive as a Telegram Bot [WIP]

![](https://img.shields.io/github/issues/nikhiljha/telegrardy)
![](https://img.shields.io/github/forks/nikhiljha/telegrardy)
![](https://img.shields.io/github/stars/nikhiljha/telegrardy)
![](https://img.shields.io/github/license/nikhiljha/telegrardy)

## Usage
1. Ask [@BotFather](https://t.me/Botfather) to make you a bot, and set the key as `TELEGRAM_TOKEN` in your environment.
2. Use the [J! Archive scraper](https://github.com/nikhiljha/jeopardy-parser) to obtain the Jeopardy clue database.
3. Put the `clues.db` that you scraped into this folder.
4. Install requirements: `pip install -r requirements.txt`
5. Run the bot: `python telegrardy.py`

## Configuration
You can set the `TG_SINGLE_CHAT` environment variable to the chat ID of your choice to only enable the bot in a single chat or for a single user.
