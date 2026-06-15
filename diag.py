# -*- coding: utf-8 -*-
"""診斷:1) ntfy 實際回應碼  2) winsound 警報音"""
import requests, config

print("=== 1) ntfy 診斷 ===")
url = f"https://ntfy.sh/{config.NTFY_TOPIC}"

# (a) 最乾淨的 ASCII-only 測試
try:
    r = requests.post(url, data="TEST ascii only".encode("utf-8"),
                      headers={"Title": "Test", "Priority": "5", "Tags": "warning"}, timeout=10)
    print(f"(a) ASCII 測試 -> HTTP {r.status_code} {r.text[:120]}")
except Exception as e:
    print("(a) 失敗:", e)

# (b) 中文標題(用 RFC2047 編碼,ntfy 支援)
try:
    r = requests.post(url, data="中文內容測試".encode("utf-8"),
                      headers={"Title": "=?UTF-8?B?5bel5Zyw5ZGK6K2m?=", "Priority": "5",
                               "Tags": "rotating_light,warning"}, timeout=10)
    print(f"(b) 中文標題 -> HTTP {r.status_code} {r.text[:120]}")
except Exception as e:
    print("(b) 失敗:", e)

print("\n=== 2) winsound 警報音 ===")
try:
    import winsound
    print("播放 Beep 中(應該聽到聲音)...")
    winsound.Beep(1000, 600)
    winsound.Beep(700, 600)
    print("Beep 完成,沒有例外")
except Exception as e:
    print("winsound 失敗:", e)

# 備援:播放系統 WAV
try:
    import winsound, os
    wav = r"C:\Windows\Media\Alarm01.wav"
    if os.path.exists(wav):
        print("播放系統警報 WAV:", wav)
        winsound.PlaySound(wav, winsound.SND_FILENAME)
        print("WAV 播放完成")
except Exception as e:
    print("WAV 失敗:", e)
