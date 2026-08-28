#pragma once
#include <Arduino.h>
#include <ArduinoJson.h>
#include "ble_bridge.h"
#include "xfer.h"

struct TamaState {
  uint8_t  sessionsTotal;
  uint8_t  sessionsRunning;
  uint8_t  sessionsWaiting;
  bool     recentlyCompleted;
  uint32_t tokensToday;
  uint32_t codexTokens;
  uint8_t  codexPrimary;
  uint8_t  codexSecondary;
  uint8_t  codexTertiary;
  uint32_t codexPrimaryResetsAt;
  uint32_t codexSecondaryResetsAt;
  uint32_t codexTertiaryResetsAt;
  char     codexProviderLabel[16];
  char     codexPrimaryLabel[8];
  char     codexSecondaryLabel[8];
  char     codexTertiaryLabel[8];
  char     codexPrimaryDisplay[8];
  char     codexSecondaryDisplay[8];
  char     codexTertiaryDisplay[8];
  bool     codexShowSecondary;
  uint8_t  codexMeterCount;
  uint8_t  codexProviderIndex;
  uint8_t  codexProviderCount;
  char     codexState[16];
  uint32_t lastUpdated;
  char     msg[24];
  bool     connected;
  char     lines[8][92];
  uint8_t  nLines;
  uint16_t lineGen;          // bumps when lines change — lets UI reset scroll
  char     promptId[40];     // pending permission request ID; empty = no prompt
  char     promptTool[20];
  char     promptHint[44];
};

// ---------------------------------------------------------------------------
// Three modes, checked in priority order:
//   demo   → auto-cycle fake scenarios every 8s, ignore live data
//   live   → JSON arrived in the last 10s over USB or BT
//   asleep → no data, all zeros, "No bridge"
// ---------------------------------------------------------------------------

static uint32_t _lastLiveMs = 0;
static uint32_t _lastBtByteMs = 0;   // hasClient() lies; track actual BT traffic
static bool     _demoMode   = false;
static uint8_t  _demoIdx    = 0;
static uint32_t _demoNext   = 0;
static uint32_t _utcEpochAtSync = 0;
static uint32_t _utcSyncMs = 0;

struct _Fake { const char* n; const char* st; uint8_t t,r,w; bool c; uint32_t tok; uint8_t p,s; };
static const _Fake _FAKES[] = {
  {"asleep","idle",0,0,0,false,0,0,0},
  {"one idle","idle",1,0,0,false,12000,1,16},
  {"busy","busy",4,3,0,false,89000,7,22},
  {"attention","attention",2,1,1,false,45000,42,64},
  {"completed","completed",1,0,0,true,142000,18,72},
};

inline void dataSetDemo(bool on) {
  _demoMode = on;
  if (on) { _demoIdx = 0; _demoNext = millis(); }
}
inline bool dataDemo() { return _demoMode; }

inline bool dataConnected() {
  return _lastLiveMs != 0 && (millis() - _lastLiveMs) <= 30000;
}

inline bool dataBtActive() {
  // Desktop's idle keepalive is ~10s; give it 1.5x headroom.
  return _lastBtByteMs != 0 && (millis() - _lastBtByteMs) <= 15000;
}

inline const char* dataScenarioName() {
  if (_demoMode) return _FAKES[_demoIdx].n;
  if (dataConnected()) return dataBtActive() ? "bt" : "usb";
  return "none";
}

// Set true once the bridge sends a time sync — until then the RTC may
// hold whatever was on the coin cell (or 2000-01-01 if it lost power).
static bool _rtcValid = false;
inline bool dataRtcValid() { return _rtcValid; }

inline void dataSyncUtc(uint32_t epoch) {
  if (epoch == 0) return;
  _utcEpochAtSync = epoch;
  _utcSyncMs = millis();
}

inline bool dataUtcNow(uint32_t* out) {
  if (_utcEpochAtSync == 0) return false;
  *out = _utcEpochAtSync + (uint32_t)((millis() - _utcSyncMs) / 1000);
  return true;
}

static uint8_t _jsonPct(JsonVariant v, uint8_t fallback) {
  if (v.isNull()) return fallback;
  int n = v.as<int>();
  if (n < 0) n = 0;
  if (n > 100) n = 100;
  return (uint8_t)n;
}

