# -*- coding: utf-8 -*-
"""中央氣象署(CWA)氣象/雨量整合。
- 自動雨量站即時雨量(找最近站)
- 鄉鎮天氣預報(溫度、降雨機率)
- 天氣警特報(大雨/豪雨)
需在 config.CWA_API_KEY 填授權碼。
"""
import requests, math, time
import config

BASE = "https://opendata.cwa.gov.tw/api/v1/rest/datastore"

def _get(dataset, params=None):
    p = {"Authorization": config.CWA_API_KEY, "format": "JSON"}
    if params: p.update(params)
    r = requests.get(f"{BASE}/{dataset}", params=p, timeout=15)
    r.raise_for_status()
    return r.json()

def _dist(lat1, lon1, lat2, lon2):
    return math.hypot(lat1 - lat2, lon1 - lon2)

def _num(v):
    try:
        f = float(v)
        return f if f >= 0 else 0.0     # -99/-990 代表無資料
    except Exception:
        return None

def find_nearest_station():
    """從自動雨量站 O-A0002-001 找離工地最近的站。"""
    data = _get("O-A0002-001")
    stations = data.get("records", {}).get("Station", [])
    best, bestd = None, 1e9
    for s in stations:
        try:
            coord = s["GeoInfo"]["Coordinates"]
            # 取 WGS84
            wgs = next((c for c in coord if c.get("CoordinateName") == "WGS84"), coord[0])
            lat = float(wgs["StationLatitude"]); lon = float(wgs["StationLongitude"])
        except Exception:
            continue
        d = _dist(config.SITE_LAT, config.SITE_LON, lat, lon)
        if d < bestd:
            bestd, best = d, s
    return best

def get_rainfall():
    """回傳最近站的雨量 dict。"""
    data = _get("O-A0002-001")
    stations = data.get("records", {}).get("Station", [])
    target = None
    if config.RAIN_STATION:
        target = next((s for s in stations if s.get("StationName") == config.RAIN_STATION), None)
    if target is None:
        # 找最近
        best, bestd = None, 1e9
        for s in stations:
            try:
                wgs = next((c for c in s["GeoInfo"]["Coordinates"] if c.get("CoordinateName")=="WGS84"), None)
                lat=float(wgs["StationLatitude"]); lon=float(wgs["StationLongitude"])
            except Exception: continue
            d=_dist(config.SITE_LAT, config.SITE_LON, lat, lon)
            if d<bestd: bestd,best=d,s
        target=best
    if not target:
        return None
    re_ = target.get("RainfallElement", {})
    def g(*keys):
        for k in keys:
            if k in re_:
                return _num(re_[k].get("Precipitation"))
        return None
    return {
        "station": target.get("StationName"),
        "now":  g("Now"),
        "r10":  g("Past10Min", "Past10min"),
        "r1h":  g("Past1hr", "Past1Hour"),
        "r3h":  g("Past3hr", "Past3Hour"),
        "r24h": g("Past24hr", "Past24Hour"),
        "time": target.get("ObsTime", {}).get("DateTime", ""),
    }

def get_forecast():
    """縣市 36 小時預報(F-C0032-001):今明高低溫、降雨機率、天氣現象。"""
    try:
        data = _get("F-C0032-001", {"locationName": config.SITE_COUNTY})
        locs = data.get("records", {}).get("location", [])
        if not locs: return None
        out = {"county": config.SITE_COUNTY}
        for we in locs[0].get("weatherElement", []):
            nm = we.get("elementName")
            param = we.get("time", [{}])[0].get("parameter", {})
            v = param.get("parameterName")
            if nm == "MaxT": out["high"] = v
            elif nm == "MinT": out["low"] = v
            elif nm == "PoP": out["pop"] = v
            elif nm == "Wx": out["wx"] = v
            elif nm == "CI": out["ci"] = v
        return out
    except Exception as e:
        print("[forecast 失敗]", e); return None

def get_warnings():
    """天氣警特報(W-C0033-001),回傳本縣市的特報標題清單。"""
    try:
        data = _get("W-C0033-001", {"locationName": config.SITE_COUNTY})
        recs = data.get("records", {}).get("location", [])
        out = []
        for loc in recs:
            for haz in loc.get("hazardConditions", {}).get("hazards", []):
                info = haz.get("info", {})
                out.append(info.get("phenomena", "") + info.get("significance", ""))
        return [x for x in out if x]
    except Exception as e:
        print("[warning 失敗]", e); return []

def rain_alert_level(rf):
    """依雨量門檻判斷告警等級。回傳 (level, message) 或 None。"""
    if not rf: return None
    r1h = rf.get("r1h") or 0; r10 = rf.get("r10") or 0
    if r1h >= config.RAIN_1HR_STOP:
        return ("stop", f"時雨量 {r1h}mm 達停工門檻,建議評估停工/防汛")
    if r1h >= config.RAIN_1HR_ALERT or r10 >= config.RAIN_10MIN_ALERT:
        return ("warn", f"強降雨:時雨量 {r1h}mm、10分 {r10}mm,注意排水/滑倒")
    return None

if __name__ == "__main__":
    if not config.CWA_API_KEY:
        print("請先在 config.py 填 CWA_API_KEY(opendata.cwa.gov.tw 申請)")
    else:
        print("最近雨量站:")
        s = find_nearest_station()
        print("  ", s.get("StationName") if s else "找不到")
        print("即時雨量:", get_rainfall())
        print("今日預報:", get_forecast())
        print("天氣特報:", get_warnings())
