# -*- coding: utf-8 -*-
"""工地多路 AI 監控:人員闖入 + 安全帽(PPE)+ 自動蒐集畫面 + 手機推播。

設計重點:
- CH3/4/6 各開一條執行緒拉流,共用 GPU 模型(有鎖)。
- 偵測到人 -> 自動存畫面到 dataset/raw(供日後驗證/微調安全帽模型)。
- 危險區域(config.DANGER_ZONES)有設就只判斷區域內;沒設算整張。
- NO-Hardhat -> 安全帽違規;有人 -> 闖入。兩者都記錄 CSV + 推播(有冷卻)。
"""
import os
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2, time, csv, datetime, threading, json
from pathlib import Path
import numpy as np
from ultralytics import YOLO
import config, notifier, gsheet

VIOLATION_LOG = Path("logs/violations.csv")
Path(config.AUTO_CAPTURE_DIR).mkdir(parents=True, exist_ok=True)

def load_zones():
    """合併 config.DANGER_ZONES 與 zones.json(後者優先)。"""
    z = {}
    for k, v in config.DANGER_ZONES.items():
        z[int(k)] = v
    try:
        if os.path.exists(config.ZONE_FILE):
            j = json.load(open(config.ZONE_FILE, encoding="utf-8"))
            for k, v in j.items():
                z[int(k)] = v
    except Exception as e:
        print("[zones 載入失敗]", e)
    return z
ZONES = load_zones()

# 共用模型 + 推論鎖(多執行緒安全)
print("載入模型...")
person_model = YOLO(config.MODEL_PATH)          # COCO,用 class 0 = person
helmet_model = YOLO(config.HELMET_MODEL) if config.PPE_ENABLE else None
infer_lock = threading.Lock()
log_lock = threading.Lock()

def now_str():
    return datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

class DomeManager:
    """序列化球機使用:偵測到人 -> 轉去該區 + 拉近拍 close-up + 跑 PPE + 推播 -> 回 home。
    全域上鎖,一次只服務一個請求;忙碌或冷卻中就略過。"""
    def __init__(self):
        self.lock = threading.Lock()
        self.busy = False
        self.last_verify = 0.0
        self.presets = {}
        self.dome = None
        if config.DOME_VERIFY:
            try:
                self.presets = json.load(open(config.PRESET_FILE, encoding="utf-8"))
                from ptz import Dome
                self.dome = Dome()
                print("球機驗證已啟用,預設點:", self.presets)
            except Exception as e:
                print(f"[球機驗證停用] 找不到預設點或連線失敗: {e}")
                print("  -> 請先跑 ptz_setup.py 設定 site_ch3/4/6 + home")

    def request(self, channel):
        if not self.dome:
            return
        name = f"site_ch{channel}"
        if name not in self.presets:
            return
        now = time.time()
        if self.busy or (now - self.last_verify) < config.DOME_VERIFY_COOLDOWN:
            return
        threading.Thread(target=self._verify, args=(channel, name), daemon=True).start()

    def _verify(self, channel, name):
        with self.lock:
            self.busy = True
            self.last_verify = time.time()
            try:
                self.dome.goto_preset(self.presets[name], wait=config.DOME_SETTLE)
                # 從 D1(c1)主碼流抓 close-up
                cap = cv2.VideoCapture(config.rtsp_url(1, 0), cv2.CAP_FFMPEG)
                frame = None; t0 = time.time(); n = 0
                while time.time() - t0 < 8:
                    ok, f = cap.read(); n += 1
                    if ok and f is not None and float(f.std()) > 15:
                        frame = f
                        if n > 40: break
                cap.release()
                if frame is None:
                    return
                # close-up 上工人較大,PPE 較準
                pr = person_model(frame, conf=config.CONF_THRES, classes=[0],
                                  device=config.DEVICE, verbose=False)[0]
                ann = pr.plot()
                no_h = 0
                if config.PPE_ENABLE:
                    hr = helmet_model(frame, conf=config.PPE_CONF, device=config.DEVICE, verbose=False)[0]
                    for b in hr.boxes:
                        nm = helmet_model.names[int(b.cls)]
                        x1,y1,x2,y2 = map(int, b.xyxy[0])
                        if nm == "NO-Hardhat":
                            no_h += 1
                            cv2.rectangle(ann,(x1,y1),(x2,y2),(0,0,255),2)
                            cv2.putText(ann,"NO-HELMET",(x1,y1-5),cv2.FONT_HERSHEY_SIMPLEX,0.6,(0,0,255),2)
                cv2.putText(ann, f"D1 close-up of CH{channel}  {now_str()}", (10,25),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,255,255), 2)
                ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
                snap = f"snapshots/domeverify_ch{channel}_{ts}.jpg"
                cv2.imwrite(snap, ann)
                detail = f"球機拉近 CH{channel}:{len(pr.boxes)} 人" + (f",{no_h} 人未戴安全帽" if no_h else "")
                log_violation(channel, "球機驗證", len(pr.boxes), detail, snap)
                notifier.notify(f"🔎 球機驗證 CH{channel}", f"{now_str()}\n{detail}", snapshot=snap)
            except Exception as e:
                print(f"[球機驗證錯誤] {e}")
            finally:
                if config.DOME_RETURN_HOME and "home" in self.presets:
                    try: self.dome.goto_preset(self.presets["home"], wait=2.0)
                    except Exception: pass
                self.busy = False

