# -*- coding: utf-8 -*-
"""唯讀:查每一路的 PTZ 節點/預設點/狀態,找出真正的球機(不會移動鏡頭)。"""
from onvif import ONVIFCamera
import config

cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
media = cam.create_media_service()
ptz = cam.create_ptz_service()
profiles = media.GetProfiles()

# 只看主碼流 profile(s0),每路一個
mains = {}
for p in profiles:
    t = p.token
    if t.endswith("s0") and "17/0/" in t:
        ch = t.split("/")[2]   # token:17/0/<ch>/...
        mains[ch] = p

# PTZ 節點
try:
    nodes = ptz.GetNodes()
    print(f"PTZ 節點數: {len(nodes)}")
    for n in nodes:
        print(f"  node token={n.token} name={getattr(n,'Name','?')} "
              f"maxPresets={getattr(n,'MaximumNumberOfPresets','?')}")
except Exception as e:
    print("GetNodes 失敗:", e)

print("\n各路 PTZ 狀態 / 預設點(唯讀):")
for ch in sorted(mains):
    p = mains[ch]
    info = []
    try:
        st = ptz.GetStatus({'ProfileToken': p.token})
        pos = getattr(st, "Position", None)
        if pos:
            pan = getattr(pos.PanTilt, "x", "?") if getattr(pos,"PanTilt",None) else "?"
            tilt = getattr(pos.PanTilt, "y", "?") if getattr(pos,"PanTilt",None) else "?"
            zoom = getattr(pos.Zoom, "x", "?") if getattr(pos,"Zoom",None) else "?"
            info.append(f"pos(pan={pan},tilt={tilt},zoom={zoom})")
    except Exception as e:
        info.append(f"status:{type(e).__name__}")
    try:
        pres = ptz.GetPresets({'ProfileToken': p.token})
        info.append(f"presets={len(pres)}")
        if pres:
            names = [getattr(x,'Name','?') for x in pres[:5]]
            info.append(f"presetNames={names}")
    except Exception as e:
        info.append(f"presets:{type(e).__name__}")
    print(f"  CH{ch}: " + "  ".join(info))
