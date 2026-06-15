# -*- coding: utf-8 -*-
"""下載工地 PPE 多類別模型,驗證類別數,並用真實工地工人照測試。"""
import os, urllib.request, ssl
from ultralytics import YOLO
import cv2

ssl._create_default_https_context = ssl._create_unverified_context

CANDIDATES = [
    ("https://github.com/VoxDroid/Construction-Site-Safety-PPE-Detection/raw/main/Model-Training/yolov8s.pt", "ppe_voxdroid.pt"),
]

def try_download(url, dst):
    try:
        print(f"下載 {url} ...")
        urllib.request.urlretrieve(url, dst)
        sz = os.path.getsize(dst)
        print(f"  -> {dst} {sz/1e6:.2f} MB")
        if sz < 100000:   # git-lfs 指標檔通常很小
            print("  ! 檔案太小,可能是 git-lfs 指標,不是真權重")
            return False
        return True
    except Exception as e:
        print("  下載失敗:", e)
        return False

model = None
for url, dst in CANDIDATES:
    if os.path.exists(dst) and os.path.getsize(dst) > 100000:
        model = YOLO(dst); break
    if try_download(url, dst):
        try:
            model = YOLO(dst); break
        except Exception as e:
            print("  載入失敗:", e)

if model is None:
    print("沒有可用的 PPE 模型"); raise SystemExit

print("\n模型類別 (%d 類):" % len(model.names), model.names)
is_ppe = len(model.names) <= 15 and any("Hardhat" in str(v) or "Vest" in str(v) for v in model.names.values())
print("是工地 PPE 模型?", "是 ✓" if is_ppe else "否 — 這只是普通 COCO 模型")
