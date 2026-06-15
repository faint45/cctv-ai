# -*- coding: utf-8 -*-
"""球機互動控制台:看著 D1 即時畫面,用鍵盤把球機轉到各工地區、存成預設點。

操作鍵(把滑鼠點在影像視窗上):
  方向 :  a 左轉   d 右轉   w 上擺   s 下擺
  變焦 :  i 拉近   o 拉遠
  存點 :  3 存「工地CH3」  4 存「工地CH4」  6 存「工地CH6」  0 存「待命home」
  測試 :  g 然後 3/4/6/0  叫球機去該預設點
  q    :  離開
存好的預設點會寫進 presets.json,監控程式會自動讀取使用。
"""
import os, json, time
os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"
import cv2
from ptz import Dome
import config

PRESET_FILE = "presets.json"
AREA_KEYS = {ord('3'): "site_ch3", ord('4'): "site_ch4",
             ord('6'): "site_ch6", ord('0'): "home"}
STEP = 0.6     # 移動速度
BURST = 0.25   # 每次按鍵移動秒數

def load_presets():
    if os.path.exists(PRESET_FILE):
        return json.load(open(PRESET_FILE, encoding="utf-8"))
    return {}

def save_presets(d):
    json.dump(d, open(PRESET_FILE, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def main():
    dome = Dome()
    presets = load_presets()
    cap = cv2.VideoCapture(config.rtsp_url(1, 1), cv2.CAP_FFMPEG)  # D1 子碼流
    goto_mode = False
    msg = ""
    print(__doc__)

    while True:
        ok, frame = cap.read()
        if not ok or frame is None:
            cap.release(); time.sleep(1); cap = cv2.VideoCapture(config.rtsp_url(1,1), cv2.CAP_FFMPEG); continue

        disp = frame.copy()
        cv2.putText(disp, "a/d pan  w/s tilt  i/o zoom | save: 3 4 6 0 | g+key=goto | q quit",
                    (10, 25), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,255), 1)
        saved = ",".join(f"{k}={v}" for k,v in presets.items())
        cv2.putText(disp, "saved: " + (saved or "(none)"), (10, 50),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0,255,0), 1)
        if msg:
            cv2.putText(disp, msg, (10, disp.shape[0]-15),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0,200,255), 2)
        if goto_mode:
            cv2.putText(disp, "GOTO: press 3/4/6/0", (10, 75),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255,150,0), 2)
        cv2.imshow("D1 PTZ Setup", disp)

        k = cv2.waitKey(30) & 0xFF
        if k == 255:
            continue
        if k == ord('q'):
            break

        if goto_mode and k in AREA_KEYS:
            name = AREA_KEYS[k]
            if name in presets:
                dome.goto_preset(presets[name]); msg = f"-> goto {name}"
            else:
                msg = f"{name} 尚未設定"
            goto_mode = False
            continue
        goto_mode = False

        if k == ord('a'): dome.pan_tilt(x=-STEP, secs=BURST); msg="pan left"
        elif k == ord('d'): dome.pan_tilt(x=STEP, secs=BURST); msg="pan right"
        elif k == ord('w'): dome.pan_tilt(y=STEP, secs=BURST); msg="tilt up"
        elif k == ord('s'): dome.pan_tilt(y=-STEP, secs=BURST); msg="tilt down"
        elif k == ord('i'): dome.zoom(z=STEP, secs=BURST); msg="zoom in"
        elif k == ord('o'): dome.zoom(z=-STEP, secs=BURST); msg="zoom out"
        elif k == ord('g'): goto_mode = True
        elif k in AREA_KEYS:
            name = AREA_KEYS[k]
            token = dome.set_preset(name, token=presets.get(name))  # 有就覆蓋
            presets[name] = str(token); save_presets(presets)
            msg = f"已存預設點 {name} (token={token})"
            print(msg)

    cap.release(); cv2.destroyAllWindows()
    print("最終預設點:", presets)

if __name__ == "__main__":
    main()
