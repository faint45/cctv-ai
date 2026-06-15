# -*- coding: utf-8 -*-
"""集中設定檔 — 所有參數改這裡就好。"""
from urllib.parse import quote

# ===== NVR / RTSP 連線 =====
NVR_HOST   = "192.168.1.172"   # 從你這台(192.168.1.x)看得到的 NVR 位址
RTSP_PORT  = 554               # UPnP 對外映射的 RTSP 埠(內部其實是 1110)
RTSP_USER  = "admin"           # ← 你的 NVR 帳號
RTSP_PASS  = ""             # ← 填你的 NVR 密碼     # ← 你的 NVR 密碼(填這裡)
CHANNEL    = 1                 # 第幾路攝影機 (1-n)
STREAM     = 1                 # 0=主碼流(高畫質) 1=子碼流(餵 AI 建議用 1)

def rtsp_url(channel=CHANNEL, stream=STREAM):
    user = quote(RTSP_USER, safe="")
    pw   = quote(RTSP_PASS, safe="")
    cred = f"{user}:{pw}@" if RTSP_USER else ""
    return f"rtsp://{cred}{NVR_HOST}:{RTSP_PORT}/unicast/c{channel}/s{stream}/live"

# ===== AI 模型 =====
MODEL_PATH   = "yolov8s.pt"    # n=最快 s=平衡 m=較準(4060Ti 跑 m 也輕鬆)
DEVICE       = 0               # 0 = 用 GPU;"cpu" = 用 CPU
CONF_THRES   = 0.4             # 偵測信心門檻
TARGET_FPS   = 8               # 每秒處理幾張(CCTV 不用太高,省資源)
SHOW_WINDOW  = True            # True=跳出即時畫面視窗

# ===== 即時在場人數 / 違規 =====
MAX_OCCUPANCY = 5              # 在場人數超過此值 → 記一次違規並推播
ALERT_COOLDOWN = 30            # 同類告警最短間隔(秒),避免狂洗推播

# ===== 工地監控(多路) =====
# 要監控的工地攝影機channel(從 survey 得知 CH3/4/6 是工地)
CONSTRUCTION_CHANNELS = [3, 4, 6]

# 危險區域多邊形(影像座標 (x,y) 清單)。空 = 整個畫面都算。
# 之後用 draw_zone.py 在畫面上點選產生座標貼進來。
DANGER_ZONES = {
    3: [],   # 例: [(120,200),(500,200),(500,400),(120,400)]
    4: [],
    6: [],
}

# PPE 偵測
PPE_ENABLE   = True
HELMET_MODEL = "helmet_yolov8m.pt"   # 安全帽模型(之後可換成你微調的)
PPE_CONF     = 0.30
CONSTRUCTION_STREAM = 0   # 工地機用主碼流(0)=1080p,PPE 才夠清楚
PPE_ZOOM     = True       # 對每個人裁切放大再測安全帽(數位變焦)
PPE_ZOOM_MIN = 320        # 裁切後放大到至少這麼高(像素)

# 自動蒐集工人畫面(供日後驗證/微調)
AUTO_CAPTURE_DIR = "dataset/raw"     # 偵測到人就把整張存這裡
AUTO_CAPTURE_MIN_GAP = 5             # 同一路最短存檔間隔(秒)

# 工地告警:在場有人就算闖入(可配合上班時段判斷,先全時段)
INTRUSION_ALERT = True

# ===== 月台/軌道侵入警戒(CH2、CH5)=====
TRACK_CHANNELS = [2, 5]        # 月台攝影機:偵測人/物越過月台邊緣進入軌道
ZONE_FILE = "zones.json"       # 各路警戒區多邊形(用 draw_zone.py 劃設)
# 要偵測的物體類別(COCO id):0人,其餘為可能掉落軌道的物件
TRACK_CLASSES = [0, 1, 24, 25, 26, 28, 32, 39]  # 人/腳踏車/背包/傘/手提包/行李箱/球/瓶
TRACK_ALERT_COOLDOWN = 15      # 軌道侵入告警冷卻(秒,要快)

