# -*- coding: utf-8 -*-
"""手機推播模組。支援 ntfy(零帳號最簡單)與 Telegram。"""
import requests, config, threading

def siren():
    """在監控電腦上播放大聲警報音(Windows)。"""
    if not getattr(config, "LOCAL_SIREN", False):
        return
    def _play():
        try:
            import winsound, os
            wav = getattr(config, "SIREN_WAV", "")
            reps = getattr(config, "SIREN_REPEAT", 3)
            if wav and os.path.exists(wav):
                for _ in range(reps):
                    winsound.PlaySound(wav, winsound.SND_FILENAME)   # 走音效卡->喇叭
            else:
                for _ in range(reps):
                    winsound.Beep(1100, 350); winsound.Beep(700, 350)
        except Exception as e:
            print("[警報音失敗]", e)
    threading.Thread(target=_play, daemon=True).start()

def _ascii_tags():
    raw = getattr(config, "NTFY_SOUND_TAGS", "warning")
    if isinstance(raw, bytes):
        raw = raw.decode("utf-8", "ignore")
    tags = [t.strip() for t in raw.split(",") if t.strip().isascii() and t.strip()]
    return ",".join(tags) or "warning"

def _check(r, label):
    if r is not None and r.status_code != 200:
        print(f"[ntfy {label} 失敗] HTTP {r.status_code} {r.text[:120]}")
        return False
    return True

def _send_ntfy(title, message, snapshot=None, priority=None):
    priority = priority or getattr(config, "NTFY_PRIORITY", "max")
    url = f"https://ntfy.sh/{config.NTFY_TOPIC}"
    headers = {                       # Title 用 UTF-8 bytes(ntfy 接受);Tags 一定要 ASCII
        "Title": title.encode("utf-8"),
        "Priority": str(priority),
        "Tags": _ascii_tags(),
    }
    try:
        ok = True
        if snapshot:
            with open(snapshot, "rb") as f:
                h2 = dict(headers); h2["Filename"] = "snap.jpg"
                r = requests.put(url, data=f, headers=h2, timeout=15)
                ok &= _check(r, "附圖")
            r = requests.post(url, data=message.encode("utf-8"),
                              headers={"Title": title.encode("utf-8"),
                                       "Priority": str(priority), "Tags": _ascii_tags()}, timeout=10)
            ok &= _check(r, "訊息")
        else:
            r = requests.post(url, data=message.encode("utf-8"), headers=headers, timeout=10)
            ok &= _check(r, "訊息")
        return ok
    except Exception as e:
        print(f"[ntfy 推播失敗] {e}")
        return False

def _send_telegram(title, message, snapshot=None):
    base = f"https://api.telegram.org/bot{config.TELEGRAM_TOKEN}"
    text = f"*{title}*\n{message}"
    try:
        if snapshot:
            with open(snapshot, "rb") as f:
                requests.post(f"{base}/sendPhoto",
                              data={"chat_id": config.TELEGRAM_CHAT_ID, "caption": text, "parse_mode": "Markdown"},
                              files={"photo": f}, timeout=10)
        else:
            requests.post(f"{base}/sendMessage",
                          data={"chat_id": config.TELEGRAM_CHAT_ID, "text": text, "parse_mode": "Markdown"}, timeout=10)
        return True
    except Exception as e:
        print(f"[Telegram 推播失敗] {e}")
        return False

def _upload_image(path):
    """上傳圖片取得公開 https 網址(LINE 傳圖必須)。用 catbox 免費圖床。"""
    try:
        with open(path, "rb") as f:
            r = requests.post("https://catbox.moe/user/api.php",
                              data={"reqtype": "fileupload"},
                              files={"fileToUpload": f}, timeout=25)
        if r.status_code == 200 and r.text.startswith("http"):
            return r.text.strip().replace("http://", "https://")
    except Exception as e:
        print("[圖片上傳失敗]", e)
    return None

def _send_line(title, message, snapshot=None):
    """LINE Messaging API 推播到群組/個人,可附現場照片。"""
    msgs = [{"type": "text", "text": f"{title}\n{message}"}]
    if snapshot:
        url = _upload_image(snapshot)
        if url:
            msgs.append({"type": "image", "originalContentUrl": url, "previewImageUrl": url})
    try:
        r = requests.post("https://api.line.me/v2/bot/message/push",
            headers={"Authorization": f"Bearer {config.LINE_TOKEN}",
                     "Content-Type": "application/json"},
            json={"to": config.LINE_TARGET_ID, "messages": msgs}, timeout=20)
        if r.status_code != 200:
            print("[LINE 失敗]", r.status_code, r.text[:150]); return False
        return True
    except Exception as e:
        print("[LINE 失敗]", e); return False

def notify(title, message, snapshot=None, alarm=True, important=None):
    """同時發到所有已設定管道(ntfy + LINE + Telegram)。
    important 預設跟 alarm 一樣(警報級=重要);LINE 可只收重要的。"""
    if alarm:
        siren()
    important = alarm if important is None else important
    sent = False
    if getattr(config, "NTFY_TOPIC", ""):
        sent |= _send_ntfy(title, message, snapshot)
    if getattr(config, "LINE_TOKEN", "") and getattr(config, "LINE_TARGET_ID", ""):
        if important or not getattr(config, "LINE_ONLY_IMPORTANT", True):
            sent |= _send_line(title, message, snapshot)
    if getattr(config, "TELEGRAM_TOKEN", ""):
        sent |= _send_telegram(title, message, snapshot)
    if not sent:
        print(f"[推播未送出] {title}: {message}")
    return sent

if __name__ == "__main__":
    # 測試推播
    ok = notify("CCTV AI 測試", "如果手機收到這則,推播就設定成功了!")
    print("推播結果:", "成功" if ok else "失敗")
