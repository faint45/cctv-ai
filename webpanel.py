# -*- coding: utf-8 -*-
"""CCTV AI 整合控制面板(Flask)。
功能:6 路即時畫面 / 球機 PTZ 搖桿 / 預設點存取 / AI 偵測開關 / 違規紀錄 / 推播 QR。
跑法: python webpanel.py  然後瀏覽 http://localhost:8080
"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time, threading, csv, io, json
from pathlib import Path
from flask import Flask, Response, jsonify, request, send_file, render_template_string
import qrcode
import config, notifier
import construction_monitor as cm
from ptz import Dome
from weather_monitor import WeatherMonitor
import weather

app = Flask(__name__)

# 球機(沿用 monitor 已建的,或自己建)
dome = cm.dome_mgr.dome
if dome is None:
    try: dome = Dome()
    except Exception as e: print("Dome init fail:", e); dome = None

PRESET_FILE = config.PRESET_FILE
def load_presets():
    return json.load(open(PRESET_FILE, encoding="utf-8")) if os.path.exists(PRESET_FILE) else {}
def save_presets(d):
    json.dump(d, open(PRESET_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

# ---- 即時畫面讀取(原始) ----
class RawReader(threading.Thread):
    def __init__(self, ch):
        super().__init__(daemon=True)
        self.ch = ch; self.latest = None; self.running = True
    def run(self):
        cap = cv2.VideoCapture(config.rtsp_url(self.ch, 1), cv2.CAP_FFMPEG)
        fails = 0
        while self.running:
            ok, f = cap.read()
            if not ok or f is None or float(f.std()) < 12:
                fails += 1
                if fails > 50:
                    cap.release(); time.sleep(1)
                    cap = cv2.VideoCapture(config.rtsp_url(self.ch, 1), cv2.CAP_FFMPEG); fails = 0
                continue
            fails = 0; self.latest = f
        cap.release()

ALL_CH = [1, 2, 3, 4, 5, 6]
readers = {ch: RawReader(ch) for ch in ALL_CH}
for r in readers.values(): r.start()

# AI 偵測 workers(可開關)
det_workers = {}
def start_detection():
    for ch in config.CONSTRUCTION_CHANNELS:
        if ch not in det_workers:
            w = cm.CameraWorker(ch, mode="construction"); w.start(); det_workers[ch] = w
    for ch in config.TRACK_CHANNELS:           # 月台軌道侵入
        if ch not in det_workers:
            w = cm.CameraWorker(ch, mode="track"); w.start(); det_workers[ch] = w
def stop_detection():
    for ch, w in list(det_workers.items()):
        w.running = False; del det_workers[ch]

def get_frame(ch):
    w = det_workers.get(ch)
    if w is not None and w.latest is not None:
        return w.latest               # 偵測中 -> 顯示標註畫面
    return readers[ch].latest          # 否則原始畫面

def mjpeg(ch):
    while True:
        f = get_frame(ch)
        if f is not None:
            ok, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 70])
            if ok:
                yield (b"--frame\r\nContent-Type: image/jpeg\r\n\r\n" + buf.tobytes() + b"\r\n")
        time.sleep(0.07)

@app.route("/video/<int:ch>")
def video(ch):
    return Response(mjpeg(ch), mimetype="multipart/x-mixed-replace; boundary=frame")

# ---- PTZ ----
@app.route("/ptz", methods=["POST"])
def ptz():
    if not dome: return jsonify(ok=False, err="球機未連線")
    a = request.json.get("action"); s = float(request.json.get("secs", 0.4)); step = 0.6
    try:
        if a == "left": dome.pan_tilt(x=-step, secs=s)
        elif a == "right": dome.pan_tilt(x=step, secs=s)
        elif a == "up": dome.pan_tilt(y=step, secs=s)
        elif a == "down": dome.pan_tilt(y=-step, secs=s)
        elif a == "zoomin": dome.zoom(z=step, secs=s)
        elif a == "zoomout": dome.zoom(z=-step, secs=s)
        else: return jsonify(ok=False, err="未知動作")
        return jsonify(ok=True)
    except Exception as e:
        return jsonify(ok=False, err=str(e))

@app.route("/preset/save", methods=["POST"])
def preset_save():
    if not dome: return jsonify(ok=False, err="球機未連線")
    name = request.json["name"]; p = load_presets()
    tok = dome.set_preset(name, token=p.get(name)); p[name] = str(tok); save_presets(p)
    return jsonify(ok=True, presets=p)

@app.route("/preset/goto", methods=["POST"])
def preset_goto():
    if not dome: return jsonify(ok=False, err="球機未連線")
    name = request.json["name"]; p = load_presets()
    if name in p:
        dome.goto_preset(p[name], wait=2.5); return jsonify(ok=True)
    return jsonify(ok=False, err="預設點不存在")

@app.route("/presets")
def presets():
    return jsonify(load_presets())

# ---- 偵測開關 ----
@app.route("/monitor/<cmd>", methods=["POST"])
def monitor(cmd):
    if cmd == "start": start_detection(); return jsonify(ok=True, running=True)
    if cmd == "stop": stop_detection(); return jsonify(ok=True, running=False)
    return jsonify(ok=False)

@app.route("/monitor/status")
def monitor_status():
    return jsonify(running=len(det_workers) > 0, channels=list(det_workers.keys()))

# ---- 違規紀錄 ----
@app.route("/violations")
def violations():
    f = Path("logs/violations.csv"); rows = []
    if f.exists():
        with open(f, encoding="utf-8-sig") as fp:
            r = list(csv.reader(fp))
            for row in r[1:][-100:][::-1]:
                rows.append(row)
    return jsonify(rows=rows)

# ---- 推播 QR ----
weather_mon = WeatherMonitor()
if config.CWA_API_KEY:
    weather_mon.start()

@app.route("/rainfall/sync", methods=["POST"])
def rainfall_sync():
    import rainfall_history, threading as _t
    _t.Thread(target=rainfall_history.backfill, daemon=True).start()
    return jsonify(ok=True, msg="歷史雨量同步中(背景),完成後 Google Sheet 會更新")

@app.route("/weather")
def weather_now():
    out = dict(weather_mon.latest)
    try:
        out["forecast"] = weather.get_forecast()
        out["warnings"] = weather.get_warnings()
    except Exception:
        pass
    out["enabled"] = bool(config.CWA_API_KEY)
    return jsonify(out)

import json as _json
def load_zones():
    return _json.load(open(config.ZONE_FILE, encoding="utf-8")) if os.path.exists(config.ZONE_FILE) else {}
def save_zones(z):
    _json.dump(z, open(config.ZONE_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

@app.route("/zone/snap/<int:ch>")
def zone_snap(ch):
    f = readers[ch].latest if ch in readers else None
    if f is None:
        return ("no frame", 503)
    ok, buf = cv2.imencode(".jpg", f, [cv2.IMWRITE_JPEG_QUALITY, 80])
    return Response(buf.tobytes(), mimetype="image/jpeg")

@app.route("/zones")
def zones_get():
    return jsonify(load_zones())

@app.route("/zone/save", methods=["POST"])
def zone_save():
    d = request.json or {}
    ch = str(d.get("ch")); pts = d.get("points", [])
    z = load_zones(); z[ch] = pts; save_zones(z)
    # 即時套用到正在跑的 worker
    cm.ZONES[int(ch)] = pts
    w = det_workers.get(int(ch))
    if w: w.zone = pts
    return jsonify(ok=True, zones=z)

@app.route("/zoneeditor")
def zoneeditor():
    return render_template_string(ZONE_HTML)

@app.route("/announce", methods=["POST"])
def announce():
    snap = None
    if request.content_type and "multipart" in request.content_type:
        msg = request.form.get("message", "").strip()
        title = request.form.get("title", "").strip() or "📢 工地廣播"
        f = request.files.get("photo")
        if f and f.filename:
            import datetime as _dt
            snap = f"snapshots/broadcast_{_dt.datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            f.save(snap)
    else:
        d = request.json or {}
        msg = d.get("message", "").strip()
        title = d.get("title", "").strip() or "📢 工地廣播"
    if not msg:
        return jsonify(ok=False, err="訊息不可空白")
    ok = notifier.notify(title, msg, alarm=False, important=True, snapshot=snap)
    return jsonify(ok=ok)

@app.route("/qr.png")
def qr():
    url = f"https://ntfy.sh/{config.NTFY_TOPIC}"
    img = qrcode.make(url)
    buf = io.BytesIO(); img.save(buf, "PNG"); buf.seek(0)
    return send_file(buf, mimetype="image/png")

@app.route("/setup")
def setup():
    return render_template_string(SETUP_HTML, topic=config.NTFY_TOPIC)

@app.route("/")
def index():
    return render_template_string(INDEX_HTML, topic=config.NTFY_TOPIC,
                                  channels=ALL_CH, construction=config.CONSTRUCTION_CHANNELS)

INDEX_HTML = open(os.path.join(os.path.dirname(__file__), "panel.html"), encoding="utf-8").read() \
    if os.path.exists(os.path.join(os.path.dirname(__file__), "panel.html")) else "panel.html missing"
SETUP_HTML = open(os.path.join(os.path.dirname(__file__), "setup.html"), encoding="utf-8").read() \
    if os.path.exists(os.path.join(os.path.dirname(__file__), "setup.html")) else "setup.html missing"
ZONE_HTML = open(os.path.join(os.path.dirname(__file__), "zoneeditor.html"), encoding="utf-8").read() \
    if os.path.exists(os.path.join(os.path.dirname(__file__), "zoneeditor.html")) else "zoneeditor.html missing"

if __name__ == "__main__":
    print("控制面板啟動:http://localhost:8080  (手機同網段可用本機IP連)")
    app.run(host="0.0.0.0", port=8080, threaded=True)
