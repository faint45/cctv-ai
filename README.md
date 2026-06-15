# 工地 CCTV AI 監控系統

火車站旁工地的 AI 視覺監控:人員闖入 + 安全帽偵測 + 球機自動拉近驗證 + 手機推播 + Google Sheet 統計。
跑在本機 RTX 4060 Ti(GPU,YOLO ~92 FPS)。

## 硬體 / 環境
- i5-14500 / RTX 4060 Ti 8GB / 64GB,Python 3.12 / PyTorch CU121 / Ultralytics
- NVR(HS-MN3426)透過 `192.168.1.172` 對外:RTSP 554、HTTP 57134、ONVIF 57134
- 通道:CH1=**D1 球機**,CH2/5=月台,CH3/4/6=工地

## 一鍵啟動(整合控制台)
```powershell
cd D:\cctv-ai
python webpanel.py          # 開 http://localhost:8080
```
面板功能:6 路即時畫面、球機 PTZ 搖桿、預設點存取、AI 偵測開關、違規紀錄、推播 QR。
手機同網段可用「本機IP:8080」連入。

## 首次設定(只需做一次)

### 1. 球機預設點
面板上用搖桿把球機轉到各工地區、拉近,按「存」→ site_ch3 / site_ch4 / site_ch6 / home。
(或跑 `python ptz_setup.py` 用鍵盤設定。)存好寫進 `presets.json`。
> 偵測到工人時,球機會自動 GotoPreset 轉去該區拉近拍 close-up(這時頭夠大,安全帽偵測較準)。

### 2. 手機推播(iOS/安卓通用)
手機裝 **ntfy** App → 訂閱主題 `allen-site-k7x9q2m4v`。
要給別人:開 `http://localhost:8080/setup`,掃 QR 即可。

### 3. Google Sheet 統計
1. 打開試算表 → 擴充功能 → Apps Script
2. 貼上 `gsheet_appsscript.gs` 全部內容
3. 部署 → 網頁應用程式 → 任何人可存取 → 取得網址
4. 網址貼到 `config.py` 的 `GSHEET_WEBHOOK_URL`
5. (選)`python -c "import gsheet; gsheet.sync_csv()"` 回填舊紀錄

## 偵測 / 告警
- **人員闖入**:工地有人 → 推播 + 電腦警報音 + 球機拉近驗證 + 記錄
- **未戴安全帽**:NO-Hardhat → 同上
- 告警強度:ntfy max 優先 + 電腦播 Alarm01.wav(安卓可設鬧鐘級;iOS 受限)
- 違規同時寫入 `logs/violations.csv`、Google Sheet,並在面板顯示

## 主要檔案
| 檔案 | 用途 |
|------|------|
| `config.py` | 所有設定集中處 |
| `webpanel.py` + `panel.html` + `setup.html` | 整合網頁控制台 + QR 設定頁 |
| `construction_monitor.py` | 多路偵測主程式(人員/PPE/球機驗證/推播/統計) |
| `ptz.py` / `ptz_setup.py` | 球機控制模組 / 預設點設定工具 |
| `notifier.py` | ntfy/Telegram 推播 + 電腦警報音 |
| `gsheet.py` / `gsheet_appsscript.gs` | Google Sheet 統計 |
| `stats.py` | 本機違規統計 |

## 調整
全部在 `config.py`:偵測門檻、處理 FPS、危險區域多邊形、告警冷卻、球機驗證冷卻、模型大小等。

## 待優化
- 安全帽模型對「你這個工地角度」可用 `dataset/raw`(自動蒐集的工人畫面)微調以提高準度。
