# -*- coding: utf-8 -*-
"""對 CH1(球機)做變焦測試:拉近 -> 比對 -> 復原。驗證 ONVIF 能否驅動。"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time, numpy as np
from onvif import ONVIFCamera
import config

CH = 1
TOKEN = "token:17/0/1/1/1/s0"   # CH1 主碼流 profile

cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
ptz = cam.create_ptz_service()

def grab(label, flush=40):
    """開 RTSP 抓一張有效畫面。"""
    cap = cv2.VideoCapture(config.rtsp_url(CH, 1), cv2.CAP_FFMPEG)
    best = None; t0 = time.time(); n = 0
    while time.time() - t0 < 8:
        ok, f = cap.read(); n += 1
        if ok and f is not None and float(f.std()) > 15:
            best = f
            if n > flush: break
    cap.release()
    if best is not None:
        cv2.imwrite(f"snapshots/ptz_{label}.jpg", best)
    return best

def move(zoom=0.0, pan=0.0, tilt=0.0, secs=2.0):
    req = ptz.create_type('ContinuousMove')
    req.ProfileToken = TOKEN
    req.Velocity = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': {'x': zoom}}
    ptz.ContinuousMove(req)
    time.sleep(secs)
    ptz.Stop({'ProfileToken': TOKEN, 'PanTilt': True, 'Zoom': True})

print("1) 抓拉近前畫面...")
before = grab("before")
print("   before std:", None if before is None else round(float(before.std()),1))

print("2) 送『變焦拉近』指令 2 秒...")
try:
    move(zoom=0.6, secs=2.0)
    print("   ContinuousMove(zoom+) 指令已送出,無例外")
except Exception as e:
    print("   PTZ 指令失敗:", type(e).__name__, e)

time.sleep(1)
print("3) 抓拉近後畫面...")
after = grab("after")

if before is not None and after is not None:
    diff = float(np.mean(cv2.absdiff(
        cv2.resize(before,(320,180)), cv2.resize(after,(320,180)))))
    print(f"\n畫面差異值: {diff:.1f}  ->  {'鏡頭有動! ✓ 這就是球機,ONVIF 可控' if diff > 8 else '幾乎沒變,可能不是球機或控制無效'}")

print("4) 變焦復原(zoom-)...")
try:
    move(zoom=-0.6, secs=2.0)
    print("   復原指令已送出")
except Exception as e:
    print("   復原失敗:", e)
print("完成。before/after 已存 snapshots/ptz_before.jpg, ptz_after.jpg")
