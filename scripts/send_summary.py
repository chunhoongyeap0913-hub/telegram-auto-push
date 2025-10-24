#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, sys, requests, datetime, xml.etree.ElementTree as ET

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_CHAT_ID")
FINNHUB_TOKEN = os.getenv("FINNHUB_TOKEN")

if not TELEGRAM_TOKEN or not TELEGRAM_CHAT_ID:
    print("❌ Missing TELEGRAM_TOKEN or TELEGRAM_CHAT_ID")
    sys.exit(1)

# 默认市场符号
SYMBOLS = os.getenv("MARKET_SYMBOLS", "^GSPC,^IXIC,^DJI,GC=F,CL=F,USDJPY=X,EURUSD=X").split(",")

# === 1) Finnhub 获取行情 ===
def fetch_from_finnhub(symbols):
    if not FINNHUB_TOKEN:
        return {}
    base = "https://finnhub.io/api/v1/quote"
    mapping = {
        "^GSPC": "US:SPX",
        "^IXIC": "US:NDX",
        "^DJI": "US:DJI",
        "GC=F": "OANDA:XAU_USD",
        "CL=F": "OANDA:WTICO_USD",
        "USDJPY=X": "FX:USDJPY",
        "EURUSD=X": "FX:EURUSD"
    }
    result = {}
    for s in symbols:
        try:
            fin_symbol = mapping.get(s, s)
            r = requests.get(base, params={"symbol": fin_symbol, "token": FINNHUB_TOKEN}, timeout=8)
            if r.status_code == 200:
                j = r.json()
                if j.get("c") is not None:
                    result[s] = {
                        "price": j["c"],
                        "change": j.get("d", 0),
                        "pct": j.get("dp", 0)
                    }
        except Exception as e:
            print(f"⚠️ Finnhub fetch error for {s}: {e}")
    return result

# === 2) Yahoo Finance 备用 ===
def fetch_from_yahoo(symbols):
    url = "https://query1.finance.yahoo.com/v7/finance/quote"
    result = {}
    try:
        r = requests.get(url, params={"symbols": ",".join(symbols)}, timeout=10)
        data = r.json()
        for q in data.get("quoteResponse", {}).get("result", []):
            result[q["symbol"]] = {
                "price": q.get("regularMarketPrice"),
                "change": q.get("regularMarketChange"),
                "pct": q.get("regularMarketChangePercent")
            }
    except Exception as e:
        print("⚠️ Yahoo fetch error:", e)
    return result

# === 获取行情 ===
quotes = fetch_from_finnhub(SYMBOLS)
missing = [s for s in SYMBOLS if s not in quotes]
if missing:
    quotes.update(fetch_from_yahoo(missing))

# === 3) 获取 Google News 头条 ===
def get_news(n=3):
    url = "https://news.google.com/rss/search?q=markets&hl=en-US&gl=US&ceid=US:en"
    try:
        r = requests.get(url, timeout=10)
        root = ET.fromstring(r.content)
        titles = [item.find("title").text for item in root.findall(".//item")[:n]]
        return titles
    except Exception as e:
        print("⚠️ News fetch error:", e)
        return []

news_titles = get_news()

# === 4) 构建消息 ===
today = datetime.datetime.now().strftime("%Y-%m-%d")
msg = [f"📰 {today} 早间宏观摘要\n"]

for s in SYMBOLS:
    q = quotes.get(s)
    if q:
        msg.append(f"{s}: {q['price']} ({q['change']} / {q['pct']}%)")
    else:
        msg.append(f"{s}: N/A")

msg.append("\n📌 今日头条：")
if news_titles:
    msg.extend([f"- {t}" for t in news_titles])
else:
    msg.append("- 暂无最新财经新闻")

msg.append("\n📝 学习主题与待办：")
msg.append("- 学习主题：美联储与宏观传导（继续）")
msg.append("- 待办：1) 阅读 FOMC 文稿  2) 整理笔记  3) 复盘上周数据")
msg.append("\n⚠️ 风险提示：关注美债收益率与经济数据发布。")

body = "\n".join(msg)

# === 5) 发送到 Telegram ===
r = requests.post(
    f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
    json={"chat_id": TELEGRAM_CHAT_ID, "text": body, "disable_web_page_preview": True},
    timeout=15
)
print("📤 Telegram response:", r.text)
