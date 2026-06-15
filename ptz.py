# -*- coding: utf-8 -*-
"""球機(D1=c1)PTZ 控制模組。封裝已驗證的正確下法。

重點:PanTilt 與 Zoom 不可同一指令混送,要分開。
"""
import time, threading
from onvif import ONVIFCamera
import config

DOME_TOKEN = "token:17/0/1/1/1/s0"   # D1 = c1 球機
DOME_NODE  = "00100"

class Dome:
    def __init__(self):
        cam = ONVIFCamera(config.NVR_HOST, 57134, config.RTSP_USER, config.RTSP_PASS)
        self.ptz = cam.create_ptz_service()
        self.lock = threading.Lock()

    def _move(self, velocity, secs):
        req = self.ptz.create_type('ContinuousMove')
        req.ProfileToken = DOME_TOKEN
        req.Velocity = velocity
        with self.lock:
            self.ptz.ContinuousMove(req)
            time.sleep(secs)
            self.ptz.Stop({'ProfileToken': DOME_TOKEN, 'PanTilt': True, 'Zoom': True})

    def pan_tilt(self, x=0.0, y=0.0, secs=0.4):
        """x:左(-)右(+)  y:下(-)上(+)"""
        self._move({'PanTilt': {'x': x, 'y': y}}, secs)   # 不帶 Zoom!

    def zoom(self, z=0.0, secs=0.4):
        """z:拉遠(-)拉近(+)"""
        self._move({'Zoom': {'x': z}}, secs)              # 不帶 PanTilt!

    def stop(self):
        with self.lock:
            self.ptz.Stop({'ProfileToken': DOME_TOKEN, 'PanTilt': True, 'Zoom': True})

    def set_preset(self, name, token=None):
        """存目前位置為預設點。token 有給=覆蓋既有預設點;回傳真實 token。"""
        with self.lock:
            req = self.ptz.create_type('SetPreset')
            req.ProfileToken = DOME_TOKEN
            req.PresetName = name
            if token is not None:
                req.PresetToken = str(token)
            self.ptz.SetPreset(req)
        if token is not None:
            return str(token)
        # SetPreset 回傳的 token 不可靠,從清單找剛存的名字
        for p in self.get_presets():
            if getattr(p, "Name", None) == name:
                return p.token
        return None

    def goto_preset(self, token, wait=3.0):
        req = self.ptz.create_type('GotoPreset')
        req.ProfileToken = DOME_TOKEN
        req.PresetToken = str(token)
        with self.lock:
            self.ptz.GotoPreset(req)
        time.sleep(wait)

    def get_presets(self):
        try:
            return self.ptz.GetPresets({'ProfileToken': DOME_TOKEN})
        except Exception:
            return []

if __name__ == "__main__":
    d = Dome()
    print("目前預設點:")
    for p in d.get_presets():
        print("  token=", p.token, " name=", getattr(p, "Name", "?"))
