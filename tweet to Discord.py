import argparse
import concurrent.futures
import discord
import os
import signal
import shutil
import sqlite3
import ssl
import sys
import time

from discord.ext import commands, tasks
from tweety import Twitter

ssl._create_default_https_context = ssl._create_unverified_context
intents = discord.Intents.default()
try:
    intents.message_content = True
except Exception:
    pass
Bot = commands.Bot(command_prefix="!", intents=intents, help_command=None)

task_list = []
url_list = [{}]
_urls = []
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
                    return 'ツイートの取得に失敗しました'

    def old_tweet(self, user):
        try:
            return self.app.get_tweets(username=user, pages=1, replies=False, wait_time=3)[1].url
        except:
            try:
                tweet, _ = self.app.get_tweets(username=user, pages=1, replies=False, wait_time=3)[1]
                return tweet.url
            except:
                try:
                    return self.app.get_tweets(username=user, pages=1, replies=False, wait_time=3).tweets[1].url
                except:
                    return 'ツイートの取得に失敗しました'



class TweetDiscord(commands.Cog):
    def __init__(self, Bot: commands.Bot):
        self.bot = Bot
        self.twitter = Tweeter()
        self.data = {'': {'url': ''}}

    @discord.slash_command(name="set_tweet", description="設定したアカウントのツイートを監視します")
    async def set_tweet(self, cx: discord.ApplicationContext, username: str = ''):
        try:
            await cx.response.send_message(content='監視ユーザーを設定しました 設定ユーザー名: {}'.format(username), ephemeral=True)
        except:
            pass
        self.data = {'TwUser': username, username: {'url': ''}}
        task = tasks.loop(minutes=1)(self.auto_refresh_for_new_tweet)
        task_list.append(task)
        task.start(username, cx)

    async def auto_refresh_for_new_tweet(self, user, cx):
        now_url = self.twitter.new_tweet(user)
        if self.string_detect(now_url):
            _urls.append(now_url)
            if 2 <= len(url_list):
                for data in url_list:
                    if data['TwUser'] == user:
                        if data[user]['url'] != now_url:
                            data[user]['url'] = now_url
                            try:
                                if now_url.split('/')[2] == 'x.com':
                                    now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                                else:
                                    now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                                if now_url.split('/')[2][0:4] == 'fxfx':
                                    now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                                await cx.send(content=now_url)
                                url_list.append(data)
                            except IndexError:
                                data[user]['url'] = now_url
                                try:
                                    now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                                    if now_url.split('/')[2][0:4] == 'fxfx':
                                        now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                                    await cx.send(content=now_url)
                                    url_list.append(data)
                                except:
                                    pass
                            except:
                                try:
                                    now_url = self.twitter.old_tweet(user)
                                    data[user]['url'] = now_url
                                    if now_url.split('/')[2] == 'x.com':
                                        now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                                    else:
                                        now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                                    if now_url.split('/')[2][0:4] == 'fxfx':
                                        now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                                    await cx.send(content=now_url)
                                    url_list.append(data)
                                except IndexError:
                                    data[user]['url'] = now_url
                                    try:
                                        now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                                        if now_url.split('/')[2][0:4] == 'fxfx':
                                            now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                                        await cx.send(content=now_url)
                                        url_list.append(data)
                                    except:
                                        pass
                                except:
                                    pass
                    else:
                        continue
                if not self.search(user, url_list):
                    _data = {'TwUser': user, user: {'url': ''}}
                    _data[user]['url'] = now_url
                    try:
                        if now_url.split('/')[2] == 'x.com':
                            now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                        else:
                            now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                        if now_url.split('/')[2][0:4] == 'fxfx':
                            now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                        await cx.send(content=now_url)
                        url_list.append(_data)
                    except IndexError:
                        _data[user]['url'] = now_url
                        try:
                            now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                            if now_url.split('/')[2][0:4] == 'fxfx':
                                now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                            await cx.send(content=now_url)
                            url_list.append(_data)
                        except:
                            pass
                    except:
                        try:
                            now_url = self.twitter.old_tweet(user)
                            _data[user]['url'] = now_url
                            if now_url.split('/')[2] == 'x.com':
                                now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                            else:
                                now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                            if now_url.split('/')[2][0:4] == 'fxfx':
                                now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                            await cx.send(content=now_url)
                            url_list.append(_data)
                        except IndexError:
                            now_url = self.twitter.old_tweet(user)
                            _data[user]['url'] = now_url
                            try:
                                now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                                if now_url.split('/')[2][0:4] == 'fxfx':
                                    now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                                await cx.send(content=now_url)
                                url_list.append(_data)
                            except:
                                pass
                        except:
                            pass
            else:
                _data = {'TwUser': user, user: {'url': ''}}
                _data[user]['url'] = now_url
                url_list[0] = _data
                try:
                    if now_url.split('/')[2] == 'x.com':
                        now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                    else:
                        now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                    if now_url.split('/')[2][0:4] == 'fxfx':
                        now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                    await cx.send(content=now_url)
                    url_list.append(_data)
                except IndexError:
                    _data[user]['url'] = now_url
                    try:
                        now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                        if now_url.split('/')[2][0:4] == 'fxfx':
                            now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                        await cx.send(content=now_url)
                        url_list.append(_data)
                    except:
                        pass
                except:
                    try:
                        now_url = self.twitter.old_tweet(user)
                        _data[user]['url'] = now_url
                        if now_url.split('/')[2] == 'x.com':
                            now_url = 'fxtwitter.com'.join(now_url.split('x.com'))
                        else:
                            now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                        if now_url.split('/')[2][0:4] == 'fxfx':
                            now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                        await cx.send(content=now_url)
                        url_list.append(_data)
                    except IndexError:
                        try:
                            now_url = self.twitter.old_tweet(user)
                            _data[user]['url'] = now_url
                            now_url = 'fxtwitter.com'.join(now_url.split('twitter.com'))
                            if now_url.split('/')[2][0:4] == 'fxfx':
                                now_url = now_url.replace(now_url.split('/')[2], 'fxtwitter.com')
                            await cx.send(content=now_url)
                            url_list.append(_data)
                        except:
                            pass
                    except:
                        pass
            url_list[0:] = list({u['TwUser']: u for u in url_list}.values())
            _urls[0:] = list(set(_urls))

    def search(self, key, list):
        result = False
        for t in list:
            if key in t.keys():
                result = True
                break
        return result

    def string_detect(self, string_text: str) -> bool:
        len_text = 0
        for strings in _urls:
            if strings == string_text:
                len_text += 1
        if 1 <= len_text:
            return False
        else:
            return True

    @discord.slash_command(name="set_stop", description="設定したアカウントの監視を停止します")
    async def set_stop(self, cx: discord.ApplicationContext):
        for task in task_list:
            try:
                task.stop()
            except:
                pass
            try:
                task.cancel()
            except:
                pass
        url_list.clear()
        url_list.append({})
        try:
            await cx.delete()
        except:
            pass

    @discord.slash_command(name="get_tweet", description="設定したアカウントの最新のツイートを取得します")
    async def get_tweet(self, cx: discord.ApplicationContext, username: str = ''):
        text = self.twitter.new_tweet(username)
        if text != '':
            await cx.response.send_message(content=text, ephemeral=True)
        else:
            await cx.response.send_message(content='ツイートの取得に失敗しました', ephemeral=True)

    @discord.slash_command(name="stopall", description="Botを停止します")
    async def stopall(self, cx: discord.ApplicationContext):
        await cx.delete()
        print('Bot is Stopped!')
        stopped[0] = True
        await self.exits()
        signal.signal(signal.Signals.SIGKILL, signal.Signals.SIGINT)

    async def exits(self):
        sys.exit(0)


