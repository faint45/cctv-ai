# -*- coding: utf-8 -*-
"""透過正在跑的面板(localhost:8080)診斷 PTZ+影像:抓圖->移動->再抓圖->比對。"""
import requests, time, numpy as np, cv2

BASE = "http://localhost:8080"

def grab_mjpeg_frame(ch, timeout=8):
    """從 MJPEG 串流抓一張 JPEG。"""
    r = requests.get(f"{BASE}/video/{ch}", stream=True, timeout=timeout)
    buf = b""
    t0 = time.time()
    for chunk in r.iter_content(4096):
        buf += chunk
        a = buf.find(b"\xff\xd8")  # JPEG start
        b = buf.find(b"\xff\xd9", a)  # JPEG end
        if a != -1 and b != -1:
            jpg = buf[a:b+2]
            r.close()
            arr = cv2.imdecode(np.frombuffer(jpg, np.uint8), cv2.IMREAD_COLOR)
            return arr
        if time.time() - t0 > timeout:
            break
    r.close()
    return None

print("1) 抓移動前 CH1...")
before = grab_mjpeg_frame(1)
print("   before:", None if before is None else before.shape)

print("2) 透過面板送大幅度移動(拉近 2.5 秒)...")
r = requests.post(f"{BASE}/ptz", json={"action": "zoomin", "secs": 2.5}, timeout=15)
print("   /ptz 回應:", r.json())
time.sleep(3)   # 等串流刷新

print("3) 抓移動後 CH1...")
after = grab_mjpeg_frame(1)

if before is not None and after is not None:
    d = float(np.mean(cv2.absdiff(cv2.resize(before,(320,180)), cv2.resize(after,(320,180)))))
    cv2.imwrite("snapshots/panel_before.jpg", before)
    cv2.imwrite("snapshots/panel_after.jpg", after)
    print(f"\n畫面差異: {d:.1f}")
    if d > 8:
        print("=> 面板影像有更新、球機有動。問題只是『按鍵幅度小/看不出來』")
    else:
        print("=> 面板影像幾乎沒變。可能 a)影像串流沒刷新 b)球機沒收到")
else:
    print("抓不到面板影像 — 伺服器可能沒在跑或串流有問題")
