#!/usr/bin/env python
# pylint: disable=C0116,W0613
# This program is dedicated to the public domain under the CC0 license.

import logging
from logging.handlers import TimedRotatingFileHandler
import sqlite3
import os
import yaml
import ast
from telegram import Update
from telegram.ext import Updater, CommandHandler, CallbackContext
from datetime import datetime

CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")

##### LOAD CONFIGURATION #####
CONFIG = yaml.load(open(CONFIG_PATH), Loader=yaml.FullLoader)

# Enable logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
log_handler = TimedRotatingFileHandler(CONFIG['log_path'], when='midnight', backupCount=10)
logger = logging.getLogger(__name__)
logger.addHandler(log_handler)

# This being an example and not having context present confusing beginners,
# we decided to have it present as context.

def block_alarm(context: CallbackContext) -> None:
    """Send the alarm message."""
    job = context.job
    print(CONFIG["cnclidb_path"])
    con = sqlite3.connect(CONFIG["cnclidb_path"])
    query_result = con.execute("select epoch, slot_qty, slots from slots order by epoch desc limit 1 ").fetchall()

    for slot in ast.literal_eval(query_result[0][2]):
        slot_time_sec = 1596491091 + (slot - 4924800)
        slot_datetime = datetime.fromtimestamp(slot_time_sec)
        slot_datestring = slot_datetime.strftime("%A, %B %d, %Y %I:%M:%S")
        slot_timediff =  slot_datetime - datetime.now()
        slot_minutesdiff = divmod(slot_timediff.total_seconds(), 60) 
        slot_stringdiff = ("{0}m {1}s").format(str(round(slot_minutesdiff[0])).rstrip('0').rstrip('.'),str(round(slot_minutesdiff[1])).rstrip('0').rstrip('.'))

        if slot_minutesdiff[0] > 0 and slot_minutesdiff[0] <= 240:
            message = "LEADERLOG \n slot scheduled on {0} \n countdown: {1}".format(slot_datestring, slot_stringdiff)
            context.bot.send_message(job.context, text=message)

    con.close()

def remove_job_if_exists(name: str, context: CallbackContext) -> bool:
    """Remove job with given name. Returns whether job was removed."""
    current_jobs = context.job_queue.get_jobs_by_name(name)
    if not current_jobs:
        return False
    for job in current_jobs:
        job.schedule_removal()
    return True

def set_timer(update: Update, context: CallbackContext) -> None:
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    try:
        job_removed = remove_job_if_exists(str(chat_id), context)
        #run once immediatly to evaluate any block coming up soon
        context.job_queue.run_once(block_alarm, 5, context=chat_id, name=str(chat_id))
        #run repeating job every hour
        context.job_queue.run_repeating(block_alarm, 3600, context=chat_id, name=str(chat_id))
        text = 'Block minting notification activated!'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Error setting up block notifications')

def unset(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Block notifications disabled!' if job_removed else 'You have no active block notifications.'
    update.message.reply_text(text)

def leaderlog(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    con = sqlite3.connect(CONFIG["cnclidb_path"])
    query_result = con.execute("select epoch, slot_qty, slots from slots order by epoch desc limit 1 ").fetchall()
    update.message.reply_text("Epoch: " + str(query_result[0][0]) +" | Slots: " + str(query_result[0][1]))
    con.close()

def main() -> None:
    """Run bot."""
    # Setup the Bot
    token = CONFIG["tgbot_token"]
    updater = Updater(token)
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("start", set_timer))
    dispatcher.add_handler(CommandHandler("disable", unset))
    dispatcher.add_handler(CommandHandler("leaderlog", leaderlog))

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()