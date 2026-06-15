# -*- coding: utf-8 -*-
"""旋轉測試 v2:Velocity 只帶 PanTilt(不帶 Zoom 欄位),用較大速度。"""
import time
from onvif import ONVIFCamera
import config

TOKEN = "token:17/0/1/1/1/s0"
cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
ptz = cam.create_ptz_service()

def pan_tilt(x=0.0, y=0.0, secs=2.0):
    req = ptz.create_type('ContinuousMove')
    req.ProfileToken = TOKEN
    req.Velocity = {'PanTilt': {'x': x, 'y': y}}   # 不帶 Zoom
    ptz.ContinuousMove(req); time.sleep(secs)
    ptz.Stop({'ProfileToken': TOKEN, 'PanTilt': True, 'Zoom': True})

try:
    print("1) 只送 PanTilt 向右 x=0.8, 2 秒..."); pan_tilt(x=0.8); time.sleep(1.5)
    print("2) 向左轉回 x=-0.8, 2 秒...");        pan_tilt(x=-0.8); time.sleep(1.5)
    print("3) 向上 y=0.8, 2 秒...");             pan_tilt(y=0.8); time.sleep(1.5)
    print("4) 向下回 y=-0.8, 2 秒...");          pan_tilt(y=-0.8)
    print("完成 —— 這次 D1 有左右轉/上下擺嗎?")
except Exception as e:
    print("失敗:", type(e).__name__, e)
