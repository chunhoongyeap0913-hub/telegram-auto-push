#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import requests
import datetime
import xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

# --- 1) 抓行情 (Yahoo Finance 无需 key)
SYMBOLS = os.getenv("MARKET_SYMBOLS", "^GSPC,^IXIC,^DJI,GC=F,CL=F,USDJPY=X,EURUSD=X")
symbols_param = SYMBOLS

yahoo_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={symbols_param}"
r = requests.get(yahoo_url, timeout=20)
quotes = {}
if r.status_code == 200:
    data = r.json()
    for q in data.get("quoteResponse", {}).get("result", []):
        sym = q.get("symbol")
        price = q.get("regularMarketPrice")
        change = q.get("regularMarketChange")
        change_pct = q.get("regularMarketChangePercent")
        quotes[sym] = {
            "price": price,
            "change": change,
            "pct": change_pct
        }
else:
    print("Yahoo Finance request failed", r.status_code)

# --- 2) 抓头条 (Google News RSS)
def get_news(query="market OR markets OR finance", n=3):
    rss_url = f"https://news.google.com/rss/search?q={requests.utils.requote_uri(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(rss_url, timeout=10)
        root = ET.fromstring(resp.content)
        items = root.findall('.//item')
        headlines = []
        for it in items[:n]:
            title = it.find('title').text or ""
            link = it.find('link').text or ""
            headlines.append((title, link))
        return headlines
    except Exception as e:
        print("News fetch error:", e)
        return []

headlines = get_news(n=3)

# --- 3) 生成消息（中文）
today = datetime.datetime.now().strftime("%Y-%m-%d")
lines = []
lines.append(f"📰 {today} 早间宏观摘要\n")

def fmt_quote(sym, info):
    if info is None:
        return f"{sym}: N/A"
    price = info.get("price")
    ch = info.get("change")
    pct = info.get("pct")
    sign = "+" if ch and ch > 0 else ""
    try:
        return f"{sym}: {price} ({sign}{round(ch,2)} / {sign}{round(pct,2)}%)"
    except Exception:
        return f"{sym}: {price}"

for s in SYMBOLS.split(","):
    info = quotes.get(s)
    lines.append(fmt_quote(s, info))

lines.append("\n📌 今日头条：")
if headlines:
    for t, link in headlines:
        lines.append(f"- {t}")
else:
    lines.append("- 无法获取新闻摘要")

lines.append("\n📝 学习主题与待办：")
lines.append("- 学习主题：美联储与宏观传导（继续）")
lines.append("- 待办：1) 阅读 FOMC 文稿 2) 整理笔记 3) 复盘上周数据")

lines.append("\n⚠️ 风险提示：注意美债收益率与重要数据发布。")

message = "\n".join(lines)

# --- 4) 发送到 Telegram
send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {
    "chat_id": TELEGRAM_CHAT_ID,
    "text": message,
    "disable_web_page_preview": True,
}

resp = requests.post(send_url, json=payload, timeout=15)
try:
    j = resp.json()
except Exception:
    j = {"ok": False, "status": resp.status_code, "text": resp.text}

print("Telegram response:", j)
if not j.get("ok"):
    print("Send failed:", j)
    sys.exit(1)

print("Send success")
