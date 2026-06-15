# -*- coding: utf-8 -*-
"""端到端測試:拉流 -> YOLO(GPU) -> 數人 -> 量速度 -> 存標註圖。"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time
from ultralytics import YOLO
import config

print("載入模型", config.MODEL_PATH, "...")
model = YOLO(config.MODEL_PATH)

url = config.rtsp_url(config.CHANNEL, 1)
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)

# 暖機 + 蒐集幾張有效畫面測速
frames = []
t0 = time.time()
while time.time() - t0 < 8 and len(frames) < 30:
    ok, f = cap.read()
    if ok and f is not None and float(f.std()) > 18:
        frames.append(f)
cap.release()
print(f"取得 {len(frames)} 張有效畫面")

if not frames:
    print("沒有有效畫面"); raise SystemExit

# 第一次推論(含 GPU 暖機,會慢)
_ = model(frames[0], classes=[0], device=config.DEVICE, verbose=False)

# 正式計時
t0 = time.time()
max_people = 0
for f in frames:
    r = model(f, conf=config.CONF_THRES, classes=[0], device=config.DEVICE, verbose=False)[0]
    max_people = max(max_people, len(r.boxes))
dt = time.time() - t0
fps = len(frames) / dt

# 存最後一張標註圖
last = model(frames[-1], conf=config.CONF_THRES, classes=[0], device=config.DEVICE, verbose=False)[0]
cv2.imwrite("snapshots/detect_result.jpg", last.plot())

print(f"\n=== 結果 ===")
print(f"GPU 推論速度: {fps:.1f} FPS  (每張 {1000/fps:.1f} ms)")
print(f"這段期間畫面中最多偵測到 {len(last.boxes)} / 峰值 {max_people} 人")
print(f"標註圖已存 snapshots/detect_result.jpg")
