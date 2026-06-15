# -*- coding: utf-8 -*-
"""CODiS 歷史日雨量抓取與整合。
- backfill(): 抓 config.HIST_START ~ 今日,寫 CSV + 推 Google Sheet(含月統計圖表)
- daily_update(): 抓昨日已定版日雨量,單筆補進
正確 API:POST https://codis.cwa.gov.tw/api/station(stn_type=auto_C0,start/end 要完整 ISO)
"""
import json, urllib.parse, urllib.request, csv, datetime, calendar
from pathlib import Path
import config, gsheet

OUT_CSV = Path("logs/官田日雨量歷史.csv")

def _call(month_first, start, end):
    payload = {"date": month_first, "type": "report_month", "stn_ID": config.HIST_STN_ID,
               "stn_type": config.HIST_STN_TYPE, "more": "", "start": start, "end": end}
    req = urllib.request.Request("https://codis.cwa.gov.tw/api/station?",
        data=urllib.parse.urlencode(payload).encode(),
        headers={"Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                 "User-Agent": "Mozilla/5.0", "Accept": "application/json",
                 "Referer": "https://codis.cwa.gov.tw/StationData"})
    return json.loads(urllib.request.urlopen(req, timeout=60).read().decode("utf-8"))

def _clean(v):
    if v is None: return None
    if isinstance(v, str):
        s = v.strip()
        if s in ("T", "t"): return 0.0
        if s in ("", "x", "X", "/", "-"): return None
        try: f = float(s)
        except ValueError: return None
    else:
        f = float(v)
    if f < 0: return None
    return f

def fetch_month(year, month, last_day=None):
    ld = last_day or calendar.monthrange(year, month)[1]
    mf = f"{year:04d}-{month:02d}-01"
    j = _call(mf, f"{mf}T00:00:00", f"{year:04d}-{month:02d}-{ld:02d}T23:59:59")
    if j.get("code") != 200:
        print("CODiS 錯誤", mf, j.get("code"), j.get("message")); return []
    out = []
    for d in j["data"][0]["dts"]:
        day = d["DataDate"][:10]
        p = _clean((d.get("Precipitation") or {}).get("Accumulation"))
        out.append((day, p))
    return out

def fetch_range(start_month, end_date):
    """start_month 'YYYY-MM',end_date date 物件。回傳 [(date, mm)]。"""
    sy, sm = map(int, start_month.split("-"))
    rows = []
    y, m = sy, sm
    while (y, m) <= (end_date.year, end_date.month):
        ld = end_date.day if (y, m) == (end_date.year, end_date.month) else None
        rows += fetch_month(y, m, ld)
        m += 1
        if m > 12: m = 1; y += 1
    rows.sort(key=lambda r: r[0])
    return rows

def write_csv(rows):
    OUT_CSV.parent.mkdir(exist_ok=True)
    with open(OUT_CSV, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f); w.writerow(["日期", "測站", "日雨量(mm)"])
        for day, p in rows:
            w.writerow([day, config.HIST_STN_NAME, "" if p is None else round(p, 1)])

def backfill(today=None):
    today = today or datetime.date.today()
    rows = fetch_range(config.HIST_START, today)
    write_csv(rows)
    # 推 Google Sheet(整批,建分頁+圖表)
    payload_rows = [[d, ("" if p is None else round(p, 1))] for d, p in rows]
    gsheet.push_rainfall_history(config.HIST_STN_NAME, payload_rows)
    # 摘要
    def msum(pfx):
        v = [p for d, p in rows if d.startswith(pfx) and p is not None]; return round(sum(v), 1)
    print(f"回填 {len(rows)} 筆 -> {OUT_CSV}")
    return rows

if __name__ == "__main__":
    rows = backfill()
    mx = max(((p, d) for d, p in rows if p is not None), default=(0, None))
    print("最大單日:", mx[0], "mm 於", mx[1])
