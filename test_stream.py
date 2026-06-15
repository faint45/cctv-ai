# -*- coding: utf-8 -*-
"""測試 RTSP 串流能不能拉到畫面,並存一張截圖。"""
import os
# 用 TCP 傳輸 RTSP(比 UDP 穩,適合監控)
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time
from urllib.parse import quote
import config

def mask(url):
    if config.RTSP_PASS:
        return url.replace(quote(config.RTSP_PASS, safe=""), "****")
    return url

def try_url(url, label):
    print(f"\n[嘗試] {label}\n  {mask(url)}")
    cap = cv2.VideoCapture(url, cv2.CAP_FFMPEG)
    for _ in range(40):
        ok, frame = cap.read()
        if ok and frame is not None:
            h, w = frame.shape[:2]
            out = f"snapshots/test_c{label}.jpg"
            cv2.imwrite(out, frame)
            print(f"  OK 成功! 解析度 {w}x{h}  已存 {out}")
            cap.release()
            return True
        time.sleep(0.1)
    cap.release()
    print("  X 讀不到畫面")
    return False

if __name__ == "__main__":
    print("=== RTSP 連線測試 ===")
    # 主要候選:子碼流 + 主碼流
    candidates = [
        (config.rtsp_url(config.CHANNEL, 1), "ch%d-sub(s1)" % config.CHANNEL),
        (config.rtsp_url(config.CHANNEL, 0), "ch%d-main(s0)" % config.CHANNEL),
    ]
    ok_any = False
    for url, label in candidates:
        if try_url(url, label):
            ok_any = True
            break
    if not ok_any:
        print("\n全部失敗。檢查:1) config.py 帳密  2) CHANNEL 是否存在  3) 防火牆")
    else:
        print("\n串流 OK,可以進下一步 people_counter.py")
