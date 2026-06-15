# -*- coding: utf-8 -*-
"""下載安全帽/PPE 預訓練模型,檢查類別,並在工地畫面上實測。"""
import os, urllib.request
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
from ultralytics import YOLO
import cv2

URL = "https://huggingface.co/keremberke/yolov8m-hard-hat-detection/resolve/main/best.pt"
DST = "helmet_yolov8m.pt"

if not os.path.exists(DST):
    print("下載安全帽模型中...")
    urllib.request.urlretrieve(URL, DST)
    print("下載完成:", DST, f"{os.path.getsize(DST)/1e6:.1f} MB")
else:
    print("已存在:", DST)

m = YOLO(DST)
print("模型類別:", m.names)

# 在已存的工地畫面 CH3/CH4 上測試
for ch in ["ch3", "ch4", "ch6"]:
    p = f"snapshots/{ch}.jpg"
    if os.path.exists(p):
        r = m(p, conf=0.3, device=0, verbose=False)[0]
        counts = {}
        for b in r.boxes:
            name = m.names[int(b.cls)]
            counts[name] = counts.get(name, 0) + 1
        print(f"{ch}: {counts if counts else '無偵測(畫面可能沒人)'}")
        cv2.imwrite(f"snapshots/{ch}_helmet.jpg", r.plot())
