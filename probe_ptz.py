# -*- coding: utf-8 -*-
"""探測 NVR 有沒有可用的 PTZ 控制通道(ONVIF / 常見 CGI)。"""
import requests
from requests.auth import HTTPDigestAuth, HTTPBasicAuth
import config

HOST = config.NVR_HOST          # 192.168.1.172
HTTP = 57134                    # NVR 對外 HTTP
USER, PW = config.RTSP_USER, config.RTSP_PASS

base = f"http://{HOST}:{HTTP}"

# 1) ONVIF device service(最標準)
onvif_paths = ["/onvif/device_service", "/onvif/Device", "/onvif/services"]
print("=== ONVIF ===")
for p in onvif_paths:
    try:
        r = requests.post(base + p, timeout=6,
                          data='<?xml version="1.0"?><s:Envelope xmlns:s="http://www.w3.org/2003/05/soap-envelope"><s:Body><GetSystemDateAndTime xmlns="http://www.onvif.org/ver10/device/wsdl"/></s:Body></s:Envelope>',
                          headers={"Content-Type": "application/soap+xml"})
        print(f"  POST {p} -> HTTP {r.status_code}  len={len(r.text)}  {'ONVIF!' if 'onvif' in r.text.lower() or 'SystemDateAndTime' in r.text else ''}")
    except Exception as e:
        print(f"  POST {p} -> {type(e).__name__}")

# 2) 常見 CGI PTZ 路徑(各廠牌)
print("=== 常見 CGI ===")
cgi_paths = [
    "/cgi-bin/ptz.cgi", "/cgi-bin/hi3510/ptzctrl.cgi", "/PSIA/PTZ/channels/1",
    "/ISAPI/PTZCtrl/channels/1/continuous", "/cgi-bin/ptzctrl.cgi",
    "/cgi-bin/api.cgi", "/web/cgi-bin/hi3510/ptzctrl.cgi", "/cgi-bin/CGIProxy.fcgi",
]
for p in cgi_paths:
    for auth in [None, HTTPDigestAuth(USER, PW), HTTPBasicAuth(USER, PW)]:
        try:
            r = requests.get(base + p, timeout=5, auth=auth)
            if r.status_code != 404:
                print(f"  GET {p} auth={type(auth).__name__ if auth else 'none'} -> HTTP {r.status_code} {r.text[:60]!r}")
                break
        except Exception:
            pass

# 3) 看 NVR 首頁回應,猜廠牌/介面
print("=== NVR 首頁 ===")
try:
    r = requests.get(base, timeout=6)
    print("  HTTP", r.status_code, "len", len(r.text))
    import re
    for kw in ["onvif", "ptz", "hisilicon", "dahua", "hik", "title", "app.js", "main.js", "guard"]:
        if kw.lower() in r.text.lower():
            print("   含關鍵字:", kw)
except Exception as e:
    print("  首頁失敗:", e)
