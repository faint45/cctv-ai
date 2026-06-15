# -*- coding: utf-8 -*-
"""跑 25 秒驗證多路監控不會出錯,並回報每路處理狀況。"""
import config
config.SHOW_WINDOW = False
import time, construction_monitor as cm

workers = [cm.CameraWorker(ch) for ch in config.CONSTRUCTION_CHANNELS]
for w in workers:
    w.start()
print(f"啟動 CH{config.CONSTRUCTION_CHANNELS},跑 25 秒...")
time.sleep(25)
for w in workers:
    w.running = False
time.sleep(1)
for w in workers:
    got = "有畫面" if w.latest is not None else "無畫面"
    print(f"CH{w.channel}: {got}")
print("smoke test 完成,無例外即代表流程正常")
