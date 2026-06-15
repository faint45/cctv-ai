# -*- coding: utf-8 -*-
"""逐一抓 6 路攝影機各一張完整畫面,方便辨認哪一路是什麼。"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time
import config

def grab(channel, max_sec=7):
    url = config.rtsp_url(channel, 1)  # 子碼流
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    best = None
    t0 = time.time(); n = 0
    while time.time() - t0 < max_sec:
        ok, f = cap.read(); n += 1
        if ok and f is not None and float(f.std()) > 18:
            best = f
            if n > 35:
                break
    cap.release()
    if best is not None:
        out = f"snapshots/ch{channel}.jpg"
        cv2.imwrite(out, best)
        h, w = best.shape[:2]
        print(f"CH{channel}: OK {w}x{h} std={best.std():.0f} -> {out}")
        return True
    else:
        print(f"CH{channel}: 無有效畫面(可能沒接或暖機不足)")
        return False

if __name__ == "__main__":
    for ch in range(1, 7):
        grab(ch)
