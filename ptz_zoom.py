# -*- coding: utf-8 -*-
"""對指定通道送『變焦拉近 -> 復原』,用來確認哪一路是球機。
用法: python ptz_zoom.py <channel>   例: python ptz_zoom.py 1
你看著 NVR 的 D1,哪次 D1 會動,那個 channel 就是球機。"""
import sys, time
from onvif import ONVIFCamera
import config

ch = int(sys.argv[1]) if len(sys.argv) > 1 else 1
TOKEN = f"token:17/0/{ch}/1/{ch}/s0"

cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
ptz = cam.create_ptz_service()

def move(zoom, secs):
    req = ptz.create_type('ContinuousMove')
    req.ProfileToken = TOKEN
    req.Velocity = {'PanTilt': {'x': 0.0, 'y': 0.0}, 'Zoom': {'x': zoom}}
    ptz.ContinuousMove(req)
    time.sleep(secs)
    ptz.Stop({'ProfileToken': TOKEN, 'PanTilt': True, 'Zoom': True})

print(f"==> 測試 c{ch}:現在送『變焦拉近』2 秒,請看 NVR 的 D1 有沒有動")
try:
    move(0.7, 2.0)
    print("   拉近指令送出完成")
    time.sleep(1.5)
    print("==> 變焦復原中...")
    move(-0.7, 2.0)
    print("   復原完成。D1 剛剛有動嗎?")
except Exception as e:
    print("   PTZ 指令失敗:", type(e).__name__, e)
