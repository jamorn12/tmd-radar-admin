"""ทันฝน · ระบบจัดการเรดาร์พิษณุโลก (PHS) — หน้าหลังบ้าน

แนวหน้าตา: แถบหัวกรมท่า + แถบเครื่องมือ (เลือกชั้นข้อมูล + แถบเวลา) แบบเว็บกรมอุตุฯ ญี่ปุ่น
+ การ์ดควบคุมระบบ และกราฟ 48 ชั่วโมง

อ่านข้อมูลจาก repo ข้อมูล (tmd-radar-archive) ผ่าน raw.githubusercontent และ GitHub API เท่านั้น — ไม่ clone repo
Secrets: GITHUB_TOKEN (ไม่บังคับ — ไม่มีก็ดูได้ แต่สวิตช์เปิด/ปิดระบบใช้ไม่ได้ และ API จำกัด 60 ครั้ง/ชม.)
"""
from __future__ import annotations

import io
import time
from datetime import datetime, timedelta, timezone

import altair as alt
import numpy as np
import pandas as pd
import requests
import streamlit as st
from PIL import Image, ImageFilter

st.set_page_config(page_title="ทันฝน · ระบบจัดการเรดาร์", layout="wide", page_icon="📡",
                   initial_sidebar_state="collapsed")

# ------------------------------------------------------------------ ค่าตั้ง
TOKEN = str(st.secrets.get("GITHUB_TOKEN", "")).strip()
OWNER = st.secrets.get("REPO_OWNER", "jamorn12")
REPO = st.secrets.get("REPO_NAME", "tmd-radar-archive")
STATION = "PHS"
RAW = f"https://raw.githubusercontent.com/{OWNER}/{REPO}/main"
API = f"https://api.github.com/repos/{OWNER}/{REPO}"
GH = f"https://github.com/{OWNER}/{REPO}"
WEB = f"https://{OWNER}.github.io/{REPO}/"
TH = timezone(timedelta(hours=7))
RUN_MINUTES = (5, 20, 35, 50)                  # เวลาที่ตัวตั้งเวลาภายนอกยิง (เวลาไทย)
FRAME_STALE_MIN, NOWCAST_STALE_MIN = 45, 60    # เท่ากับเกณฑ์ใน watchdog.py
NAVY, OK, WARN, BAD, CORAL = "#1d4e89", "#1a7f37", "#b35900", "#c0392b", "#ef5b3a"
TH_MON = ["", "ม.ค.", "ก.พ.", "มี.ค.", "เม.ย.", "พ.ค.", "มิ.ย.", "ก.ค.", "ส.ค.", "ก.ย.", "ต.ค.", "พ.ย.", "ธ.ค."]

# ส่ง Authorization เฉพาะเมื่อมี token — "Bearer " ว่างทำให้ GitHub ตอบ 401/404 ทั้งที่ repo เป็น public
HEADERS = {"Accept": "application/vnd.github+json"}
if TOKEN:
    HEADERS["Authorization"] = f"Bearer {TOKEN}"

