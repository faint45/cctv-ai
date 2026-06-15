# -*- coding: utf-8 -*-
"""測試球機旋轉:右轉->左轉復原,上擺->下擺復原。你看 D1 有沒有轉。"""
import time
from onvif import ONVIFCamera
import config

TOKEN = "token:17/0/1/1/1/s0"   # c1 = D1 球機
cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
ptz = cam.create_ptz_service()

def move(pan=0.0, tilt=0.0, secs=1.5):
    req = ptz.create_type('ContinuousMove')
    req.ProfileToken = TOKEN
    req.Velocity = {'PanTilt': {'x': pan, 'y': tilt}, 'Zoom': {'x': 0.0}}
    ptz.ContinuousMove(req); time.sleep(secs)
    ptz.Stop({'ProfileToken': TOKEN, 'PanTilt': True, 'Zoom': True})

try:
    print("1) 向右轉 1.5 秒..."); move(pan=0.5); time.sleep(1)
    print("2) 向左轉回 1.5 秒..."); move(pan=-0.5); time.sleep(1)
    print("3) 向上擺 1.5 秒..."); move(tilt=0.5); time.sleep(1)
    print("4) 向下擺回 1.5 秒..."); move(tilt=-0.5)
    print("完成 —— D1 有左右轉、上下擺嗎?方向對不對(右轉是不是真的往右)?")
except Exception as e:
    print("旋轉指令失敗:", type(e).__name__, e)