@Bot.event
async def on_ready():
    await Bot.change_presence(activity=discord.Game('BOTが正常に起動ました！(v1.0.0)'))


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
            print('稼働時間: {}年, {}週間, {}日, {}:{}:{}'.format(SYear, SWeek, SDay, SHour, SMinute, SSec), end='\r',
                  flush=True)
            time.sleep(1)
            Uptimeloop.append(i + 1)

    concurrent.futures.ThreadPoolExecutor().submit(TimeCounter)


def main():
    ArgumentPaerser = argparse.ArgumentParser(description='TweetDiscord')
    ArgumentPaerser.add_argument('--reset-login', '-rl', action='store_true', help='Twitterのログイン情報をリセットします')
    ArgumentPaerser.add_argument('--refresh-login', '-rfl', action='store_true', help='Twitterのログイン情報を更新します')
    ArgumentPaerser.add_argument('--reset-token', '-rt', action='store_true', help='Discordのトークン情報をリセットします')
    ArgumentPaerser.add_argument('--remove-all', '-ra', action='store_true', help='全てのログイン情報を消去します')
    arg = ArgumentPaerser.parse_args()
    if arg.reset_login:
        print('ログイン情報をリセットします')
        try:
            os.remove(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db'))
        except:
            pass
        connect_db(user_id=input('Twitterのユーザー名: '), password=input('Twitterのパスワード: '))
    if arg.refresh_login:
        print('ログイン情報を更新します')
        connect_db(user_id=input('Twitterのユーザー名: '), password=input('Twitterのパスワード: '))
    if arg.reset_token:
        print('トークン情報をリセットします')
        connect_db(token=input('Discordのトークン: '))
    if arg.remove_all:
        print('ログイン情報を削除しています........')
        try:
            shutil.rmtree(os.path.join(os.getcwd(), '.setting_twitter'))
            print('完了!')
        except:
            print('何らかのエラーで削除できませんでした')
    if not os.path.exists(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db')):
        connect_db(user_id=input('Twitterのユーザー名: '), password=input('Twitterのパスワード: '), token=input('Discordのトークン: '))
    if not arg.reset_login and not arg.refresh_login and not arg.reset_token and not arg.remove_all:
        _, __, TOKEN = connect_db()
        print('BOT Starting...')
        TimeCount()
        Bot.add_cog(TweetDiscord(Bot))
        Bot.run(TOKEN)


if __name__ == '__main__':
    try:
        main()
    except OSError:
        pass
