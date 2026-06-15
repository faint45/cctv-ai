# -*- coding: utf-8 -*-
"""測試 ONVIF 預設點:存目前位置 -> 變焦離開 -> 叫回預設點。自我復原。"""
import time
from onvif import ONVIFCamera
import config

TOKEN = "token:17/0/1/1/1/s0"   # c1 = D1 球機
cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
ptz = cam.create_ptz_service()

def zoom(z, secs):
    req = ptz.create_type('ContinuousMove')
    req.ProfileToken = TOKEN
    req.Velocity = {'PanTilt': {'x': 0.0, 'y': 0.0}, 'Zoom': {'x': z}}
    ptz.ContinuousMove(req); time.sleep(secs)
    ptz.Stop({'ProfileToken': TOKEN, 'PanTilt': True, 'Zoom': True})

print("1) 存目前位置為預設點...")
preset_token = None
try:
    req = ptz.create_type('SetPreset')
    req.ProfileToken = TOKEN
    req.PresetName = "ai_test"
    res = ptz.SetPreset(req)
    preset_token = res if isinstance(res, str) else getattr(res, "PresetToken", res)
    print("   SetPreset 成功,token =", preset_token)
except Exception as e:
    print("   SetPreset 失敗:", type(e).__name__, e)

print("2) 故意變焦拉近 2 秒(離開原位)...")
zoom(0.7, 2.0); time.sleep(1)

print("3) 叫球機回到剛存的預設點...")
try:
    req = ptz.create_type('GotoPreset')
    req.ProfileToken = TOKEN
    req.PresetToken = preset_token
    ptz.GotoPreset(req)
    time.sleep(3)
    print("   GotoPreset 已送出 —— D1 有沒有變焦回去原來的廣度?")
except Exception as e:
    print("   GotoPreset 失敗:", type(e).__name__, e)

# 列出目前預設點
try:
    pres = ptz.GetPresets({'ProfileToken': TOKEN})
    print(f"4) 目前預設點數量: {len(pres)}")
    for p in pres[:10]:
        print("   -", getattr(p, "token", "?"), getattr(p, "Name", "?"))
except Exception as e:
    print("4) GetPresets:", type(e).__name__, e)
