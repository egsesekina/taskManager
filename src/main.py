import asyncio
import logging
import sys

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram import html

from handlers import router

from aiogram import Bot

import redis
import json

REDIS_HOST = "localhost"
REDIS_PORT = 27020
REDIS_DB = 0
REDIS_QUEUE_REMINDERS = "reminders"
REDIS_QUEUE_DEADLINES = "expired"

TOKEN = '8044024877:AAEPIz1ImnnDWXFmmwE4qSGgaHg7txWjPhk'

# TOKEN = None

# if TOKEN == None:
#     print("Paste your token in main.py::23")
#     sys.exit()

import threading
import subprocess


def run_in_another_thread(path):
    subprocess.Popen(['python', path])

async def consumer_reminders(redis: redis.Redis, notificator):  # No need for aioredis now

    while True:
        result = await asyncio.to_thread(redis.blpop, REDIS_QUEUE_REMINDERS, timeout=3)  # Wrap in asyncio.to_thread
        if result:
            _, message_data_bytes = result
            message_data_str = message_data_bytes.decode('utf-8')
            try:
                print(message_data)
                message_data = json.loads(message_data_str)
                user_id = message_data["user_id"]
                title = message_data["title"]
                deadline = message_data["deadline"]
                await notificator.send_message(user_id, f"Remind you about your deadline on task {html.bold(title)},\nPlease notice: your deadline is on {html.bold(deadline)}")
            except json.JSONDecodeError:
                print(f"Consumer: Could not decode JSON: {message_data_str}")
        else:
            #print("Consumer: No messages in the queue, yielding control...")
            await asyncio.sleep(0.1)

async def consumer_deadline_expired(redis: redis.Redis, notificator):
    while True:
        result = await asyncio.to_thread(redis.blpop, REDIS_QUEUE_DEADLINES, timeout=3)  # Wrap in asyncio.to_thread
        if result:
            _, message_data_bytes = result
            message_data_str = message_data_bytes.decode('utf-8')
            try:
                message_data = json.loads(message_data_str)
                user_id = message_data["user_id"]
                title = message_data["title"]
                desc = message_data["description"]
                deadline = message_data["deadline"]
                await notificator.send_message(user_id, f'You missed your task {html.bold(title)}\nWe have extended your deadline by {html.italic("1 day")}\nPlease notice: your deadline currently is on {html.bold(deadline)}')

            except json.JSONDecodeError:
                print(f"Consumer: Could not decode JSON: {message_data_str}")
        else:
            #print("Consumer: No messages in the queue, yielding control...")
            await asyncio.sleep(0.1)

async def main():
    # Initialize Bot instance with default bot properties which will be passed to all API calls
    bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()

    # And the run events dispatching
    dp.include_router(router)


    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB)

    thread = threading.Thread(target=run_in_another_thread, args=('./notifier.py',))
    thread.start()

    await asyncio.gather(dp.start_polling(bot), consumer_reminders(r, bot), consumer_deadline_expired(r, bot))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stdout)
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("bot is off!")