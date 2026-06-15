# -*- coding: utf-8 -*-
"""抓 CH3 即時高畫質畫面,跑人員 + 安全帽偵測,存標註圖。"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time
from ultralytics import YOLO
import config

CH = 3
person_model = YOLO(config.MODEL_PATH)
helmet_model = YOLO(config.HELMET_MODEL)

# 主碼流(s0)高畫質
url = config.rtsp_url(CH, 0)
cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
best = None
t0 = time.time(); n = 0
while time.time() - t0 < 10:
    ok, f = cap.read(); n += 1
    if ok and f is not None and float(f.std()) > 18:
        best = f
        if n > 40:
            break
cap.release()

if best is None:
    print("抓不到畫面"); raise SystemExit
h, w = best.shape[:2]
cv2.imwrite("snapshots/ch3_live.jpg", best)
print(f"抓到 CH3 即時畫面 {w}x{h}")

# 人員
pr = person_model(best, conf=0.3, classes=[0], device=0, verbose=False)[0]
print(f"人員偵測: {len(pr.boxes)} 人")

# 安全帽
hr = helmet_model(best, conf=0.25, device=0, verbose=False)[0]
hc = {}
for b in hr.boxes:
    nm = helmet_model.names[int(b.cls)]
    hc[nm] = hc.get(nm, 0) + 1
print(f"安全帽偵測: {hc if hc else '無'}")

# 合併標註:人員(綠)+ 安全帽結果
ann = best.copy()
for b in pr.boxes:
    x1, y1, x2, y2 = map(int, b.xyxy[0])
    cv2.rectangle(ann, (x1, y1), (x2, y2), (0, 200, 0), 2)
    cv2.putText(ann, "person", (x1, y1-5), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,200,0), 1)
for b in hr.boxes:
    nm = helmet_model.names[int(b.cls)]
    x1, y1, x2, y2 = map(int, b.xyxy[0])
    col = (0,0,255) if nm == "NO-Hardhat" else (255,200,0)
    cv2.rectangle(ann, (x1, y1), (x2, y2), col, 2)
    cv2.putText(ann, nm, (x1, y2+15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)
cv2.imwrite("snapshots/ch3_live_annotated.jpg", ann)
print("標註圖 -> snapshots/ch3_live_annotated.jpg")