static void _applyPrompt(JsonVariant v, TamaState* out, bool clearIfNull) {
  JsonObject pr = v.as<JsonObject>();
  if (!pr.isNull()) {
    const char* pid = pr["id"]; const char* pt = pr["tool"]; const char* ph = pr["hint"];
    strncpy(out->promptId,   pid ? pid : "", sizeof(out->promptId)-1);   out->promptId[sizeof(out->promptId)-1]=0;
    strncpy(out->promptTool, pt  ? pt  : "", sizeof(out->promptTool)-1); out->promptTool[sizeof(out->promptTool)-1]=0;
    strncpy(out->promptHint, ph  ? ph  : "", sizeof(out->promptHint)-1); out->promptHint[sizeof(out->promptHint)-1]=0;
  } else if (clearIfNull) {
    out->promptId[0] = 0; out->promptTool[0] = 0; out->promptHint[0] = 0;
  }
}

static void _applyJson(const char* line, TamaState* out) {
  JsonDocument doc;
  if (deserializeJson(doc, line)) return;
  if (xferCommand(doc)) { _lastLiveMs = millis(); return; }

  // Bridge sends {"time":[epoch_sec, tz_offset_sec]}; gmtime_r on the
  // adjusted epoch yields local components including weekday.
  JsonArray t = doc["time"];
  if (!t.isNull() && t.size() == 2) {
    uint32_t utc = t[0].as<uint32_t>();
    dataSyncUtc(utc);
    time_t local = (time_t)utc + (int32_t)t[1];
    appRtcSynced(local);
    _rtcValid = true;
    _lastLiveMs = millis();
    return;
  }

  if (doc["now"].is<uint32_t>()) dataSyncUtc(doc["now"].as<uint32_t>());

  bool codexPacket = doc["state"].is<const char*>()
                  || doc["primary"].is<int>()
                  || doc["secondary"].is<int>()
                  || doc["primary_resets_at"].is<uint32_t>()
                  || doc["secondary_resets_at"].is<uint32_t>();

  if (codexPacket) {
    const char* st = doc["state"];
    if (!st || !*st) st = out->codexState[0] ? out->codexState : "idle";
    strncpy(out->codexState, st, sizeof(out->codexState) - 1);
    out->codexState[sizeof(out->codexState) - 1] = 0;

    if (doc["tokens"].is<uint32_t>()) {
      out->codexTokens = doc["tokens"].as<uint32_t>();
      out->tokensToday = out->codexTokens;
    }
    out->codexPrimary = _jsonPct(doc["primary"], out->codexPrimary);
    out->codexSecondary = _jsonPct(doc["secondary"], out->codexSecondary);
    out->codexTertiary = _jsonPct(doc["tertiary"], out->codexTertiary);
    out->codexPrimaryResetsAt = doc["primary_resets_at"] | out->codexPrimaryResetsAt;
    out->codexSecondaryResetsAt = doc["secondary_resets_at"] | out->codexSecondaryResetsAt;
    out->codexTertiaryResetsAt = doc["tertiary_resets_at"] | out->codexTertiaryResetsAt;

    const char* prov = doc["provider"];
    const char* lbl = doc["label"];
    if (lbl && *lbl) {
      strncpy(out->codexProviderLabel, lbl, sizeof(out->codexProviderLabel) - 1);
      out->codexProviderLabel[sizeof(out->codexProviderLabel) - 1] = 0;
    } else if (prov && *prov) {
      strncpy(out->codexProviderLabel, prov, sizeof(out->codexProviderLabel) - 1);
      out->codexProviderLabel[sizeof(out->codexProviderLabel) - 1] = 0;
    }
    const char* pl = doc["primary_label"];
    if (pl && *pl) {
      strncpy(out->codexPrimaryLabel, pl, sizeof(out->codexPrimaryLabel) - 1);
      out->codexPrimaryLabel[sizeof(out->codexPrimaryLabel) - 1] = 0;
    }
    const char* sl = doc["secondary_label"];
    if (sl && *sl) {
      strncpy(out->codexSecondaryLabel, sl, sizeof(out->codexSecondaryLabel) - 1);
      out->codexSecondaryLabel[sizeof(out->codexSecondaryLabel) - 1] = 0;
    }
    const char* pdisp = doc["primary_display"];
    if (pdisp && *pdisp) {
      strncpy(out->codexPrimaryDisplay, pdisp, sizeof(out->codexPrimaryDisplay) - 1);
      out->codexPrimaryDisplay[sizeof(out->codexPrimaryDisplay) - 1] = 0;
      // Balance / custom left value: clear right label unless explicitly sent.
      if (!(pl && *pl)) out->codexPrimaryLabel[0] = 0;
    } else {
      out->codexPrimaryDisplay[0] = 0;
    }
    const char* sdisp = doc["secondary_display"];
    if (sdisp && *sdisp) {
      strncpy(out->codexSecondaryDisplay, sdisp, sizeof(out->codexSecondaryDisplay) - 1);
      out->codexSecondaryDisplay[sizeof(out->codexSecondaryDisplay) - 1] = 0;
      if (!(sl && *sl)) out->codexSecondaryLabel[0] = 0;
    } else {
      out->codexSecondaryDisplay[0] = 0;
    }
    if (doc["show_secondary"].is<bool>()) {
      out->codexShowSecondary = doc["show_secondary"].as<bool>();
    } else {
      out->codexShowSecondary = true;
    }
    const char* tl = doc["tertiary_label"];
    if (tl && *tl) {
      strncpy(out->codexTertiaryLabel, tl, sizeof(out->codexTertiaryLabel) - 1);
      out->codexTertiaryLabel[sizeof(out->codexTertiaryLabel) - 1] = 0;
    }
    const char* tdisp = doc["tertiary_display"];
    if (tdisp && *tdisp) {
      strncpy(out->codexTertiaryDisplay, tdisp, sizeof(out->codexTertiaryDisplay) - 1);
      out->codexTertiaryDisplay[sizeof(out->codexTertiaryDisplay) - 1] = 0;
      if (!(tl && *tl)) out->codexTertiaryLabel[0] = 0;
    } else {
      out->codexTertiaryDisplay[0] = 0;
    }
    if (doc["meter_count"].is<uint8_t>() || doc["meter_count"].is<int>()) {
      int meters = doc["meter_count"].as<int>();
      if (meters < 1) meters = 1;
      if (meters > 3) meters = 3;
      out->codexMeterCount = (uint8_t)meters;
    } else if (out->codexTertiaryLabel[0] || doc["tertiary"].is<int>()) {
      out->codexMeterCount = 3;
    } else {
      out->codexMeterCount = out->codexShowSecondary ? 2 : 1;
    }
    if (doc["provider_index"].is<uint8_t>() || doc["provider_index"].is<int>()) {
      int idx = doc["provider_index"].as<int>();
      if (idx < 0) idx = 0;
      if (idx > 255) idx = 255;
      out->codexProviderIndex = (uint8_t)idx;
    }
    if (doc["provider_count"].is<uint8_t>() || doc["provider_count"].is<int>()) {
      int cnt = doc["provider_count"].as<int>();
      if (cnt < 0) cnt = 0;
      if (cnt > 255) cnt = 255;
      out->codexProviderCount = (uint8_t)cnt;
    }

    out->sessionsRunning = strcmp(out->codexState, "busy") == 0 ? 1 : 0;
    out->sessionsWaiting = strcmp(out->codexState, "attention") == 0 ? 1 : 0;
    out->recentlyCompleted = strcmp(out->codexState, "completed") == 0
                           || strcmp(out->codexState, "celebrate") == 0;
    out->sessionsTotal = 1;

    const char* m = doc["message"];
    if (!m) m = doc["msg"];
    if (!m) m = "Usage live";
    strncpy(out->msg, m, sizeof(out->msg) - 1);
    out->msg[sizeof(out->msg) - 1] = 0;

    out->lastUpdated = millis();
    _lastLiveMs = millis();
    return;
  }

  out->sessionsTotal     = doc["total"]     | out->sessionsTotal;
  out->sessionsRunning   = doc["running"]   | out->sessionsRunning;
  out->sessionsWaiting   = doc["waiting"]   | out->sessionsWaiting;
  out->recentlyCompleted = doc["completed"] | false;
  uint32_t bridgeTokens = doc["tokens"] | 0;
  if (doc["tokens"].is<uint32_t>()) statsOnBridgeTokens(bridgeTokens);
  out->tokensToday = doc["tokens_today"] | out->tokensToday;
  const char* m = doc["msg"];
  if (m) { strncpy(out->msg, m, sizeof(out->msg)-1); out->msg[sizeof(out->msg)-1]=0; }
  JsonArray la = doc["entries"];
  if (!la.isNull()) {
    uint8_t n = 0;
    for (JsonVariant v : la) {
      if (n >= 8) break;
      const char* s = v.as<const char*>();
      strncpy(out->lines[n], s ? s : "", 91); out->lines[n][91]=0;
      n++;
    }
    if (n != out->nLines || (n > 0 && strcmp(out->lines[n-1], out->msg) != 0)) {
      out->lineGen++;
    }
    out->nLines = n;
  }
  _applyPrompt(doc["prompt"], out, true);
  out->lastUpdated = millis();
  _lastLiveMs = millis();
}

