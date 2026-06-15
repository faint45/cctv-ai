# -*- coding: utf-8 -*-
"""背景氣象監控:定時查雨量→告警/記錄;每天早上發當日施工風險建議。"""
import threading, time, datetime
import config, weather, notifier, gsheet, rainfall_history

class WeatherMonitor(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.running = True
        self.last_rain_alert = 0.0
        self.last_advisory_day = None
        self.last_backfill_day = None
        self.latest = {}     # 給面板顯示

    def build_advice(self, fc, warns):
        """規則式當日施工風險建議。"""
        tips = []
        high = None
        try: high = float(fc.get("high") or fc.get("temp"))
        except Exception: pass
        if high and high >= config.HEAT_ALERT_TEMP:
            tips.append(f"⚠️ 高溫 {high:.0f}°C:熱危害風險,加強遮陽/補水/輪休,避開正午時段")
        pop = fc.get("pop")
        try: popn = float(pop)
        except Exception: popn = None
        if popn is not None and popn >= 70:
            tips.append(f"🌧️ 降雨機率 {pop}%:備好排水/防滑,電氣設備防水")
        for w in warns:
            if "豪雨" in w or "大雨" in w:
                tips.append(f"🚨 {w}:評估高處/開挖作業停工,加強邊坡與積水巡查")
        if not tips:
            tips.append("✅ 今日無明顯氣象風險,正常施工注意一般工安")
        return "；".join(tips)

    def daily_advisory(self):
        fc = weather.get_forecast() or {}
        warns = weather.get_warnings()
        advice = self.build_advice(fc, warns)
        temp = f"{fc.get('low','?')}~{fc.get('high','?')}°C"
        pop = f"{fc.get('pop','?')}%"
        warn = "、".join(warns) if warns else "無"
        msg = f"📋 今日施工風險建議\n溫度 {temp} 降雨 {pop}\n特報:{warn}\n\n{advice}"
        notifier.notify("📋 今日施工風險建議", msg, alarm=False)
        gsheet.append_advisory(datetime.datetime.now().strftime("%Y-%m-%d"), temp, pop, warn, advice)
        print("[已發送當日風險建議]", advice)

    def run(self):
        if not config.CWA_API_KEY:
            print("[氣象監控停用] 未設定 CWA_API_KEY"); return
        print("氣象監控啟動")
        while self.running:
            try:
                rf = weather.get_rainfall()
                if rf:
                    lvl = weather.rain_alert_level(rf)
                    self.latest = {"rain": rf, "alert": lvl}
                    gsheet.append_rainfall(rf, lvl[1] if lvl else "")
                    now = time.time()
                    if lvl and (now - self.last_rain_alert) > 1800:   # 30分冷卻
                        title = "🚨 強降雨/停工" if lvl[0] == "stop" else "🌧️ 強降雨注意"
                        notifier.notify(title, f"{rf['station']} 站\n{lvl[1]}", alarm=(lvl[0]=="stop"))
                        self.last_rain_alert = now
                # 每日建議(到 ADVISORY_TIME 後第一次檢查時發,每天一次)
                today = datetime.date.today()
                ah, am = map(int, config.ADVISORY_TIME.split(":"))
                nowt = datetime.datetime.now()
                if self.last_advisory_day != today and (nowt.hour, nowt.minute) >= (ah, am):
                    self.daily_advisory(); self.last_advisory_day = today
                # 每日自動補歷史日雨量(昨日已定版)+ 更新 Sheet 圖表
                if datetime.datetime.now().hour == config.HIST_BACKFILL_HOUR and self.last_backfill_day != today:
                    try: rainfall_history.backfill(); print("[歷史雨量已自動更新]")
                    except Exception as e: print("[歷史雨量更新失敗]", e)
                    self.last_backfill_day = today
            except Exception as e:
                print("[氣象監控錯誤]", e)
            time.sleep(config.RAIN_CHECK_INTERVAL)

if __name__ == "__main__":
    m = WeatherMonitor(); m.run()
