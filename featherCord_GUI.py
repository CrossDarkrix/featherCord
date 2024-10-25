# -*- coding: utf-8 -*-

import asyncio
import concurrent.futures
import multiprocessing
import os
import shutil
import signal
import sqlite3
import ssl
import sys
import threading
import time

import discord
from PySide6.QtCore import (QMetaObject, QRect,
                            QSize)
from PySide6.QtGui import (QFont)
from PySide6.QtWidgets import (QApplication, QFrame, QLabel, QLineEdit,
                               QPushButton, QSizePolicy, QMainWindow)
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

    @discord.slash_command(name="set_tweet", description="設定したアカウントのツイートを監視します")
    async def set_tweet(self, cx: discord.ApplicationContext, username: str = ''):
        try:
            await cx.response.send_message(content='監視ユーザーを設定しました 設定ユーザー名: {}'.format(username), ephemeral=True)
        except:
            pass
        _urls = []
        task = tasks.loop(seconds=48)(self.auto_refresh_for_new_tweet)
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
                try:
                    now_url = self.twitter.old_tweet(user)
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

    @discord.slash_command(name="set_stop", description="指定したアカウントの監視を停止します")
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

    @discord.slash_command(name="get_tweet", description="指定したアカウントの最新のポストを取得します")
    async def get_tweet(self, cx: discord.ApplicationContext, username: str = ''):
        text = self.twitter.new_tweet(username)
        if text != '':
            await cx.response.send_message(content=text, ephemeral=True)
        else:
            await cx.response.send_message(content='ツイートの取得に失敗しました', ephemeral=True)

    @discord.slash_command(name="stop_all", description="Botをシャットダウンします")
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
    await Bot.change_presence(activity=discord.Game('BOTは正常に稼働しました！(ver.0.0.1)'))


