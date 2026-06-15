# -*- coding: utf-8 -*-
"""叫球機回到指定預設點。用法: python ptz_goto.py <preset_token>"""
import sys, time
from onvif import ONVIFCamera
import config

TOKEN = "token:17/0/1/1/1/s0"
pt = sys.argv[1] if len(sys.argv) > 1 else "1"
cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
ptz = cam.create_ptz_service()

req = ptz.create_type('GotoPreset')
req.ProfileToken = TOKEN
req.PresetToken = str(pt)
try:
    ptz.GotoPreset(req)
    print(f"GotoPreset({pt}) 已送出,等待球機移動...")
    time.sleep(3)
    print("完成 —— D1 應該回到 ai_test 存的位置了")
except Exception as e:
    print("GotoPreset 失敗:", type(e).__name__, e)
