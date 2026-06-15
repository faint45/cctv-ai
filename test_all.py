# -*- coding: utf-8 -*-
"""完整功能測試:逐項打 localhost:8080 + 後端鏈路,印出 PASS/FAIL 報告。"""
import requests, time, numpy as np, cv2, json

BASE = "http://localhost:8080"
R = []   # (項目, 結果, 備註)
def rec(name, ok, note=""): R.append((name, ok, note)); print(f"{'PASS' if ok else 'FAIL'}  {name}  {note}")

def grab(ch, timeout=8):
    try:
        r = requests.get(f"{BASE}/video/{ch}", stream=True, timeout=timeout)
        buf=b""; t0=time.time()
        for c in r.iter_content(4096):
            buf+=c; a=buf.find(b"\xff\xd8"); b=buf.find(b"\xff\xd9",a)
            if a!=-1 and b!=-1:
                r.close(); return cv2.imdecode(np.frombuffer(buf[a:b+2],np.uint8),cv2.IMREAD_COLOR)
            if time.time()-t0>timeout: break
        r.close()
    except Exception as e: return None
    return None

print("="*50, "\n A. 網頁端點\n", "="*50)
for path in ["/", "/setup", "/qr.png", "/presets", "/violations", "/monitor/status"]:
    try:
        r = requests.get(BASE+path, timeout=8)
        rec(f"GET {path}", r.status_code==200, f"HTTP {r.status_code}")
    except Exception as e: rec(f"GET {path}", False, str(e))

# QR 是不是有效 PNG
try:
    r=requests.get(BASE+"/qr.png",timeout=8); rec("QR 是 PNG", r.content[:4]==b'\x89PNG', f"{len(r.content)} bytes")
except Exception as e: rec("QR 是 PNG", False, str(e))

print("\n", "="*50, "\n B. 六路即時影像\n", "="*50)
for ch in range(1,7):
    f=grab(ch); ok=f is not None and f.size>0
    rec(f"CH{ch} 影像", ok, f"{f.shape[1]}x{f.shape[0]}" if ok else "無影像")

print("\n", "="*50, "\n C. 球機 PTZ(會實際移動)\n", "="*50)
for act in ["zoomin","zoomout","left","right","up","down"]:
    try:
        r=requests.post(BASE+"/ptz",json={"action":act,"secs":0.5},timeout=10).json()
        rec(f"PTZ {act}", r.get("ok")==True, r.get("err",""))
        time.sleep(0.6)
    except Exception as e: rec(f"PTZ {act}", False, str(e))

print("\n", "="*50, "\n D. 預設點 存/取\n", "="*50)
try:
    r=requests.post(BASE+"/preset/save",json={"name":"_test_tmp"},timeout=10).json()
    rec("存預設點 _test_tmp", r.get("ok")==True)
    r=requests.post(BASE+"/preset/goto",json={"name":"_test_tmp"},timeout=10).json()
    rec("前往預設點 _test_tmp", r.get("ok")==True)
except Exception as e: rec("預設點", False, str(e))

print("\n", "="*50, "\n E. AI 偵測開關\n", "="*50)
try:
    r=requests.post(BASE+"/monitor/start",timeout=10).json(); rec("啟動偵測", r.get("ok")==True)
    time.sleep(3)
    r=requests.get(BASE+"/monitor/status",timeout=8).json(); rec("偵測執行中", r.get("running")==True, f"CH{r.get('channels')}")
    r=requests.post(BASE+"/monitor/stop",timeout=10).json(); rec("停止偵測", r.get("ok")==True)
except Exception as e: rec("偵測開關", False, str(e))

print("\n", "="*50, "\n F. 廣播推播(手機會收到)\n", "="*50)
try:
    r=requests.post(BASE+"/announce",json={"title":"🧪 系統測試","message":"這是完整測試的廣播,收到代表推播正常"},timeout=12).json()
    rec("廣播推播", r.get("ok")==True)
except Exception as e: rec("廣播", False, str(e))

print("\n", "="*50, "\n G. 違規鏈路(CSV+GoogleSheet+推播)\n", "="*50)
try:
    import construction_monitor as cm
    cm.log_violation(3, "測試違規", 1, "完整測試:寫CSV+GoogleSheet", "snapshots/woker_annotated.jpg")
    rec("log_violation(CSV+Sheet)", True, "已寫入(背景送 Sheet)")
    import config
    r=requests.post(config.GSHEET_WEBHOOK_URL, json={"time":"2026-06-12 23:00:00","camera":"CH3","type":"測試違規","count":1,"detail":"完整測試直送","snapshot":""}, timeout=10)
    rec("Google Sheet 直送", r.json().get("ok")==True)
except Exception as e: rec("違規鏈路", False, str(e))

print("\n", "="*50, "\n 總結\n", "="*50)
p=sum(1 for _,ok,_ in R if ok); print(f"通過 {p}/{len(R)}")
for n,ok,note in R:
    if not ok: print("  需檢查:", n, note)
