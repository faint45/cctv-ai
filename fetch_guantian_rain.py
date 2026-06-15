# -*- coding: utf-8 -*-
# 抓取 CWA CODiS 官田自動氣象站 (C0X130) 日累積雨量
# 正確 API：POST https://codis.cwa.gov.tw/api/station?
#   form-urlencoded body:
#     date=YYYY-MM-01  type=report_month  stn_ID=C0X130
#     stn_type=auto_C0  more=  start=YYYY-MM-01T00:00:00  end=YYYY-MM-DDT23:59:59
import json, urllib.parse, urllib.request, csv

STN_ID = "C0X130"
STN_NAME = "官田"
STN_TYPE = "auto_C0"
OUT_CSV = r"D:\cctv-ai\官田日雨量_2026.csv"

# 每月查詢範圍 (start, end 為完整 ISO datetime)
MONTHS = [
    ("2026-04", "2026-04-01T00:00:00", "2026-04-30T23:59:59"),
    ("2026-05", "2026-05-01T00:00:00", "2026-05-31T23:59:59"),
    ("2026-06", "2026-06-01T00:00:00", "2026-06-15T23:59:59"),
]

def call(date, start, end, more=""):
    payload = {
        "date": date + "-01",
        "type": "report_month",
        "stn_ID": STN_ID,
        "stn_type": STN_TYPE,
        "more": more,
        "start": start,
        "end": end,
    }
    body = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(
        "https://codis.cwa.gov.tw/api/station?",
        data=body,
        headers={
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
            "User-Agent": "Mozilla/5.0",
            "Accept": "application/json",
            "Referer": "https://codis.cwa.gov.tw/StationData",
            "X-Requested-With": "XMLHttpRequest",
        },
    )
    r = urllib.request.urlopen(req, timeout=60)
    return json.loads(r.read().decode("utf-8"))

def clean(v):
    # 處理無資料/微量值。CWA 新版 JSON 用 null 表示無資料；
    # 字串 "T"/"x"/"-99"/"-990"/"-9991" 等視情況處理。
    if v is None:
        return None            # 無資料
    if isinstance(v, str):
        s = v.strip()
        if s in ("T", "t"):    # trace 微量 -> 0
            return 0.0
        if s in ("", "x", "X", "/", "-"):
            return None
        try:
            f = float(s)
        except ValueError:
            return None
    else:
        f = float(v)
    if f in (-99, -990, -991, -9991, -9.9, -99.0, -990.0):
        return None
    if f < 0:                  # 其餘負值視為無效
        return None
    return f

rows = []
for date, start, end in MONTHS:
    j = call(date, start, end)
    if j.get("code") != 200:
        print("ERROR", date, j.get("code"), j.get("message"))
        continue
    dts = j["data"][0]["dts"]
    for d in dts:
        day = d["DataDate"][:10]
        precp = clean((d.get("Precipitation") or {}).get("Accumulation"))
        rows.append((day, STN_NAME, precp))

rows.sort(key=lambda r: r[0])

with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
    w = csv.writer(f)
    w.writerow(["日期", "測站", "日雨量(mm)"])
    for day, name, p in rows:
        w.writerow([day, name, "" if p is None else round(p, 1)])

print("已寫入", OUT_CSV, "共", len(rows), "筆")
print("--- 前 10 筆 ---")
for r in rows[:10]:
    print(r[0], r[1], r[2])

# 月統計
def msum(prefix):
    vals = [p for d, n, p in rows if d.startswith(prefix) and p is not None]
    return round(sum(vals), 1), len(vals)

apr = msum("2026-04"); may = msum("2026-05"); jun = msum("2026-06")
print("--- 月統計 ---")
print("4月總雨量:", apr[0], "mm (", apr[1], "天有值)")
print("5月總雨量:", may[0], "mm (", may[1], "天有值)")
print("6月1-15日總雨量:", jun[0], "mm (", jun[1], "天有值)")
mx = max(((p, d) for d, n, p in rows if p is not None), default=(0, None))
print("最大單日雨量:", mx[0], "mm 於", mx[1])
