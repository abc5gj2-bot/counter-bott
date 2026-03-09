import os
import json
from datetime import datetime, timedelta, time

import discord
from discord.ext import tasks
from discord import app_commands

TOKEN = "MTQ4MDU0MzQwNjU0Njc1MTYyMA.GblH0j.it-iY8tKuXOYQ2n87VELHfuAfSyduYHL6YpTq8"

TARGET_CHANNEL_ID = 1474732960719835327  # ←集計結果を送るチャンネルID
DATA_FILE = "word_count.json"

# カウントしたいワード一覧
TARGET_WORDS = ["ちんこ", "ちんぽ", "ちんちん","チンコ", "チンポ", "チンチン"]

intents = discord.Intents.default()
intents.message_content = True
client = discord.Client(intents=intents)

# Slashコマンド用
tree = app_commands.CommandTree(client)


# -----------------------------
# JSON 読み書き
# -----------------------------
def load_data():
    if not os.path.exists(DATA_FILE):
        return {}
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


word_counts = load_data()


# -----------------------------
# 日付（JST）
# -----------------------------
def get_today_str():
    jst = datetime.utcnow() + timedelta(hours=9)
    return jst.strftime("%Y-%m-%d")


def get_yesterday_str():
    jst = datetime.utcnow() + timedelta(hours=9)
    y = jst - timedelta(days=1)
    return y.strftime("%Y-%m-%d")


# -----------------------------
# Bot 起動
# -----------------------------
@client.event
async def on_ready():
    print(f"Logged in as {client.user}")
    await tree.sync()  # Slashコマンド同期
    schedule_daily_report.start()


# -----------------------------
# メッセージ監視
# -----------------------------
@client.event
async def on_message(message):
    if message.author.bot:
        return

    content = message.content
    today = get_today_str()

    # 日付の初期化
    if today not in word_counts:
        word_counts[today] = {}

    # ワードごとにカウント
    for word in TARGET_WORDS:
        if word in content:
            word_counts[today][word] = word_counts[today].get(word, 0) + 1

    save_data(word_counts)


# -----------------------------
# 毎日0時（JST）に実行
# JST 0:00 = UTC 15:00（前日）
# -----------------------------
@tasks.loop(time=time(hour=15, minute=0, second=0))
async def schedule_daily_report():
    await send_yesterday_report()


async def send_yesterday_report():
    channel = client.get_channel(TARGET_CHANNEL_ID)
    if channel is None:
        print("Channel not found")
        return

    yesterday = get_yesterday_str()
    data = word_counts.get(yesterday, {})

    if not data:
        await channel.send(f"【{yesterday} の集計】\n該当ワードはありませんでした")
        return

    lines = [f"【{yesterday} のワード集計】"]
    for word, count in data.items():
        lines.append(f"・{word}: {count} 回")

    await channel.send("\n".join(lines))


# -----------------------------
# Slashコマンド：今日の途中経過
# -----------------------------
@tree.command(name="count_today", description="今日のワードカウントを表示します")
async def count_today(interaction: discord.Interaction):
    today = get_today_str()
    data = word_counts.get(today, {})

    if not data:
        await interaction.response.send_message(
            f"【{today} の集計】\nまだ該当ワードはありません"
        )
        return

    lines = [f"【{today} のワード集計（現在まで）】"]
    for word, count in data.items():
        lines.append(f"・{word}: {count} 回")

    await interaction.response.send_message("\n".join(lines))


client.run(TOKEN)
