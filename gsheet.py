# -*- coding: utf-8 -*-
"""把違規紀錄送到 Google Sheet(透過 Apps Script Web App)。
失敗不影響監控主流程(背景送、吞例外)。"""
import requests, threading, csv
from pathlib import Path
import config

def _post(row):
    url = getattr(config, "GSHEET_WEBHOOK_URL", "")
    if not getattr(config, "GSHEET_ENABLE", False) or not url:
        return False
    try:
        r = requests.post(url, json={
            "time": row[0], "camera": row[1], "type": row[2],
            "count": row[3], "detail": row[4], "snapshot": row[5] if len(row) > 5 else "",
        }, timeout=8)
        return r.status_code == 200
    except Exception as e:
        print("[GSheet 失敗]", e)
        return False

def append_async(row):
    """非阻塞送一筆違規到 Google Sheet。"""
    threading.Thread(target=_post, args=(row,), daemon=True).start()

def _post_json(payload):
    url = getattr(config, "GSHEET_WEBHOOK_URL", "")
    if not getattr(config, "GSHEET_ENABLE", False) or not url:
        return False
    try:
        r = requests.post(url, json=payload, timeout=10)
        return r.status_code == 200
    except Exception as e:
        print("[GSheet 失敗]", e); return False

def append_rainfall(rf, alert=""):
    """送一筆雨量紀錄(非阻塞)。"""
    payload = {"kind": "rainfall", "time": rf.get("time", ""), "station": rf.get("station", ""),
               "now": rf.get("now"), "r10": rf.get("r10"), "r1h": rf.get("r1h"),
               "r24h": rf.get("r24h"), "alert": alert}
    threading.Thread(target=_post_json, args=(payload,), daemon=True).start()

def push_rainfall_history(station, rows):
    """整批送歷史日雨量(Apps Script 會建『官田歷史雨量』分頁 + 月統計圖表)。"""
    payload = {"kind": "rainfall_history", "station": station, "rows": rows}
    ok = _post_json(payload)
    print("歷史雨量推送 Google Sheet:", "成功" if ok else "失敗(確認已重部署 Apps Script v3)")
    return ok

def append_advisory(date, temp, pop, warn, advice):
    """送一筆每日風險建議(非阻塞)。"""
    payload = {"kind": "advisory", "time": date, "temp": temp, "pop": pop,
               "warn": warn, "advice": advice}
    threading.Thread(target=_post_json, args=(payload,), daemon=True).start()

def sync_csv():
    """把現有 logs/violations.csv 全部補送到 Google Sheet(一次性回填)。"""
    f = Path("logs/violations.csv")
    if not f.exists():
        print("沒有 violations.csv"); return
    n = 0
    with open(f, encoding="utf-8-sig") as fp:
        for row in list(csv.reader(fp))[1:]:
            if _post(row): n += 1
    print(f"已回填 {n} 筆到 Google Sheet")

if __name__ == "__main__":
    if not config.GSHEET_WEBHOOK_URL:
        print("尚未設定 GSHEET_WEBHOOK_URL,請先部署 Apps Script(見 gsheet_appsscript.gs)")
    else:
        ok = _post(["2026-06-12 00:00:00", "CH3", "測試", 1, "Google Sheet 連線測試", ""])
        print("測試寫入:", "成功" if ok else "失敗")