# ------------------------------------------------------------------ หน้าตา
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@400;600;700&family=IBM+Plex+Mono:wght@500&display=swap');
html,body,[class*="css"],.stMarkdown,button,input,label{{font-family:'Sarabun',sans-serif!important}}
.stApp{{background:#fff}}
header[data-testid="stHeader"]{{display:none}}
.block-container,[data-testid="stMainBlockContainer"]{{padding:0 18px 28px!important;max-width:100%!important}}
[data-testid="stAppViewContainer"] .main,[data-testid="stMain"]{{padding-top:0!important}}
div[data-testid="stSlider"] [data-testid="stSliderThumbValue"]{{display:none}}
.mono{{font-family:'IBM Plex Mono',monospace}}
.topbar{{margin:0 -18px;height:48px;background:{NAVY};color:#fff;display:flex;align-items:center;justify-content:space-between;padding:0 20px}}
.topbar b{{font-size:17px}} .topbar .sub{{opacity:.85;margin-left:10px;padding-left:10px;border-left:1px solid #ffffff55}}
.topbar .r{{font-size:13px;opacity:.9}}
@media (max-width:700px){{.topbar{{height:auto;padding:10px 16px;flex-direction:column;align-items:flex-start;gap:2px}}
  .topbar .sub{{display:block;margin:0;padding:0;border:none;font-size:13px}} .topbar .r{{font-size:11.5px}}}}
.toolbar{{margin:0 -18px 14px;border-bottom:1px solid #d7dde5;background:#f4f6f9;height:6px}}
div[data-testid="stHorizontalBlock"]:has(> div .tb-anchor){{background:#f4f6f9;margin:0 -18px 16px;padding:10px 18px 6px;border-bottom:1px solid #d7dde5}}
h3.sec{{font-size:16px;font-weight:700;border-left:5px solid {NAVY};padding-left:9px;margin:4px 0 10px;color:#222}}
.note{{font-size:12.5px;color:#666}}
table.gv{{border-collapse:collapse;width:100%;font-size:14px}}
table.gv th,table.gv td{{border:1px solid #d7dde5;padding:7px 10px;text-align:left}}
table.gv th{{background:#eef2f7;font-weight:600}}
table.gv.st th{{width:33%}}
table.gv.lg td{{font-family:'IBM Plex Mono',monospace;font-size:13px;text-align:right}}
table.gv.lg td:first-child{{text-align:left}}
.badge{{display:inline-block;padding:7px 14px;border-radius:4px;color:#fff;font-weight:700;font-size:14px;white-space:nowrap}}
.ann{{border:1px solid #f0c27a;background:#fff8ec;padding:11px 13px;font-size:14px;line-height:1.6}}
.ann.ok{{border-color:#b7dfc4;background:#f0faf3}}
.ann a{{color:{NAVY}}}
.links a{{color:{NAVY};margin-right:18px;font-size:14px;text-decoration:none}}
.ctrl{{background:#eef2f7;border-radius:10px;padding:12px 14px;margin-bottom:10px}}
.ctrl b{{font-size:15px}}
.cap{{font-size:13px;color:#555;margin-bottom:5px}}
.cap b{{color:#222}}
div[data-testid="stImage"] img{{border:1px solid #c9d3df}}
/* ปุ่มเลือกชั้นข้อมูล */
div[data-testid="stButtonGroup"] button{{border:2px solid {NAVY}!important;color:{NAVY}!important;border-radius:999px!important;
  background:#fff!important;font-weight:600;margin-right:4px}}
div[data-testid="stButtonGroup"] button[aria-checked="true"],div[data-testid="stButtonGroup"] button[kind$="Active"]{{background:{NAVY}!important;color:#fff!important}}
div[data-testid="stSlider"] [role="slider"]{{background:#fff;border:3px solid {NAVY}}}
.legend span{{margin-right:14px;font-size:12.5px;color:#555}}
.legend i{{display:inline-block;width:10px;height:10px;border-radius:3px;margin-right:5px;vertical-align:-1px}}
</style>
""", unsafe_allow_html=True)


# ------------------------------------------------------------------ ตัวช่วยเวลา
def th_str(dt, date=True, year=False) -> str:
    if dt is None or pd.isna(dt):
        return "—"
    dt = dt.astimezone(TH)
    y = f" {dt.year + 543}" if year else ""
    return f"{dt.day} {TH_MON[dt.month]}{y} {dt:%H:%M} น." if date else f"{dt:%H:%M} น."


def age_min(dt) -> float | None:
    return None if dt is None else (datetime.now(TH) - dt).total_seconds() / 60


def age_str(m: float | None) -> str:
    if m is None:
        return "—"
    t = int(round(m))
    return f"{t} นาที" if t < 60 else f"{t // 60} ชม. {t % 60} นาที"


def next_run() -> datetime:
    n = datetime.now(TH)
    m = next((x for x in RUN_MINUTES if x > n.minute), None)
    return (n.replace(minute=m, second=0, microsecond=0) if m is not None
            else (n + timedelta(hours=1)).replace(minute=RUN_MINUTES[0], second=0, microsecond=0))


# ------------------------------------------------------------------ ดึงข้อมูล (cache สั้น ๆ)
def _get(url, timeout=8, **kw):
    try:
        r = requests.get(url, headers=HEADERS, timeout=timeout, **kw)
        return r if r.status_code == 200 else None
    except Exception:
        return None


@st.cache_data(ttl=60, show_spinner=False)
def load_log() -> pd.DataFrame:
    try:
        df = pd.read_csv(f"{RAW}/data/log/{STATION}_index.csv?t={int(time.time())}")
    except Exception:
        return pd.DataFrame()
    df["t_utc"] = pd.to_datetime(df["timestamp_utc"], utc=True, errors="coerce")
    df = df.dropna(subset=["t_utc"]).sort_values("t_utc").drop_duplicates("t_utc", keep="last")
    return df.reset_index(drop=True)


@st.cache_data(ttl=60, show_spinner=False)
def load_manifest() -> dict | None:
    r = _get(f"{RAW}/docs/nowcast/{STATION}/latest.json?t={int(time.time())}")
    try:
        return r.json() if r else None
    except Exception:
        return None


@st.cache_data(ttl=120, show_spinner=False)
def load_runs() -> list[dict]:
    r = _get(f"{API}/actions/workflows/archive.yml/runs", params={"per_page": 12})
    return r.json().get("workflow_runs", []) if r else []


@st.cache_data(ttl=300, show_spinner=False)
def load_issues(state: str = "open") -> list[dict] | None:
    r = _get(f"{API}/issues", params={"labels": "watchdog", "state": state, "per_page": 3})
    return r.json() if r else None


@st.cache_data(ttl=1800, show_spinner=False)
def load_repo_mb() -> float | None:
    r = _get(API)
    return r.json().get("size", 0) / 1024 if r else None


def get_pipeline_enabled() -> bool | None:
    if not TOKEN:
        return None
    r = _get(f"{API}/actions/variables/PIPELINE_ENABLED", timeout=5)
    return None if r is None else r.json().get("value", "true") == "true"


def set_pipeline_enabled(on: bool) -> bool:
    try:
        r = requests.patch(f"{API}/actions/variables/PIPELINE_ENABLED", headers=HEADERS, timeout=6,
                           json={"name": "PIPELINE_ENABLED", "value": "true" if on else "false"})
        return r.status_code in (200, 204)
    except Exception:
        return False


class _Missing(Exception):
    pass


@st.cache_data(ttl=3600, show_spinner=False)
def _bytes_cached(path: str) -> bytes:
    r = _get(f"{RAW}/{path}", timeout=12)
    if r is None:
        raise _Missing(path)          # ไม่ cache ความล้มเหลว — ไฟล์รอบใหม่อาจยังไม่ขึ้น CDN
    return r.content


def load_bytes(path: str) -> bytes | None:
    try:
        return _bytes_cached(path)
    except _Missing:
        return None


def on_basemap(grid_path: str, size: int = 900) -> bytes | None:
    try:
        return _basemap_cached(grid_path, size)
    except _Missing:
        return None


@st.cache_data(ttl=3600, show_spinner=False)
def _basemap_cached(grid_path: str, size: int = 900) -> bytes:
    """วางกริด 241×241 (obs.png / f+XXX.png) ลงบนแผนที่พื้นหลังของเว็บทันฝน"""
    g, b = _bytes_cached(grid_path), _bytes_cached("docs/base_light.png")
    base = Image.open(io.BytesIO(b)).convert("RGB").resize((size, size), Image.LANCZOS)
    ov = Image.open(io.BytesIO(g)).convert("RGBA").resize((size, size), Image.NEAREST)
    a = np.array(ov)
    a[..., 3] = (a[..., 3] > 0) * 235
    ov = Image.fromarray(a).filter(ImageFilter.GaussianBlur(0.8))
    base.paste(ov, (0, 0), ov)
    out = io.BytesIO()
    base.save(out, "PNG", optimize=True)
    return out.getvalue()


def paths(row) -> dict:
    t = row["t_utc"]
    raw = str(row.get("raw_file", "")).replace("\\", "/").lstrip("/")
    ep = int(t.floor("15min").timestamp())   # โฟลเดอร์ใช้เวลาเต็มช่อง 15 นาที (log มีวินาทีติดมา)
    return dict(raw=raw if raw.startswith("data/") else f"data/{raw}",
                solid=f"data/processed/{STATION}/solid/{t:%Y/%m}/{STATION}_{t:%Y%m%d_%H%M}Z_solid.png",
                obs=f"data/nowcast/{STATION}/{ep}/obs.png",
                fc=lambda lead: f"data/nowcast/{STATION}/{ep}/f+{lead:03d}.png")


# ------------------------------------------------------------------ ประเมินสถานะรวม
def overall(df, man, runs, enabled):
    last_t = df["t_utc"].iloc[-1] if len(df) else None
    nc_t = pd.to_datetime(man["base_time_utc"], utc=True) if man and man.get("base_time_utc") else None
    fa, na = age_min(last_t), age_min(nc_t)
    run = runs[0] if runs else None
    if enabled is False:
        s = (WARN, "ปิดระบบอยู่")
    elif fa is None:
        s = (BAD, "อ่านข้อมูลไม่ได้")
    elif fa > FRAME_STALE_MIN:
        s = (BAD, f"ไม่มีภาพใหม่ {age_str(fa)}")
    elif na is not None and na > NOWCAST_STALE_MIN:
        s = (WARN, "ภาพเข้า แต่พยากรณ์ค้าง")
    elif run and run.get("conclusion") == "failure":
        s = (WARN, "รอบล่าสุดล้มเหลว")
    else:
        s = (OK, "ระบบทำงานปกติ")
    return s, last_t, nc_t, fa, na, run


# ------------------------------------------------------------------ ส่วนประกอบ
def status_table(df, last_t, nc_t, fa, na, run, runs):
    now = datetime.now(TH)
    day = df[df["t_utc"] >= now - timedelta(hours=24)] if len(df) else df
    got = len(day)
    rows = []
    rows.append(("ภาพเรดาร์ล่าสุด", f"{th_str(last_t, year=True)} ({age_str(fa)})",
                 ("ปกติ", OK) if fa is not None and fa <= FRAME_STALE_MIN else ("ค้าง", BAD)))
    rows.append(("ภาพพยากรณ์บนเว็บ", f"{th_str(nc_t, False)} (+15 ถึง +120 นาที)",
                 ("ปกติ", OK) if na is not None and na <= NOWCAST_STALE_MIN else ("ค้าง", BAD)))
    gap = ""
    if len(day) > 1:
        g = day["t_utc"].diff().dt.total_seconds().div(60)
        if g.max() > 20:
            i = g.idxmax()
            gap = f"ขาด {th_str(day.loc[i - 1, 't_utc'], False).replace(' น.', '')}–{th_str(day.loc[i, 't_utc'], False)}"
    rows.append(("ความครบ 24 ชม.", f"{got} / 96 ช่อง",
                 ("ครบ", OK) if got >= 92 else ((gap or "ขาดบางช่อง"), WARN if got >= 70 else BAD)))
    if run:
        c = run.get("conclusion") or run.get("status")
        rt = pd.to_datetime(run["run_started_at"], utc=True)
        dur = (pd.to_datetime(run["updated_at"]) - pd.to_datetime(run["run_started_at"])).total_seconds()
        okn = sum(1 for r in runs if r.get("conclusion") == "success")
        rows.append(("pipeline", f"#{run['run_number']} · {th_str(rt, False)} · {int(dur // 60)} นาที {int(dur % 60)} วินาที",
                     {"success": (f"สำเร็จ {okn}/{len(runs)}", OK), "failure": ("ล้มเหลว", BAD)}.get(c, (str(c), WARN))))
    else:
        rows.append(("pipeline", "อ่าน GitHub API ไม่ได้", ("—", "#888")))
    mb = load_repo_mb()
    rows.append(("ขนาด repo", f"{mb / 1024:.2f} GB · {len(df):,} ภาพ" if mb else f"— · {len(df):,} ภาพ",
                 ("เฝ้าระวัง", WARN) if mb and mb > 1024 else ("ปกติ", OK)))
    iss = load_issues("open")
    rows.append(("watchdog", f"เปิดค้าง {len(iss)} รายการ" if iss else "ไม่มีรายการค้าง",
                 ("แจ้งเตือน", BAD) if iss else ("ปกติ", OK)))
    body = "".join(f'<tr><th>{a}</th><td>{b}</td><td style="color:{c[1]};font-weight:700">{c[0]}</td></tr>' for a, b, c in rows)
    st.markdown(f'<table class="gv st">{body}</table>', unsafe_allow_html=True)


def control_card(enabled):
    with st.container(border=True):
        st.markdown(f'<div style="font-weight:700;font-size:15px;color:{NAVY};margin-bottom:8px">⏻ ควบคุมระบบ</div>',
                    unsafe_allow_html=True)
        c1, c2 = st.columns([3, 1], vertical_alignment="center")
        nr = next_run()
        c1.markdown(f'<div><b style="font-size:15px">เก็บภาพอัตโนมัติ</b><div class="note">ทุก 15 นาที · :05 :20 :35 :50 · '
                    f'รอบถัดไป {nr:%H:%M} น.</div></div>', unsafe_allow_html=True)
        if enabled is None:
            c2.toggle("เปิด", value=True, disabled=True, label_visibility="collapsed")
            st.markdown('<div class="note">ใส่ GITHUB_TOKEN ใน Secrets (สิทธิ์ Variables: Read and write) เพื่อเปิด/ปิดจากหน้านี้</div>',
                        unsafe_allow_html=True)
        else:
            on = c2.toggle("เปิด", value=enabled, label_visibility="collapsed")
            if on != enabled:
                if set_pipeline_enabled(on):
                    st.toast("เปิดระบบแล้ว" if on else "ปิดระบบแล้ว — รอบถัดไปจะข้ามการเก็บภาพ", icon="✅")
                    time.sleep(0.6)
                    st.rerun()
                else:
                    st.error("เปลี่ยนค่าบน GitHub ไม่สำเร็จ — ตรวจสิทธิ์ของ token")
        a, b = st.columns(2)
        a.link_button("เว็บทันฝน", WEB, icon=":material/public:", width="stretch")
        b.link_button("Actions", f"{GH}/actions", icon=":material/account_tree:", width="stretch")
        a.link_button("Issues", f"{GH}/issues", icon=":material/notifications:", width="stretch")
        if b.button("รีเฟรช", icon=":material/refresh:", width="stretch"):
            st.cache_data.clear()
            st.rerun()


def chart_48h(df, height=190):
    end = pd.Timestamp.now(tz="UTC").floor("15min")
    slots = pd.date_range(end - pd.Timedelta(hours=48), end, freq="15min")
    d = df.set_index(df["t_utc"].dt.floor("15min"))
    d = d[~d.index.duplicated(keep="last")].reindex(slots)
    t = pd.DataFrame({"t": slots.tz_convert(TH).tz_localize(None), "echo": d["coverage_pct"].values,
                      "rfi": pd.to_numeric(d["qc_spike_px"], errors="coerce").fillna(0).values,
                      "miss": d["coverage_pct"].isna().values})
    x = alt.X("t:T", title=None, axis=alt.Axis(format="%d %b %H:%M", labelColor="#666", grid=False, tickCount=4))
    area = alt.Chart(t).mark_area(color="#1d8f9a", opacity=.18, line={"color": "#127c86", "strokeWidth": 1.6}).encode(
        x=x, y=alt.Y("echo:Q", title=None, axis=alt.Axis(labelColor="#888", gridColor="#eef1f5", tickCount=3)),
        tooltip=[alt.Tooltip("t:T", title="เวลา", format="%d/%m %H:%M"), alt.Tooltip("echo:Q", title="พื้นที่ echo %", format=".2f")])
    rfi = alt.Chart(t[t["rfi"] > 0]).mark_bar(color="#d98a0e", width=2).encode(
        x=x, y=alt.Y("rfi:Q", title=None, axis=None, scale=alt.Scale(domain=[0, t["rfi"].max() * 5 or 1])),
        tooltip=[alt.Tooltip("t:T", title="เวลา", format="%d/%m %H:%M"), alt.Tooltip("rfi:Q", title="RFI ที่ตัด (px)")])
    miss = alt.Chart(t[t["miss"]]).mark_rule(color=CORAL, opacity=.55, strokeWidth=3).encode(
        x=x, tooltip=[alt.Tooltip("t:T", title="ภาพขาด", format="%d/%m %H:%M")])
    ch = alt.layer(area, rfi, miss).resolve_scale(y="independent").properties(height=height)
    st.altair_chart(ch.configure_view(strokeWidth=0), width="stretch")
    st.markdown(f'<div class="legend"><span><i style="background:#127c86"></i>พื้นที่ echo (%)</span>'
                f'<span><i style="background:#d98a0e"></i>RFI ที่ตัด</span><span><i style="background:{CORAL}"></i>'
                f'ภาพขาด {int(t["miss"].sum())}/{len(t)} ช่อง</span></div>', unsafe_allow_html=True)


def log_table(df, n=8):
    v = df.tail(n).iloc[::-1]
    rows = "".join(
        f'<tr><td>{th_str(r.t_utc, False).replace(" น.", "")}</td><td>{str(r.timestamp_source).replace("ocr-majority", "ocr-maj")}</td>'
        f'<td>{r.coverage_pct:.2f}</td><td>{r.max_dbz}</td><td>{int(r.qc_spike_px or 0) if pd.notna(r.qc_spike_px) else 0}</td>'
        f'<td>{float(r.qc_removed_pct or 0):.2f}</td></tr>' for r in v.itertuples())
    st.markdown('<table class="gv lg"><tr><th>เวลา</th><th>ที่มาเวลา</th><th>echo %</th><th>max dBZ</th><th>RFI px</th><th>QC ตัด %</th></tr>'
                f'{rows}</table>', unsafe_allow_html=True)


def runs_table(runs):
    if not runs:
        st.info("อ่าน GitHub API ไม่ได้ — ใส่ GITHUB_TOKEN ใน Secrets เพื่อลดปัญหา rate limit")
        return
    mark = {"success": ("สำเร็จ", OK), "failure": ("ล้มเหลว", BAD), "cancelled": ("ยกเลิก", "#888")}
    rows = ""
    for r in runs:
        c = mark.get(r.get("conclusion"), ("กำลังรัน", NAVY))
        st_ = pd.to_datetime(r["run_started_at"], utc=True)
        dur = (pd.to_datetime(r["updated_at"]) - pd.to_datetime(r["run_started_at"])).total_seconds() if r.get("conclusion") else None
        ev = {"workflow_dispatch": "ตัวตั้งเวลา", "schedule": "cron สำรอง"}.get(r.get("event"), r.get("event"))
        rows += (f'<tr><td><a href="{r["html_url"]}" target="_blank">#{r["run_number"]}</a></td><td>{th_str(st_)}</td>'
                 f'<td>{"—" if dur is None else f"{int(dur // 60)}:{int(dur % 60):02d}"}</td><td>{ev}</td>'
                 f'<td style="color:{c[1]};font-weight:700">{c[0]}</td></tr>')
    st.markdown('<table class="gv"><tr><th>รอบ</th><th>เริ่ม</th><th>ใช้เวลา</th><th>สั่งโดย</th><th>ผล</th></tr>'
                f'{rows}</table>', unsafe_allow_html=True)


def announcements():
    iss = load_issues("open")
    if iss:
        for i in iss:
            ct = pd.to_datetime(i["created_at"], utc=True)
            st.markdown(f'<div class="ann"><b>{th_str(ct, year=True)}</b> <a href="{i["html_url"]}" target="_blank">'
                        f'#{i["number"]} {i["title"]}</a></div>', unsafe_allow_html=True)
        return
    closed = load_issues("closed") or []
    if closed:
        i = closed[0]
        ct = pd.to_datetime(i.get("closed_at") or i["created_at"], utc=True)
        st.markdown(f'<div class="ann ok">ไม่มีแจ้งเตือนค้าง · ล่าสุด <a href="{i["html_url"]}" target="_blank">#{i["number"]}</a> '
                    f'ปิดแล้วเมื่อ {th_str(ct)}<div class="note">{i["title"]}</div></div>', unsafe_allow_html=True)
    else:
        st.markdown('<div class="ann ok">ไม่มีแจ้งเตือนจาก watchdog</div>', unsafe_allow_html=True)


@st.cache_data(ttl=3600, show_spinner=False)
def square(b: bytes, size: int = 800) -> bytes:
    """ย่อ/ขยายภาพให้อยู่ในกรอบจัตุรัสขนาดเดียวกัน (เติมขอบสีพื้นของภาพ) — ภาพดิบ 800×800 กับ solid 725×757
    จะได้แสดงเท่ากันทุกช่อง"""
    im = Image.open(io.BytesIO(b)).convert("RGB")
    sc = size / max(im.size)
    im = im.resize((round(im.width * sc), round(im.height * sc)), Image.LANCZOS)
    bg = (0, 0, 0) if im.getpixel((2, 2)) == (0, 0, 0) else im.getpixel((2, 2))
    out = Image.new("RGB", (size, size), bg)
    out.paste(im, ((size - im.width) // 2, (size - im.height) // 2))
    buf = io.BytesIO()
    out.save(buf, "PNG", optimize=True)
    return buf.getvalue()


def show_img(b: bytes | None, missing: str):
    if b:
        st.image(square(b), width="stretch")
    else:
        st.markdown(f'<div style="aspect-ratio:1/1;border:1px dashed #c9d3df;display:grid;place-items:center;color:#888;'
                    f'font-size:13px;text-align:center;padding:10px">{missing}</div>', unsafe_allow_html=True)


# ================================================================== จัดหน้า
df = load_log()
man, runs = load_manifest(), load_runs()
enabled = get_pipeline_enabled()
state, last_t, nc_t, fa, na, run = overall(df, man, runs, enabled)

st.markdown(f"""<div class="topbar"><div><b>📡 ทันฝน</b><span class="sub">ระบบจัดการเรดาร์พิษณุโลก ({STATION})</span></div>
<div class="r">ข้อมูล ณ {th_str(datetime.now(TH), year=True)} · <span class="mono">{OWNER}/{REPO}</span></div></div>""",
            unsafe_allow_html=True)

# ---- แถบเครื่องมือ: ชั้นข้อมูล · แถบเวลา · สถานะ
LAYERS = {"ภาพดิบ": ":material/image:", "หลัง QC": ":material/grid_view:", "พยากรณ์": ":material/rainy:",
          "คุณภาพ": ":material/monitoring:", "pipeline": ":material/account_tree:"}
tb = st.columns([5.4, 4.4, 1.6], vertical_alignment="center")
with tb[0]:
    st.markdown('<span class="tb-anchor"></span>', unsafe_allow_html=True)
    layer = st.segmented_control("ชั้นข้อมูล", list(LAYERS), default="หลัง QC", label_visibility="collapsed",
                                 format_func=lambda k: f"{LAYERS[k]} {k}") or "หลัง QC"
recent = df.tail(24) if len(df) else df
with tb[1]:
    if len(recent):
        idx = list(recent.index)
        pick = st.select_slider("เวลา", options=idx, value=idx[-1], label_visibility="collapsed",
                                format_func=lambda i: th_str(df.loc[i, "t_utc"], False))
    else:
        pick = None
with tb[2]:
    st.markdown(f'<div style="text-align:right"><span class="badge" style="background:{state[0]}">● {state[1]}</span></div>',
                unsafe_allow_html=True)

left, right = st.columns([1.05, 1], gap="large")

# ---- ซ้าย: ภาพ / คุณภาพ / pipeline
with left:
    if pick is None:
        st.warning("ยังอ่าน log ของระบบไม่ได้")
    elif layer in ("ภาพดิบ", "หลัง QC", "พยากรณ์"):
        row = df.loc[pick]
        p = paths(row)
        st.markdown(f'<h3 class="sec">ภาพเรดาร์ {th_str(row["t_utc"], year=True)}</h3>', unsafe_allow_html=True)
        if layer == "พยากรณ์":
            lead = st.radio("ล่วงหน้า", [30, 60, 120], horizontal=True, format_func=lambda x: f"+{x} นาที",
                            label_visibility="collapsed")
            a, b = st.columns(2, gap="small")
            with a:
                st.markdown('<div class="cap"><b>ภาพจริง ณ เวลานี้</b> (กริดหลัง QC)</div>', unsafe_allow_html=True)
                show_img(on_basemap(p["obs"]), "รอบนี้ไม่มีกริด (ระบบพยากรณ์ไม่ได้รัน)")
            with b:
                st.markdown(f'<div class="cap"><b>พยากรณ์ล่วงหน้า {lead} นาที</b> · ถึงเวลา '
                            f'{th_str(row["t_utc"] + pd.Timedelta(minutes=lead), False)}</div>', unsafe_allow_html=True)
                show_img(on_basemap(p["fc"](lead)), "รอบนี้ไม่มีภาพพยากรณ์")
        else:
            a, b = st.columns(2, gap="small")
            with a:
                st.markdown('<div class="cap"><b>ภาพจากกรมอุตุฯ</b></div>', unsafe_allow_html=True)
                show_img(load_bytes(p["raw"]), f"ไม่พบไฟล์ {p['raw']}")
            with b:
                if layer == "ภาพดิบ":
                    st.markdown('<div class="cap"><b>ภาพ solid</b> (ตัดพื้นหลังแผนที่)</div>', unsafe_allow_html=True)
                    show_img(load_bytes(p["solid"]), "ยังไม่มีภาพ solid")
                else:
                    st.markdown('<div class="cap"><b>หลังแยกชั้นแผนที่และ QC</b> (กริด 2 กม. ที่ใช้พยากรณ์)</div>',
                                unsafe_allow_html=True)
                    grid = on_basemap(p["obs"])
                    show_img(grid or load_bytes(p["solid"]), "ยังไม่มีภาพ")
        az = str(row.get("qc_spike_az", "") or "")
        az = "" if az == "nan" else f" · มุม {az.replace(';', ', ')}°"
        st.markdown(f'<div class="note" style="margin-top:6px">ที่มาเวลา {row["timestamp_source"]} · echo {row["coverage_pct"]:.2f}% · '
                    f'สูงสุด {row["max_dbz"]} dBZ · RFI ตัด {int(row.get("qc_spike_px", 0) or 0):,} px{az} · '
                    f'QC ตัดรวม {float(row.get("qc_removed_pct", 0) or 0):.2f}%</div>', unsafe_allow_html=True)
        st.write("")
        st.markdown('<h3 class="sec">บันทึกรายรอบ</h3>', unsafe_allow_html=True)
        log_table(df)
    elif layer == "คุณภาพ":
        st.markdown('<h3 class="sec">คุณภาพข้อมูล 48 ชั่วโมง</h3>', unsafe_allow_html=True)
        chart_48h(df, height=300)
        st.write("")
        st.markdown('<h3 class="sec">บันทึกรายรอบ</h3>', unsafe_allow_html=True)
        log_table(df, n=16)
    else:
        st.markdown('<h3 class="sec">pipeline 12 รอบหลังสุด</h3>', unsafe_allow_html=True)
        runs_table(runs)

# ---- ขวา: สถานะ · ควบคุม · 48 ชม. · ประกาศ
with right:
    st.markdown('<h3 class="sec">สถานะระบบ</h3>', unsafe_allow_html=True)
    status_table(df, last_t, nc_t, fa, na, run, runs)
    st.write("")
    control_card(enabled)
    if layer != "คุณภาพ":
        with st.container(border=True):
            st.markdown(f'<div style="font-weight:700;font-size:15px;color:{NAVY}">〽 48 ชั่วโมงล่าสุด</div>', unsafe_allow_html=True)
            chart_48h(df)
    st.markdown('<h3 class="sec">ประกาศ</h3>', unsafe_allow_html=True)
    announcements()
    st.markdown(f'<div class="links" style="margin-top:12px"><a href="{WEB}" target="_blank">› เว็บทันฝน</a>'
                f'<a href="{GH}/actions" target="_blank">› GitHub Actions</a><a href="{GH}/issues" target="_blank">› Issues</a>'
                f'<a href="{GH}" target="_blank">› repo ข้อมูล</a></div>', unsafe_allow_html=True)