template<size_t N>
struct _LineBuf {
  char buf[N];
  uint16_t len = 0;
  void feed(Stream& s, TamaState* out) {
    while (s.available()) {
      char c = s.read();
      if (c == '\n' || c == '\r') {
        if (len > 0) { buf[len]=0; if (buf[0]=='{') _applyJson(buf, out); len=0; }
      } else if (len < N-1) {
        buf[len++] = c;
      }
    }
  }
};

static _LineBuf<1024> _usbLine, _btLine;

inline void dataPoll(TamaState* out) {
  uint32_t now = millis();

  if (_demoMode) {
    if (now >= _demoNext) { _demoIdx = (_demoIdx + 1) % 5; _demoNext = now + 8000; }
    const _Fake& s = _FAKES[_demoIdx];
    out->sessionsTotal=s.t; out->sessionsRunning=s.r; out->sessionsWaiting=s.w;
    out->recentlyCompleted=s.c; out->tokensToday=s.tok; out->lastUpdated=now;
    out->codexTokens=s.tok; out->codexPrimary=s.p; out->codexSecondary=s.s;
    if (_utcEpochAtSync == 0) dataSyncUtc(now / 1000);
    uint32_t utcNow = 0;
    if (dataUtcNow(&utcNow)) {
      out->codexPrimaryResetsAt = utcNow + 4 * 3600 + 32 * 60;
      out->codexSecondaryResetsAt = utcNow + 5 * 86400 + 12 * 3600;
    }
    strncpy(out->codexState, s.st, sizeof(out->codexState) - 1);
    out->codexState[sizeof(out->codexState) - 1] = 0;
    out->connected = true;
    snprintf(out->msg, sizeof(out->msg), "demo: %s", s.n);
    return;
  }

  _usbLine.feed(Serial, out);
  // BLE ring buffer is drained manually since it's not a Stream.
  while (bleAvailable()) {
    int c = bleRead();
    if (c < 0) break;
    _lastBtByteMs = millis();
    if (c == '\n' || c == '\r') {
      if (_btLine.len > 0) {
        _btLine.buf[_btLine.len] = 0;
        if (_btLine.buf[0] == '{') _applyJson(_btLine.buf, out);
        _btLine.len = 0;
      }
    } else if (_btLine.len < sizeof(_btLine.buf) - 1) {
      _btLine.buf[_btLine.len++] = (char)c;
    }
  }

  out->connected = dataConnected();
  if (!out->connected) {
    out->sessionsTotal=0; out->sessionsRunning=0; out->sessionsWaiting=0;
    out->recentlyCompleted=false; out->lastUpdated=now;
    strncpy(out->msg, "No bridge", sizeof(out->msg)-1);
    out->msg[sizeof(out->msg)-1]=0;
    // Clear stale LIVE meters so WAIT shows empty 3-row placeholders.
    out->codexPrimary = 0;
    out->codexSecondary = 0;
    out->codexTertiary = 0;
    out->codexPrimaryResetsAt = 0;
    out->codexSecondaryResetsAt = 0;
    out->codexTertiaryResetsAt = 0;
    out->codexPrimaryLabel[0] = 0;
    out->codexSecondaryLabel[0] = 0;
    out->codexTertiaryLabel[0] = 0;
    out->codexPrimaryDisplay[0] = 0;
    out->codexSecondaryDisplay[0] = 0;
    out->codexTertiaryDisplay[0] = 0;
    out->codexMeterCount = 3;
    out->codexShowSecondary = true;
  }
}
