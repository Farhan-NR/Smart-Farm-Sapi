"""Backend penerima data deteksi sapi (VPS).
Jalankan: uvicorn main:app --host 0.0.0.0 --port 8000
"""
import json, os, sqlite3, uuid
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles

API_KEY = os.getenv("API_KEY", "ganti-dengan-kunci-rahasia")
TG_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
TG_CHAT = os.getenv("TELEGRAM_CHAT_ID", "")
VPS_HOST = os.getenv("VPS_HOST", "10.33.109.63")
DATA_DIR = Path(os.getenv("DATA_DIR", "./data"))
PHOTO_DIR = DATA_DIR / "photos"
PHOTO_DIR.mkdir(parents=True, exist_ok=True)
DB = str(DATA_DIR / "sapi.db")

def db():
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    return con

with db() as c:
    c.execute("""CREATE TABLE IF NOT EXISTS detections(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        ts TEXT, camera TEXT, cow_id TEXT, behavior TEXT,
        confidence REAL, is_anomaly INTEGER, photo TEXT, raw TEXT)""")

app = FastAPI(title="Cow Monitoring API")
app.mount("/photos", StaticFiles(directory=PHOTO_DIR), name="photos")

def auth(x_api_key: str = Header(default="")):
    if x_api_key != API_KEY:
        raise HTTPException(401, "API key salah")

async def send_telegram(text: str, photo_path: Path | None):
    if not (TG_TOKEN and TG_CHAT):
        return
    base = f"https://api.telegram.org/bot{TG_TOKEN}"
    async with httpx.AsyncClient(timeout=20) as cl:
        if photo_path:
            with open(photo_path, "rb") as f:
                await cl.post(f"{base}/sendPhoto", data={"chat_id": TG_CHAT, "caption": text},
                              files={"photo": f})
        else:
            await cl.post(f"{base}/sendMessage", data={"chat_id": TG_CHAT, "text": text})

@app.post("/api/detections", dependencies=[Depends(auth)])
async def receive(data: str = Form(...), photo: UploadFile | None = File(None)):
    """data = string JSON, contoh:
    {"camera":"kandang1","cow_id":"sapi_3","behavior":"berdiri",
     "confidence":0.91,"is_anomaly":false,"timestamp":"2026-09-25T15:11:00"}"""
    try:
        d = json.loads(data)
    except json.JSONDecodeError:
        raise HTTPException(400, "field 'data' bukan JSON valid")

    photo_name, photo_path = None, None
    if photo:
        photo_name = f"{datetime.now():%Y%m%d_%H%M%S}_{uuid.uuid4().hex[:6]}.jpg"
        photo_path = PHOTO_DIR / photo_name
        photo_path.write_bytes(await photo.read())

    anomaly = 1 if d.get("is_anomaly") else 0
    with db() as c:
        cur = c.execute(
            "INSERT INTO detections(ts,camera,cow_id,behavior,confidence,is_anomaly,photo,raw) VALUES(?,?,?,?,?,?,?,?)",
            (d.get("timestamp", datetime.now().isoformat(timespec="seconds")),
             d.get("camera"), d.get("cow_id"), d.get("behavior"),
             d.get("confidence"), anomaly, photo_name, data))
        new_id = cur.lastrowid

    if anomaly:  # hanya anomali yang dikirim ke Telegram
        await send_telegram(
            f"⚠️ Anomali terdeteksi\nKamera: {d.get('camera')}\nSapi: {d.get('cow_id')}\n"
            f"Perilaku: {d.get('behavior')} ({d.get('confidence')})", photo_path)
    return {"ok": True, "id": new_id}

@app.get("/api/detections", dependencies=[Depends(auth)])
def list_detections(limit: int = 50, only_anomaly: bool = False):
    q = "SELECT * FROM detections" + (" WHERE is_anomaly=1" if only_anomaly else "") + " ORDER BY id DESC LIMIT ?"
    with db() as c:
        return [dict(r) for r in c.execute(q, (limit,))]

# ---- Dashboard sederhana (tanpa auth, batasi lewat VPN/firewall) ----
@app.get("/api/public/latest")
def latest():
    with db() as c:
        return [dict(r) for r in c.execute(
            "SELECT id,ts,camera,cow_id,behavior,confidence,is_anomaly,photo FROM detections ORDER BY id DESC LIMIT 30")]

@app.get("/", response_class=HTMLResponse)
def dashboard():
    return f"""<!doctype html><meta charset=utf-8><title>Monitoring Sapi</title>
<style>body{{font-family:sans-serif;margin:16px}}table{{border-collapse:collapse;width:100%}}
td,th{{border:1px solid #ccc;padding:6px}}.a{{background:#ffe0e0}}img{{height:48px}}</style>
<h2>Monitoring Sapi</h2>
<iframe src="http://{VPS_HOST}:8889/cctv" style="width:100%;height:420px;border:0" allow="autoplay"></iframe>
<h3>Log terbaru</h3><table id=t><tr><th>Waktu<th>Kamera<th>Sapi<th>Perilaku<th>Conf<th>Foto</table>
<script>
async function load(){{
 const r=await (await fetch('/api/public/latest')).json();
 const t=document.getElementById('t');
 t.innerHTML='<tr><th>Waktu<th>Kamera<th>Sapi<th>Perilaku<th>Conf<th>Foto';
 r.forEach(x=>t.insertAdjacentHTML('beforeend',
  `<tr class="${{x.is_anomaly?'a':''}}"><td>${{x.ts}}<td>${{x.camera}}<td>${{x.cow_id}}<td>${{x.behavior}}<td>${{x.confidence??''}}<td>${{x.photo?`<a href="/photos/${{x.photo}}"><img src="/photos/${{x.photo}}"></a>`:''}}`));
}}
load();setInterval(load,5000);
</script>"""