dome_mgr = DomeManager()

def log_violation(channel, vtype, count, detail, snapshot):
    with log_lock:
        new = not VIOLATION_LOG.exists()
        with open(VIOLATION_LOG, "a", newline="", encoding="utf-8-sig") as f:
            w = csv.writer(f)
            if new:
                w.writerow(["時間", "攝影機", "違規類型", "數量", "說明", "截圖"])
            row = [now_str(), f"CH{channel}", vtype, count, detail, snapshot]
            w.writerow(row)
    gsheet.append_async(row)   # 同步到 Google Sheet(非阻塞,失敗不影響)

def point_in_zone(cx, cy, zone):
    if not zone:
        return True
    return cv2.pointPolygonTest(np.array(zone, np.int32), (float(cx), float(cy)), False) >= 0

def helmet_status_zoom(frame, box):
    """對單一個人框裁切放大,再跑安全帽模型。
    回傳 'helmet' / 'no_helmet' / 'unknown'(模型沒把握就 unknown,不誤報)。"""
    H, W = frame.shape[:2]
    x1, y1, x2, y2 = box
    # 往外擴一點 padding,重點放在上半身/頭部
    pw = int((x2 - x1) * 0.3); ph = int((y2 - y1) * 0.3)
    cx1 = max(0, x1 - pw); cy1 = max(0, y1 - ph)
    cx2 = min(W, x2 + pw); cy2 = min(H, y2 + ph)
    crop = frame[cy1:cy2, cx1:cx2]
    if crop.size == 0:
        return "unknown"
    # 放大到至少 PPE_ZOOM_MIN 高
    h = crop.shape[0]
    if h < config.PPE_ZOOM_MIN:
        scale = config.PPE_ZOOM_MIN / h
        crop = cv2.resize(crop, None, fx=scale, fy=scale, interpolation=cv2.INTER_CUBIC)
    with infer_lock:
        hr = helmet_model(crop, conf=config.PPE_CONF, device=config.DEVICE, verbose=False)[0]
    has_helmet = has_no = False
    for b in hr.boxes:
        nm = helmet_model.names[int(b.cls)]
        if nm == "Hardhat": has_helmet = True
        elif nm == "NO-Hardhat": has_no = True
    if has_no and not has_helmet:
        return "no_helmet"
    if has_helmet:
        return "helmet"
    return "unknown"

