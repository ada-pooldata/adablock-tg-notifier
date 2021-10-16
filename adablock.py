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

# Load Configuration
CONFIG = yaml.load(open(CONFIG_PATH), Loader=yaml.FullLoader)

# Setup logging
formatter = logging.Formatter(f'%(asctime)s %(levelname)s %(name)s %(threadName)s : %(message)s')
handler = TimedRotatingFileHandler(CONFIG['log_path'], when='midnight', backupCount=10)
handler.setFormatter(formatter)
logger = logging.getLogger(__name__)
logger.addHandler(handler)
logger.setLevel(logging.DEBUG)

def check_notification_range(minute_diff):
    for m in CONFIG["notification_minutes"]:
        if minute_diff >= m-1 and minute_diff < m:
            return True
    return False

# block notification logics
def block_alarm(context: CallbackContext) -> None:
    """Send the alarm message."""
    job = context.job
    con = sqlite3.connect(CONFIG["cnclidb_path"])
    query_result = con.execute("select epoch, slot_qty, slots from slots order by epoch desc limit 2 ").fetchall() # pick last 2 epochs

    for row in query_result:
        for slot in ast.literal_eval(row[2]):
            slot_time_sec = 1596491091 + (slot - 4924800) #convert slot# to timestamp in seconds
            slot_datetime = datetime.fromtimestamp(slot_time_sec)
            slot_datestring = slot_datetime.strftime("%A, %B %d, %Y %H:%M:%S")
            slot_timediff =  slot_datetime - datetime.now()
            slot_minutesdiff = divmod(slot_timediff.total_seconds(), 60) 
            slot_stringdiff = str(slot_timediff)

            if check_notification_range(slot_minutesdiff[0]):
                message = "LEADERLOG - slot: {0} \n- slot scheduled on {1} CET\n- countdown: {2}".format(str(slot), slot_datestring, slot_stringdiff)
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

# store chat ids with notification status to prevent resubscribing at every restart
def save_notification_status(chat_id, status): 
    con = sqlite3.connect(CONFIG["localdb_path"])
    try: 
        con.execute("INSERT INTO user_chats VALUES ({0},{1})".format(chat_id,int(status)))
    except sqlite3.IntegrityError:
        con.execute("UPDATE user_chats SET notifications = {1} WHERE chat_id = {0}".format(chat_id,int(status)))
    con.commit()
    con.close()

def enable_notifications(update: Update, context: CallbackContext) -> None:
    """Add a job to the queue."""
    chat_id = update.message.chat_id
    save_notification_status(chat_id,True)
    try:
        job_removed = remove_job_if_exists(str(chat_id), context)
        #run repeating job every 10s
        context.job_queue.run_repeating(block_alarm, 60, context=chat_id, name=str(chat_id))
        text = 'Block minting notification activated!'
        update.message.reply_text(text)

    except (IndexError, ValueError):
        update.message.reply_text('Error setting up block notifications')

def disable_notifications(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    save_notification_status(chat_id,False)
    job_removed = remove_job_if_exists(str(chat_id), context)
    text = 'Block notifications disabled!' if job_removed else 'You have no active block notifications.'
    update.message.reply_text(text)

def leaderlog(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    con = sqlite3.connect(CONFIG["cnclidb_path"])
    result = con.execute("select epoch, slot_qty, slots from slots order by epoch desc limit 1 ").fetchall()
    update.message.reply_text("Epoch: " + str(result[0][0]) +" | Slots: " + str(result[0][1]))
    con.close()

def nextslot(update: Update, context: CallbackContext) -> None:
    chat_id = update.message.chat_id
    con = sqlite3.connect(CONFIG["cnclidb_path"])
    result = con.execute("select slots from slots order by epoch desc limit 2").fetchall() # always check 2 epochs in case leaderlog already ran
    slot_list = []

    for row in result:
        slot_list = slot_list + ast.literal_eval(row[0])

    if slot_list == []:
        update.message.reply_text("There are no slots scheduled - try again after next leaderlog!")

    for slot in sorted(slot_list):
        slot_datetime = datetime.fromtimestamp(1596491091 + (slot - 4924800))
        slot_timediff =  slot_datetime - datetime.now()
        if slot_timediff.total_seconds() < 0:
            continue
        if slot_timediff.total_seconds() > 0:
            update.message.reply_text("Next Slot Scheduled: #{0}""\n- on: {1} CET\n- countdown: {2}".format(str(slot),str(slot_datetime.strftime("%A, %B %d, %Y %H:%M:%S")),str(slot_timediff)))
            break

    con.close()

# Setup internal SQLite database if needed
def create_localdb():
    con = sqlite3.connect(CONFIG["localdb_path"])
    con.execute("CREATE TABLE IF NOT EXISTS user_chats (chat_id INTEGER PRIMARY KEY AUTOINCREMENT, notifications INTEGER NOT NULL)")
    con.close()

def restore_notifications(updater):
    # enable notifications for saved users
    con = sqlite3.connect(CONFIG["localdb_path"])
    try: 
        result = con.execute("select chat_id from user_chats where notifications = 1").fetchall()
        for row in result:
            updater.job_queue.run_repeating(block_alarm, 60, context=row[0], name=str(row[0]))
    except Exception:
        pass
    finally:
        con.close()

def main() -> None:
    create_localdb()

    # Setup the Bot
    token = CONFIG["tgbot_token"]
    updater = Updater(token)
    restore_notifications(updater) # restore existing user notification settings
    dispatcher = updater.dispatcher
    dispatcher.add_handler(CommandHandler("enable", enable_notifications))
    dispatcher.add_handler(CommandHandler("start", enable_notifications))
    dispatcher.add_handler(CommandHandler("disable", disable_notifications))
    dispatcher.add_handler(CommandHandler("leaderlog", leaderlog))
    dispatcher.add_handler(CommandHandler("nextslot", nextslot))

    # Start the Bot
    updater.start_polling()
    updater.idle()

if __name__ == '__main__':
    main()