#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, requests, datetime, xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

SYMBOLS = os.getenv("MARKET_SYMBOLS", "^GSPC,^IXIC,^DJI,GC=F,CL=F,USDJPY=X,EURUSD=X")
yahoo_url = f"https://query1.finance.yahoo.com/v7/finance/quote?symbols={SYMBOLS}"
quotes = {}
r = requests.get(yahoo_url, timeout=20)
if r.status_code == 200:
    for q in r.json().get("quoteResponse", {}).get("result", []):
        sym = q.get("symbol")
        quotes[sym] = {
            "price": q.get("regularMarketPrice"),
            "change": q.get("regularMarketChange"),
            "pct": q.get("regularMarketChangePercent"),
        }

def get_news(query="market OR markets OR finance", n=3):
    rss = f"https://news.google.com/rss/search?q={requests.utils.requote_uri(query)}&hl=en-US&gl=US&ceid=US:en"
    try:
        resp = requests.get(rss, timeout=10)
        root = ET.fromstring(resp.content)
        items = root.findall('.//item')
        return [(it.find('title').text or "") for it in items[:n]]
    except Exception as e:
        print("News fetch error:", e)
        return []

headlines = get_news(n=3)
today = datetime.datetime.now().strftime("%Y-%m-%d")
lines = [f"📰 {today} 早间宏观摘要\n"]
def fmt(sym,info):
    if not info: return f"{sym}: N/A"
    p = info.get("price")
    ch = info.get("change") or 0
    pct = info.get("pct") or 0
    sign = "+" if ch>0 else ""
    try:
        return f"{sym}: {p} ({sign}{round(ch,2)} / {sign}{round(pct,2)}%)"
    except:
        return f"{sym}: {p}"
for s in SYMBOLS.split(","):
    lines.append(fmt(s, quotes.get(s)))
lines.append("\n📌 今日头条：")
if headlines:
    for h in headlines:
        lines.append(f"- {h}")
else:
    lines.append("- 无法获取新闻摘要")
lines.append("\n📝 学习主题与待办：\n- 学习主题：美联储与宏观传导（继续）\n- 待办：1) 阅读 FOMC 文稿 2) 整理笔记 3) 复盘上周数据")
lines.append("\n⚠️ 风险提示：注意美债收益率与重要数据发布。")
message = "\n".join(lines)

send_url = f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage"
payload = {"chat_id": TELEGRAM_CHAT_ID, "text": message, "disable_web_page_preview": True}
resp = requests.post(send_url, json=payload, timeout=15)
try:
    j = resp.json()
except:
    j = {"ok": False, "status": resp.status_code, "text": resp.text}
print("Telegram response:", j)
if not j.get("ok"):
    print("Send failed:", j)
    sys.exit(1)
print("Send success")