class CameraWorker(threading.Thread):
    def __init__(self, channel, mode="construction"):
        super().__init__(daemon=True)
        self.channel = channel
        self.mode = mode              # "construction" 或 "track"(月台軌道侵入)
        self.zone = ZONES.get(channel, [])
        self.latest = None            # 最新標註畫面(給主執行緒顯示)
        self.running = True
        self.last_intrusion = 0.0
        self.last_helmet = 0.0
        self.last_capture = 0.0
        self.last_track = 0.0

    def open(self):
        stream = 1 if self.mode == "track" else config.CONSTRUCTION_STREAM
        return cv2.VideoCapture(config.rtsp_url(self.channel, stream), cv2.CAP_FFMPEG)

    def run(self):
        cap = self.open()
        interval = 1.0 / max(1, config.TARGET_FPS)
        last_proc = 0.0
        fails = 0
        while self.running:
            ok, frame = cap.read()
            if not ok or frame is None or float(frame.std()) < 15:
                fails += 1
                if fails > 50:
                    cap.release(); time.sleep(2); cap = self.open(); fails = 0
                continue
            fails = 0
            now = time.time()
            if now - last_proc < interval:
                continue
            last_proc = now
            self.process(frame, now)
        cap.release()

    def track_process(self, frame, now):
        """月台/軌道侵入:人或物的腳底點落入軌道警戒區 → 告警。"""
        annotated = frame.copy()
        if self.zone:
            cv2.polylines(annotated, [np.array(self.zone, np.int32)], True, (0, 0, 255), 2)
        with infer_lock:
            r = person_model(frame, conf=config.CONF_THRES, classes=config.TRACK_CLASSES,
                             device=config.DEVICE, verbose=False)[0]
        intruders = []
        for b in r.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            cls = person_model.names[int(b.cls)]
            cx, cy = (x1 + x2) // 2, y2          # 腳底/底邊中點
            inside = point_in_zone(cx, cy, self.zone)
            col = (0, 0, 255) if inside else (0, 200, 0)
            cv2.rectangle(annotated, (x1, y1), (x2, y2), col, 2)
            if inside:
                intruders.append(cls)
                cv2.putText(annotated, "INTRUSION!", (x1, y1 - 5),
                            cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
        cv2.putText(annotated, f"CH{self.channel} 月台軌道警戒  侵入:{len(intruders)}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(annotated, now_str(), (10, frame.shape[0]-10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        self.latest = annotated

        if intruders and (now - self.last_track) > config.TRACK_ALERT_COOLDOWN:
            if not self.zone:
                return   # 未劃警戒區就不誤報
            snap = self.save_snap(annotated, "trackintr")
            kinds = "、".join(sorted(set(intruders)))
            detail = f"CH{self.channel} 偵測到 {len(intruders)} 個目標({kinds})進入軌道警戒區"
            log_violation(self.channel, "軌道侵入", len(intruders), detail, snap)
            notifier.notify(f"🚨 軌道侵入警戒 (CH{self.channel})", f"{now_str()}\n{detail}", snapshot=snap)
            self.last_track = now

    def process(self, frame, now):
        if self.mode == "track":
            return self.track_process(frame, now)
        annotated = frame.copy()
        # 畫危險區域
        if self.zone:
            cv2.polylines(annotated, [np.array(self.zone, np.int32)], True, (0, 165, 255), 2)

        # --- 人員偵測 ---
        with infer_lock:
            pr = person_model(frame, conf=config.CONF_THRES, classes=[0],
                              device=config.DEVICE, verbose=False)[0]
        people_in_zone = 0
        no_helmet = 0
        for b in pr.boxes:
            x1, y1, x2, y2 = map(int, b.xyxy[0])
            cx, cy = (x1 + x2) // 2, y2          # 用腳底點判斷是否在區域
            inside = point_in_zone(cx, cy, self.zone)
            if not inside:
                cv2.rectangle(annotated, (x1, y1), (x2, y2), (0, 200, 0), 2)
                continue
            people_in_zone += 1

            # --- 安全帽:對這個人裁切放大再測(數位變焦) ---
            status = "off"
            if config.PPE_ENABLE:
                status = helmet_status_zoom(frame, (x1, y1, x2, y2)) if config.PPE_ZOOM else "unknown"

            if status == "no_helmet":
                no_helmet += 1
                col, label = (0, 0, 255), "NO-HELMET!"
            elif status == "helmet":
                col, label = (0, 200, 0), "helmet OK"
            else:
                col, label = (0, 200, 255), "person"   # unknown=黃,不誤報
            cv2.rectangle(annotated, (x1, y1), (x2, y2), col, 2)
            cv2.putText(annotated, label, (x1, y1 - 5),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, col, 2)

        # 疊資訊
        cv2.putText(annotated, f"CH{self.channel}  people:{people_in_zone}  no-helmet:{no_helmet}",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 255), 2)
        cv2.putText(annotated, now_str(), (10, frame.shape[0] - 10),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (200, 200, 200), 1)
        self.latest = annotated

        # --- 自動蒐集工人畫面 ---
        if people_in_zone > 0 and (now - self.last_capture) > config.AUTO_CAPTURE_MIN_GAP:
            ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"{config.AUTO_CAPTURE_DIR}/ch{self.channel}_{ts}.jpg", frame)
            self.last_capture = now

        # --- 闖入告警 ---
        if config.INTRUSION_ALERT and people_in_zone > 0 and (now - self.last_intrusion) > config.ALERT_COOLDOWN:
            snap = self.save_snap(annotated, "intrusion")
            detail = f"CH{self.channel} 工地偵測到 {people_in_zone} 人"
            log_violation(self.channel, "人員闖入", people_in_zone, detail, snap)
            notifier.notify(f"🚧 工地有人 (CH{self.channel})", f"{now_str()}\n{detail}", snapshot=snap)
            self.last_intrusion = now
            dome_mgr.request(self.channel)   # 球機轉去該區拉近驗證

        # --- 安全帽告警 ---
        if no_helmet > 0 and (now - self.last_helmet) > config.ALERT_COOLDOWN:
            snap = self.save_snap(annotated, "nohelmet")
            detail = f"CH{self.channel} 偵測到 {no_helmet} 人未戴安全帽"
            log_violation(self.channel, "未戴安全帽", no_helmet, detail, snap)
            notifier.notify(f"⛑️ 未戴安全帽 (CH{self.channel})", f"{now_str()}\n{detail}", snapshot=snap)
            self.last_helmet = now

    def save_snap(self, frame, tag):
        ts = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
        p = f"snapshots/{tag}_ch{self.channel}_{ts}.jpg"
        cv2.imwrite(p, frame)
        return p

def main():
    workers = [CameraWorker(ch) for ch in config.CONSTRUCTION_CHANNELS]
    for w in workers:
        w.start()
    print(f"監控中:CH{config.CONSTRUCTION_CHANNELS}  (視窗按 q 結束)")
    try:
        while True:
            if config.SHOW_WINDOW:
                for w in workers:
                    if w.latest is not None:
                        cv2.imshow(f"CH{w.channel}", w.latest)
                if cv2.waitKey(30) & 0xFF == ord("q"):
                    break
            else:
                time.sleep(1)
    except KeyboardInterrupt:
        pass
    for w in workers:
        w.running = False
    cv2.destroyAllWindows()
    print("已停止。")

if __name__ == "__main__":
    main()