class Ui_DisBOT(object):
    def setupUi(self, DisBOT):
        if not DisBOT.objectName():
            DisBOT.setObjectName(u"DisBOT")
        DisBOT.resize(673, 547)
        sizePolicy = QSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(DisBOT.sizePolicy().hasHeightForWidth())
        DisBOT.setSizePolicy(sizePolicy)
        DisBOT.setMinimumSize(QSize(673, 547))
        DisBOT.setMaximumSize(QSize(673, 547))
        DisBOT.setAutoFillBackground(False)
        self.UserID = QLineEdit(DisBOT)
        self.UserID.setObjectName(u"UserID")
        self.UserID.setGeometry(QRect(60, 59, 261, 31))
        self.UserPass = QLineEdit(DisBOT)
        self.UserPass.setObjectName(u"UserPass")
        self.UserPass.setGeometry(QRect(350, 59, 261, 31))
        self.label1 = QLabel(DisBOT)
        self.label1.setObjectName(u"label1")
        self.label1.setGeometry(QRect(70, 39, 141, 16))
        font = QFont()
        font.setPointSize(13)
        self.label1.setFont(font)
        self.label2 = QLabel(DisBOT)
        self.label2.setObjectName(u"label2")
        self.label2.setGeometry(QRect(350, 39, 141, 16))
        self.label2.setFont(font)
        self.UserID_2 = QLineEdit(DisBOT)
        self.UserID_2.setObjectName(u"UserID_2")
        self.UserID_2.setGeometry(QRect(60, 149, 551, 31))
        self.label3 = QLabel(DisBOT)
        self.label3.setObjectName(u"label3")
        self.label3.setGeometry(QRect(70, 127, 161, 16))
        self.label3.setFont(font)
        self.startEnd = QPushButton(DisBOT)
        self.startEnd.setObjectName(u"startEnd")
        self.startEnd.setGeometry(QRect(70, 239, 521, 61))
        self.startEnd.clicked.connect(self._start)
        self.label4 = QLabel(DisBOT)
        self.label4.setObjectName(u"label4")
        self.label4.setGeometry(QRect(80, 220, 141, 16))
        self.label4.setFont(font)
        self.reset_login = QPushButton(DisBOT)
        self.reset_login.setObjectName(u"reset_login")
        self.reset_login.setGeometry(QRect(110, 420, 181, 31))
        self.reset_login.setStyleSheet(u"QPushButton{background: Red;color: White}")
        self.reset_login.clicked.connect(self._reset_login)
        self.reset_token = QPushButton(DisBOT)
        self.reset_token.setObjectName(u"reset_token")
        self.reset_token.setGeometry(QRect(110, 480, 181, 31))
        self.reset_token.setStyleSheet(u"QPushButton{background: Red;color: White}")
        self.reset_token.clicked.connect(self._reset_token)
        self.remove_all = QPushButton(DisBOT)
        self.remove_all.setObjectName(u"remove_all")
        self.remove_all.setGeometry(QRect(330, 450, 181, 31))
        self.remove_all.setStyleSheet(u"QPushButton{background: Red;color: White}")
        self.remove_all.clicked.connect(self._remove_all)
        self.frame = QFrame(DisBOT)
        self.frame.setObjectName(u"frame")
        self.frame.setGeometry(QRect(10, 380, 651, 2))
        self.frame.setStyleSheet(u"QFrame{background:  Black;}")
        self.frame.setFrameShape(QFrame.StyledPanel)
        self.frame.setFrameShadow(QFrame.Raised)
        self.UpTime = QLabel(DisBOT)
        self.UpTime.setObjectName(u"UpTime")
        self.UpTime.setGeometry(QRect(20, 340, 641, 31))
        self.loop = asyncio.get_event_loop()
        if os.path.exists(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db')):
            user, passwd, token = connect_db()
            self.UserID.setText(user)
            self.UserPass.setText(passwd)
            self.UserID_2.setText(token)

        self.retranslateUi(DisBOT)
        QMetaObject.connectSlotsByName(DisBOT)

    def retranslateUi(self, DisBOT):
        DisBOT.setWindowTitle("FeatherCord")
        self.label1.setText("Twitter iD:")
        self.label2.setText("Twitter Password:")
        self.label3.setText("Discord BOT Token:")
        self.startEnd.setText("Start")
        self.label4.setText("ControlButtton:")
        self.reset_login.setText("Twitterのログイン情報をリセット")
        self.reset_token.setText("Discordのトークン情報をリセット")
        self.remove_all.setText("全てのログイン情報を消去")
        self.UpTime.setText('稼働時間: 00年, 00週間, 00日, 00:00:00')

    def TimeCount(self):
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
                self.UpTime.setText('稼働時間: {}年, {}週間, {}日, {}:{}:{}'.format(SYear, SWeek, SDay, SHour, SMinute, SSec))
                time.sleep(1)
                Uptimeloop.append(i + 1)

        self.timeThread = threading.Thread(target=TimeCounter, daemon=True)
        self.timeThread.start()

    def _remove_all(self):
        try:
            shutil.rmtree(os.path.join(os.getcwd(), '.setting_twitter'))
        except:
            pass
        self.UserID_2.setText('')
        self.UserID.setText('')
        self.UserPass.setText('')

    def _reset_token(self):
        connect_db(token=' ')
        self.UserID_2.setText(' ')

    def _reset_login(self):
        connect_db(user_id=' ', password=' ')
        self.UserID.setText(' ')
        self.UserPass.setText(' ')

    def _start(self):
        if self.startEnd.text() != 'Stop':
            self.startEnd.setText('Stop')
            if not os.path.exists(os.path.join(os.getcwd(), '.setting_twitter', 'loginInfo.db')):
                if self.UserID.text() != '' and self.UserPass.text() != '' and self.UserID_2.text() != '':
                    if self.UserID.text() != ' ' and self.UserPass.text() != ' ' and self.UserID_2.text() != ' ':
                        connect_db(user_id=self.UserID.text(), password=self.UserPass.text(), token=self.UserID_2.text())
            if self.UserID.text() != ' ' and self.UserPass.text() != ' ' and self.UserID_2.text() != ' ':
                if self.UserID.text() != '' and self.UserPass.text() != '' and self.UserID_2.text() != '':
                    user, passwd, TOKEN = connect_db()
                    if self.UserID.text() != user and self.UserPass.text() != passwd:
                        connect_db(user_id=self.UserID.text(), password=self.UserPass.text())
                    elif self.UserID.text() != user and self.UserPass.text() == passwd:
                        connect_db(user_id=self.UserID.text(), password=passwd)
                    if self.UserID_2.text() != TOKEN:
                        connect_db(token=self.UserID_2.text())
                    self.TimeCount()
                    Bot.add_cog(TweetDiscord(Bot))
                    self.process = threading.Thread(target=asyncio.run, daemon=True, args=(Bot.start(TOKEN), ))
                    self.process.start()
        else:
            self.process.join(0)
            stopped[0] = True
            self.timeThread.join(0)
            self.startEnd.setText('Start')
            self.UpTime.setText('稼働時間: 00年, 00週間, 00日, 00:00:00')


def main():
    app = QApplication(sys.argv)
    main_window = QMainWindow()
    ui_window = Ui_DisBOT()
    ui_window.setupUi(main_window)
    main_window.setFixedSize(main_window.size())
    main_window.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    if sys.platform == 'linux':
        multiprocessing.set_start_method('fork')
    else:
        multiprocessing.set_start_method('spawn')
    with concurrent.futures.ProcessPoolExecutor() as P:
        P.submit(main)
