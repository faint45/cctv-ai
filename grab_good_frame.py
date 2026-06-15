# -*- coding: utf-8 -*-
"""暖機後抓一張完整影格(跳過 H.265 解碼未同步的灰畫面)。"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time, numpy as np
import config

def is_good(frame):
    # 灰雜訊畫面的標準差很低;真實畫面通常 > 25
    return frame is not None and float(frame.std()) > 18.0

url = config.rtsp_url(config.CHANNEL, 1)
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
best = None
t0 = time.time()
n = 0
while time.time() - t0 < 8:          # 最多暖機 8 秒
    ok, frame = cap.read()
    n += 1
    if not ok or frame is None:
        time.sleep(0.02); continue
    if is_good(frame):
        best = frame
        if n > 40:                    # 已暖機夠久,拿到好畫面就收
            break
cap.release()

if best is not None:
    cv2.imwrite("snapshots/good_frame.jpg", best)
    print(f"OK 抓到完整畫面 std={best.std():.1f} 共讀 {n} 張 -> snapshots/good_frame.jpg")
else:
    print(f"暖機 8 秒仍只拿到雜訊(讀了 {n} 張),可能該路攝影機沒接或編碼異常")
