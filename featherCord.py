#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import argparse
import concurrent.futures
import signal
import os
import ssl
import sqlite3
import sys
import time
import threading
import json

import discord
from discord.ext import commands, tasks
from tweety import Twitter

ssl._create_default_https_context = ssl._create_unverified_context
intents = discord.Intents.default()
try:
    intents.message_content = True
except Exception:
    pass
Bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

task_data = []
stopped = [False]


def connect_db(user_id: str='', password: str='', token: str=''):
    if not os.path.exists(os.path.join(os.getcwd(), '.setting_twitter')):
        os.makedirs(os.path.join(os.getcwd(), '.setting_twitter'), exist_ok=True)
    if not os.path.exists(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db')):
        _connect = sqlite3.connect(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db'))
        _cur = _connect.cursor()
        _cur.execute('CREATE TABLE LoginInfomation(User STRING, Password STRING, TOKEN STRING)')
        _cur.execute('INSERT INTO LoginInfomation(User, Password, TOKEN) values("{}", "{}", "{}")'.format(user_id, password, token))
        _connect.commit()
        user = user_id
        passwd = password
        _token = token
    else:
        _connect = sqlite3.connect(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db'))
        _cur = _connect.cursor()
        _cur.execute('SELECT * FROM LoginInfomation')
        user, passwd, _token = _cur.fetchall()[0]
        if user_id != '' and password != '':
            _cur.execute('REPLACE INTO LoginInfomation(User, Password) values("{}", "{}")'.format(user_id, password))
        if user_id != '' and password != '' and token != '':
            _cur.execute('REPLACE INTO LoginInfomation(User, Password, TOKEN) values("{}", "{}", "{}")'.format(user_id, password, token))
        elif token != '':
            _cur.execute('REPLACE INTO LoginInfomation(TOKEN) values("{}")'.format(token))
    _cur.close()
    _connect.close()
    return user, passwd, _token


class Tweeter(object):
    def __init__(self):
        self.app = Twitter('session')
        username, password, _ = connect_db()
        self.app.sign_in(username, password)
        self.kill = 0

    def new_tweet(self, user):
        try:
            return self.app.get_tweets(username=user, pages=1, replies=False, wait_time=3)[0].url
        except:
            try:
                tweet, _ = self.app.get_tweets(username=user, pages=1, replies=False, wait_time=3)[0]
                return tweet.url
            except:
                try:
                    return self.app.get_tweets(username=user, pages=1, replies=False, wait_time=3).tweets[0].url
                except:
                    return 'no get tweet'


class TweetDiscord(commands.Cog):
    def __init__(self, Bot: commands.Bot):
        self.bot = Bot
        self.twitter = Tweeter()

    @commands.slash_command(name="recovery_set_tweet", description="recovery monitoring set account posts")
    async def recovery_set_tweet(self, cx: discord.commands.context.ApplicationContext):
        def recover_set_tweet(cxx: discord.TextChannel, username: str = ''):
            _urls = []
            task = tasks.loop(seconds=57)(self.auto_refresh_for_new_tweet)
            task_data.append({"username": username, "task_list": task})
            task.start(username, cxx, _urls)

        if os.path.exists(os.path.join(os.getcwd(), '.setting_twitter', 'set_channel.json')):
            with open(os.path.join(os.getcwd(), '.setting_twitter', 'set_channel.json'), 'r', encoding='utf-8') as scl:
                channel_jsn = json.load(scl)
            for channel in cx.guild.channels:
                try:
                    recover_set_tweet(channel, channel_jsn['{}'.format(channel.id)])
                except KeyError:
                    continue
                except Exception as Err:
                    print(Err)
            try:
                await cx.response.send_message(content='all monitoring account was setting', ephemeral=True)
            except:
                pass
        else:
            try:
                await cx.response.send_message(content='error: setting file not found', ephemeral=True)
            except:
                pass

    @commands.slash_command(name="delete_json", description="delete seting file")
    async def delete_json(self, cx: discord.commands.context.ApplicationContext):
        try:
            os.remove(os.path.join(os.getcwd(), '.setting_twitter', 'set_channel.json'))
        except:
            pass
        try:
            await cx.response.send_message(content='done', ephemeral=True)
        except:
            pass

    @commands.slash_command(name="set_tweet", description="monitoring set account posts")
    async def set_tweet(self, cx: discord.commands.context.ApplicationContext, username: str = ''):
        if os.path.exists(os.path.join(os.getcwd(), '.setting_twitter', 'set_channel.json')):
            with open(os.path.join(os.getcwd(), '.setting_twitter', 'set_channel.json'), 'r', encoding='utf-8') as scl:
                channel_jsn = json.load(scl)
        else:
            channel_jsn = dict()
        channel_jsn['{}'.format(cx.channel_id)] = username
        with open(os.path.join(os.getcwd(), '.setting_twitter', 'set_channel.json'), 'w', encoding='utf-8') as jsn_w:
            json.dump(channel_jsn, jsn_w, ensure_ascii=False, indent=4)
        try:
            await cx.response.send_message(content='監視ユーザーを設定しました 設定ユーザー名: {}'.format(username), ephemeral=True)
        except:
            pass
        _urls = []
        task = tasks.loop(seconds=57)(self.auto_refresh_for_new_tweet)
        task_data.append({"username": username, "task_list": task})
        task.start(username, cx, _urls)

    async def auto_refresh_for_new_tweet(self, user, cx, _urls: list):
        def string_detect(string_text: str) -> bool:
            len_text = 0
            for strings in _urls:
                if strings == string_text:
                    len_text += 1
            if 1 <= len_text:
                return False
            else:
                return True

        now_url = self.twitter.new_tweet(user)
        if string_detect(now_url):
            _urls.append(now_url)
            try:
                if now_url.split('/')[2] == 'x.com':
                    now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                else:
                    now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                if now_url.split('/')[2][0:4] == 'fxfx':
                    now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                await cx.send(content=now_url)
            except IndexError:
                try:
                    now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                    if now_url.split('/')[2][0:4] == 'fxfx':
                        now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                    await cx.send(content=now_url)
                except:
                    pass
            except:
                pass
            _urls[0:] = list(set(_urls))

        def string_detect(string_text: str) -> bool:
            len_text = 0
            for strings in _urls:
                if strings == string_text:
                    len_text += 1
            if 1 <= len_text:
                return False
            else:
                return True

        now_url = self.twitter.new_tweet(user)
        if string_detect(now_url):
            _urls.append(now_url)
            try:
                if now_url.split('/')[2] == 'x.com':
                    now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                else:
                    now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                if now_url.split('/')[2][0:4] == 'fxfx':
                    now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                await cx.send(content=now_url)
            except IndexError:
                try:
                    now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                    if now_url.split('/')[2][0:4] == 'fxfx':
                        now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                    await cx.send(content=now_url)
                except:
                    pass
            except:
                pass
            _urls[0:] = list(set(_urls))

    @commands.slash_command(name="set_stop", description="stop monitoring account.")
    async def set_stop(self, cx: discord.ApplicationContext, user_name):
        for _json in task_data:
            if _json["username"] == user_name:
                try:
                    _json["task_list"].stop()
                except:
                    pass
                try:
                    _json["task_list"].cancel()
                except:
                    pass
        try:
            await cx.delete()
        except:
            pass

    @commands.slash_command(name="get_tweet", description="get new post")
    async def get_tweet(self, cx: discord.ApplicationContext, username: str = ''):
        text = self.twitter.new_tweet(username)
        if text != 'no get tweet':
            await cx.response.send_message(content=text, ephemeral=True)
        else:
            await cx.response.send_message(content='no get post', ephemeral=True)

    @commands.slash_command(name="stop_all", description="shutdown bot")
    async def stop_all(self, cx: discord.ApplicationContext):
        await cx.delete()
        print('Bot is Stopped!')
        stopped[0] = True
        await self.exits()
        signal.signal(signal.Signals.SIGKILL, signal.Signals.SIGINT)

    async def exits(self):
        sys.exit(0)


@Bot.event
async def on_ready():
    await Bot.change_presence(activity=discord.Game('Bot is Started!(v0.0.1)'))


def TimeCount():
    Uptimeloop = [0]

    def TimeCounter():
        Year = 0
        Week = 0
        Day = 0
        Hour = 0
        Minute = 0
        Sec = 0
        for i in Uptimeloop:
            if stopped[0]:
                break
            if Sec == 59:
                Sec = 0
                Minute += 1
            else:
                Sec += 1
            if Minute == 59:
                Minute = 0
                Hour += 1
            if Hour == 24:
                Hour = 0
                Day += 1
            if Day == 7:
                Day = 0
                Week += 1
            if Week == 13:
                Week = 0
                Year += 1
            if Year <= 9:
                SYear = '0{}'.format(Year)
            else:
                SYear = '{}'.format(Year)
            if Week <= 9:
                SWeek = '0{}'.format(Week)
            else:
                SWeek = '{}'.format(Week)
            if Day <= 9:
                SDay = '0{}'.format(Day)
            else:
                SDay = '{}'.format(Day)
            if Hour <= 9:
                SHour = '0{}'.format(Hour)
            else:
                SHour = '{}'.format(Hour)
            if Minute <= 9:
                SMinute = '0{}'.format(Minute)
            else:
                SMinute = '{}'.format(Minute)
            if Sec <= 9:
                SSec = '0{}'.format(Sec)
            else:
                SSec = '{}'.format(Sec)
            print('Uptime: {}year, {}week, {}day, {}:{}:{}'.format(SYear, SWeek, SDay, SHour, SMinute, SSec), end='\r', flush=True)
            time.sleep(1)
            Uptimeloop.append(i + 1)

    concurrent.futures.ThreadPoolExecutor().submit(TimeCounter)


def main():
    ArgumentPaerser = argparse.ArgumentParser(description='TweetDiscord')
    ArgumentPaerser.add_argument('--reset-login', '-rl', action='store_true', help='reset login data for twitter.')
    ArgumentPaerser.add_argument('--reset-token', '-rt', action='store_true', help='reset discord token')
    ArgumentPaerser.add_argument('--remove-all', '-ra', action='store_true', help='all account data delete')
    arg = ArgumentPaerser.parse_args()
    if arg.reset_login:
        print('reset login data')
        connect_db(user_id=input('Twitter(X) UserName: '), password=input('Twitter(X) Password: '))
    if arg.reset_token:
        print('reset token')
        connect_db(token=input('discard token: '))
    if arg.remove_all:
        print('delete all account data...')
        try:
            shutil.rmtree(os.path.join(os.getcwd(), '.setting_twitter'))
            print('done!')
        except:
            print('error')
    if not os.path.exists(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db')):
        connect_db(user_id=input('Twitter(X) UserName: '), password=input('Twitter(X) Password: '), token=input('discard token: '))
    if not arg.reset_login and not arg.reset_token and not arg.remove_all:
        _, __, TOKEN = connect_db()
        print('BOT Starting...')
        TimeCount()
        Bot.add_cog(TweetDiscord())
        Bot.run(TOKEN)


if __name__ == '__main__':
    try:
        main()
    except OSError:
        pass