# 球機(D1)自動驗證:固定機偵測到人 -> 球機轉去該區預設點 + 拉近拍 close-up
DOME_VERIFY = True
DOME_SETTLE = 3.0              # 轉到位後等幾秒再拍(等畫面穩定)
DOME_VERIFY_COOLDOWN = 60      # 全域:兩次球機驗證最短間隔(秒)
DOME_RETURN_HOME = True        # 驗證完是否回 home 預設點
PRESET_FILE = "presets.json"   # 由 ptz_setup.py 產生(site_ch3/4/6, home)

# ===== 推播設定(擇一,見 notifier.py) =====
# 方式 A:ntfy(零帳號最簡單)— 手機裝 ntfy App 訂閱這個主題即可
NTFY_TOPIC = "改成你自己獨特的字串"   # ntfy 推播主題   # 工地告警專用,獨特不易被猜
# 方式 B:Telegram(需建 bot)
TELEGRAM_TOKEN   = ""
TELEGRAM_CHAT_ID = ""

# 方式 C:LINE Messaging API(群組推播,免費約200則/月)
LINE_TOKEN      = ""          # ← LINE Channel access token
LINE_TARGET_ID  = ""          # ← LINE 群組ID (C 開頭)   # 工地 LINE 群組
LINE_ONLY_IMPORTANT = True    # True=LINE 只收重要告警(停工/軌道侵入/未戴安全帽/廣播)

NOTIFY_METHOD = "ntfy"         # 主要管道;ntfy/line 會同時發(只要有設定)

# ===== Google Sheet 統計 =====
GSHEET_ENABLE = True
# 部署 Apps Script Web App 後把網址貼這(見 gsheet_appsscript.gs 說明)
GSHEET_WEBHOOK_URL = ""      # ← Apps Script 部署網址
GSHEET_ID = "1IO0COK7lSWmNV2eEYFih3m5nqWQr4NyiKXcmG3M5aos"

# ===== 氣象 / 雨量(中央氣象署 CWA 開放資料)=====
CWA_API_KEY  = ""            # ← CWA 授權碼 opendata.cwa.gov.tw   # CWA 授權碼
SITE_COUNTY  = "臺南市"         # 工地縣市
SITE_TOWN    = "官田區"         # 工地鄉鎮(拔林車站)
RAIN_STATION = "官田"          # 官田自動雨量站(站號 C0X130,臺南市官田區)
SITE_LAT     = 23.205          # 拔林車站約略座標(找最近雨量站用)
SITE_LON     = 120.346

# 雨量告警門檻(mm)
RAIN_10MIN_ALERT = 6           # 10 分鐘雨量 ≥ 此值 → 強降雨告警
RAIN_1HR_ALERT   = 15          # 時雨量 ≥ → 注意
RAIN_1HR_STOP    = 40          # 時雨量 ≥ → 建議停工(對應大雨/豪雨)
RAIN_CHECK_INTERVAL = 600      # 每幾秒查一次雨量

# 風險建議(每日)
ADVISORY_TIME = "07:30"       # 每天幾點幾分發當日施工風險建議
HEAT_ALERT_TEMP = 36          # 高溫熱危害門檻(°C)

# 歷史雨量(CODiS)
HIST_STN_ID   = "C0X130"      # 官田站 CODiS 站號
HIST_STN_TYPE = "auto_C0"     # 自動氣象站(C0/CA 開頭)
HIST_STN_NAME = "官田"
HIST_START    = "2026-04"     # 歷史起始月(民國115年4月)
HIST_BACKFILL_HOUR = 8        # 每天幾點自動補昨日已定版日雨量

# ===== 強制告警(像地震警報那樣大聲) =====
NTFY_PRIORITY = "max"          # max=最高優先,手機會強提示(預設 high)
NTFY_SOUND_TAGS = "rotating_light,warning"   # 只能 ASCII!中文會讓推播失效
LOCAL_SIREN  = True            # 在這台監控電腦播放大聲警報音
SIREN_REPEAT = 4               # 警報音重複幾次
SIREN_WAV    = r"C:\Windows\Media\Alarm01.wav"   # 警報音檔(走音效卡較可靠)
