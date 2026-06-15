/****************************************************************
 * 工地 AI 違規紀錄 -> Google Sheet 接收端 (Apps Script Web App)
 *
 * 安裝步驟:
 * 1. 打開你的試算表 -> 上方選單「擴充功能」->「Apps Script」
 * 2. 把這整段貼進去(覆蓋原本的 myFunction)
 * 3. 上方「部署」->「新增部署作業」-> 類型選「網頁應用程式」
 * 4. 「執行身分」= 我自己;「誰可以存取」= 任何人
 * 5. 按「部署」,授權後會給你一個網址(https://script.google.com/macros/s/.../exec)
 * 6. 把那個網址貼到 config.py 的 GSHEET_WEBHOOK_URL
 ****************************************************************/

function doPost(e) {
  try {
    var data = JSON.parse(e.postData.contents);
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    var kind = data.kind || "violation";
    var t = data.time ? new Date(data.time.replace(/-/g, "/")) : new Date();

    if (kind === "rainfall") {
      var rs = ss.getSheetByName("雨量紀錄");
      if (!rs) {
        rs = ss.insertSheet("雨量紀錄");
        rs.appendRow(["時間", "測站", "目前", "10分(mm)", "時雨量(mm)", "24h(mm)", "告警"]);
        rs.getRange("A1:G1").setFontWeight("bold").setBackground("#0b3d2e").setFontColor("#fff");
      }
      rs.appendRow([t, data.station || "", data.now, data.r10, data.r1h, data.r24h, data.alert || ""]);
    } else if (kind === "advisory") {
      var as = ss.getSheetByName("每日風險建議");
      if (!as) {
        as = ss.insertSheet("每日風險建議");
        as.appendRow(["日期", "高低溫", "降雨機率", "特報", "風險建議"]);
        as.getRange("A1:E1").setFontWeight("bold").setBackground("#5a3a0b").setFontColor("#fff");
      }
      as.appendRow([t, data.temp || "", data.pop || "", data.warn || "", data.advice || ""]);
    } else if (kind === "rainfall_history") {
      buildRainHistory(ss, data.station || "官田", data.rows || []);
    } else {
      var sh = ss.getSheetByName("違規紀錄");
      if (!sh) {
        sh = ss.insertSheet("違規紀錄");
        sh.appendRow(["時間", "攝影機", "違規類型", "數量", "說明", "截圖"]);
        sh.getRange("A1:F1").setFontWeight("bold").setBackground("#1e3a5a").setFontColor("#fff");
      }
      sh.appendRow([t, data.camera || "", data.type || "", data.count || "",
                    data.detail || "", data.snapshot || ""]);
      ensureSummary(ss);
    }
    return ContentService.createTextOutput(JSON.stringify({ok: true}))
           .setMimeType(ContentService.MimeType.JSON);
  } catch (err) {
    return ContentService.createTextOutput(JSON.stringify({ok: false, err: String(err)}))
           .setMimeType(ContentService.MimeType.JSON);
  }
}

// 建立/更新「統計」分頁(用公式自動彙總,不需每次重算)
function ensureSummary(ss) {
  var s = ss.getSheetByName("統計");
  if (s) return;
  s = ss.insertSheet("統計");
  s.getRange("A1").setValue("依類型").setFontWeight("bold");
  s.getRange("A2").setFormula(
    "=QUERY(違規紀錄!C2:C,\"select C, count(C) where C is not null group by C label count(C) '次數'\",0)");
  s.getRange("D1").setValue("依日期").setFontWeight("bold");
  s.getRange("D2").setFormula(
    "=QUERY({ARRAYFORMULA(TEXT(違規紀錄!A2:A,\"yyyy-mm-dd\")),違規紀錄!C2:C}," +
    "\"select Col1, count(Col2) where Col1<>'' group by Col1 label count(Col2) '次數'\",0)");
  s.getRange("G1").setValue("依攝影機").setFontWeight("bold");
  s.getRange("G2").setFormula(
    "=QUERY(違規紀錄!B2:B,\"select B, count(B) where B is not null group by B label count(B) '次數'\",0)");
}

// 歷史日雨量:寫「歷史雨量」分頁 + 月統計 + 長條圖
function buildRainHistory(ss, station, rows) {
  var sh = ss.getSheetByName("歷史雨量");
  if (!sh) sh = ss.insertSheet("歷史雨量");
  sh.clear();
  // 移除舊圖表
  sh.getCharts().forEach(function(c){ sh.removeChart(c); });

  // 日資料(A:B)
  sh.getRange("A1:B1").setValues([["日期", "日雨量(mm)"]]).setFontWeight("bold").setBackground("#0b3d2e").setFontColor("#fff");
  if (rows.length) {
    var vals = rows.map(function(r){ return [r[0], r[1] === "" ? null : r[1]]; });
    sh.getRange(2, 1, vals.length, 2).setValues(vals);
  }

  // 月統計(D:E)
  var monthly = {};
  rows.forEach(function(r){
    if (r[1] === "" || r[1] === null) return;
    var m = String(r[0]).slice(0, 7);
    monthly[m] = (monthly[m] || 0) + Number(r[1]);
  });
  var mkeys = Object.keys(monthly).sort();
  sh.getRange("D1:E1").setValues([["月份", "月雨量(mm)"]]).setFontWeight("bold").setBackground("#1e3a5a").setFontColor("#fff");
  if (mkeys.length) {
    var mvals = mkeys.map(function(k){ return [k, Math.round(monthly[k]*10)/10]; });
    sh.getRange(2, 4, mvals.length, 2).setValues(mvals);
  }
  sh.getRange("G1").setValue("測站:" + station + "  更新:" + new Date());

  // 月雨量長條圖
  if (mkeys.length) {
    var chart = sh.newChart().asColumnChart()
      .addRange(sh.getRange(1, 4, mkeys.length + 1, 2))
      .setPosition(2, 7, 0, 0)
      .setOption("title", station + " 月雨量統計")
      .setOption("legend", {position: "none"})
      .setOption("width", 480).setOption("height", 300)
      .build();
    sh.insertChart(chart);
  }
}

// 測試用:在編輯器按「執行」這個可手動驗證
function testAppend() {
  doPost({postData: {contents: JSON.stringify({
    time: "2026-06-12 09:00:00", camera: "CH3", type: "測試",
    count: 1, detail: "手動測試", snapshot: ""})}});
}
