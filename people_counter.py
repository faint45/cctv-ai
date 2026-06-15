# -*- coding: utf-8 -*-
"""即時在場人數辨識 + 違規統計 + 手機推播。

流程:RTSP 子碼流 -> YOLO(GPU) -> 數人頭 -> 超過上限就記違規/推播。
之後要加「安全帽/反光背心/危險區域」,在 analyze_frame() 裡擴充即可。
"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time, csv, datetime
from pathlib import Path
from ultralytics import YOLO
import config, notifier

VIOLATION_LOG = Path("logs/violations.csv")

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def log_violation(vtype, count, detail, snapshot):
    new = not VIOLATION_LOG.exists()
    with open(VIOLATION_LOG, "a", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["時間", "違規類型", "人數/數量", "說明", "截圖"])
        w.writerow([now_str(), vtype, count, detail, snapshot])

def save_snapshot(frame, tag):
    ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    path = f"snapshots/{tag}_{ts}.jpg"
    cv2.imwrite(path, frame)
    return path

def open_stream():
    url = config.rtsp_url()
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    return cap

def analyze_frame(model, frame):
    """回傳 (人數, 已標註畫面)。未來在這裡加 PPE / 危險區域判斷。"""
    results = model(frame, conf=config.CONF_THRES, classes=[0],  # class 0 = person
                    device=config.DEVICE, verbose=False)
    r = results[0]
    count = len(r.boxes)
    annotated = r.plot()
    return count, annotated

def main():
    print("載入模型...", config.MODEL_PATH)
    model = YOLO(config.MODEL_PATH)
    print("連線 RTSP...")
    cap = open_stream()

    last_alert = 0.0
    frame_interval = 1.0 / max(1, config.TARGET_FPS)
    last_proc = 0.0
    fail = 0

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            fail += 1
            print(f"讀取失敗 ({fail}),重連中...")
            cap.release(); time.sleep(2); cap = open_stream()
            if fail > 30:
                print("連續失敗過多,結束。"); break
            continue
        fail = 0

        # 控制處理頻率,省 GPU/CPU
        now = time.time()
        if now - last_proc < frame_interval:
            continue
        last_proc = now

        count, annotated = analyze_frame(model, frame)

        # 疊加在場人數
        color = (0, 0, 255) if count > config.MAX_OCCUPANCY else (0, 200, 0)
        cv2.putText(annotated, f"In-frame: {count}  (max {config.MAX_OCCUPANCY})",
                    (15, 40), cv2.FONT_HERSHEY_SIMPLEX, 1.0, color, 2)
        cv2.putText(annotated, now_str(), (15, 75),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 1)

        # 違規判斷:超過上限
        if count > config.MAX_OCCUPANCY and (now - last_alert) > config.ALERT_COOLDOWN:
            snap = save_snapshot(annotated, "occupancy")
            detail = f"在場 {count} 人,超過上限 {config.MAX_OCCUPANCY}"
            log_violation("人數超標", count, detail, snap)
            notifier.notify("⚠️ 人數超標", f"{now_str()}\n{detail}", snapshot=snap)
            print("[違規]", detail, "->", snap)
            last_alert = now

        if config.SHOW_WINDOW:
            cv2.imshow("CCTV AI - people count (q=quit)", annotated)
            if cv2.waitKey(1) & 0xFF == ord("q"):
                break

    cap.release()
    cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
