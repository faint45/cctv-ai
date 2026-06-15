# -*- coding: utf-8 -*-
"""連 ONVIF,列出 media profiles,找出哪個支援 PTZ。"""
from onvif import ONVIFCamera
import config

HOST = config.NVR_HOST
PORT = 57134
USER, PW = config.RTSP_USER, config.RTSP_PASS

print(f"連線 ONVIF {HOST}:{PORT} ...")
cam = ONVIFCamera(HOST, PORT, USER, PW)

# 裝置資訊
try:
    info = cam.devicemgmt.GetDeviceInformation()
    print("廠牌:", info.Manufacturer, "| 型號:", info.Model, "| 韌體:", info.FirmwareVersion)
except Exception as e:
    print("GetDeviceInformation 失敗:", e)

# Media profiles
media = cam.create_media_service()
profiles = media.GetProfiles()
print(f"\n共 {len(profiles)} 個 media profile:")
ptz = None
try:
    ptz = cam.create_ptz_service()
except Exception as e:
    print("無法建立 PTZ service:", e)

for i, p in enumerate(profiles):
    has_ptz = getattr(p, "PTZConfiguration", None) is not None
    name = getattr(p, "Name", "?")
    token = p.token
    print(f"  [{i}] token={token}  name={name}  PTZ={'YES' if has_ptz else 'no'}")
    if has_ptz:
        print(f"       PTZConfig token: {p.PTZConfiguration.token}")

# 列出每個 profile 的 RTSP/串流(對應 channel)
print("\n各 profile 串流 URI:")
for p in profiles:
    try:
        from onvif import ONVIFService
        uri = media.GetStreamUri({'StreamSetup': {'Stream': 'RTP-Unicast',
              'Transport': {'Protocol': 'RTSP'}}, 'ProfileToken': p.token})
        print(f"  {p.token}: {uri.Uri}")
    except Exception as e:
        print(f"  {p.token}: (取 URI 失敗 {type(e).__name__})")
