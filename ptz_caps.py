# -*- coding: utf-8 -*-
"""唯讀:查 c1 球機 PTZ 節點支援哪些控制空間(pan/tilt/zoom、連續/相對/絕對)。"""
from onvif import ONVIFCamera
import config

cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
ptz = cam.create_ptz_service()

NODE = "00100"   # c1 = D1 球機
try:
    node = ptz.GetNode({'NodeToken': NODE})
    print("Node:", node.token, "name=", getattr(node, "Name", "?"))
    sp = getattr(node, "SupportedPTZSpaces", None)
    if sp:
        def show(label, items):
            print(f"\n[{label}] {len(items) if items else 0} 個")
            for s in (items or []):
                print("   URI:", getattr(s, "URI", "?"),
                      "X", getattr(getattr(s,'XRange',None),'Min','?'), "~", getattr(getattr(s,'XRange',None),'Max','?'))
        show("連續 PanTilt 速度", getattr(sp, "ContinuousPanTiltVelocitySpace", None))
        show("連續 Zoom 速度",    getattr(sp, "ContinuousZoomVelocitySpace", None))
        show("絕對 PanTilt 位置",  getattr(sp, "AbsolutePanTiltPositionSpace", None))
        show("絕對 Zoom 位置",    getattr(sp, "AbsoluteZoomPositionSpace", None))
        show("相對 PanTilt 位移",  getattr(sp, "RelativePanTiltTranslationSpace", None))
        show("相對 Zoom 位移",    getattr(sp, "RelativeZoomTranslationSpace", None))
    print("\nHomeSupported:", getattr(node, "HomeSupported", "?"))
    print("MaxPresets:", getattr(node, "MaximumNumberOfPresets", "?"))
except Exception as e:
    print("GetNode 失敗:", type(e).__name__, e)
