<div align="center">
	<a href="https://github.com/CrossDarkrix/featherCord">
	<img width="200px" height="200px" alt="featherCord" src="https://raw.githubusercontent.com/CrossDarkrix/featherCord/main/images/feathercord.png"></a>

# featherCord
a simple tweet transfer bot.

[English Version](https://github.com/CrossDarkrix/Tweet_to_discord/blob/main/README_EN.md)
</div>

## 📝説明
このBotはほぼリアルタイムでツイートリンクを取得してそれをfx_twitter形式で配信します。


## 実行に必要なモジュール
・[py-cord](https://github.com/Pycord-Development/pycord)

・[tweety-ns](https://github.com/mahrtayyab/tweety)

> [!IMPORTANT]
> 非公式apiを使っているので自己責任でお願いします。tweety-nsを悪用するとTwitterアカウントが凍結される可能性もあります。

## 機能
・/set_tweet: 設定したアカウントのポストを監視します

・/get_tweet: 指定したアカウントの最新のポストを取得します

・/set_stop: 指定したアカウントの監視を停止します

・/stop_all: Botをシャットダウンします

・/recovery_set_tweet: set_tweetの設定を再設定します。