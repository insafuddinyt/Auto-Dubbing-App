"""
কোলাবের ভেতরে চলা সার্ভার (FastAPI)। নোটবুক এটাকে চালু করে।

সুরক্ষা:
  - প্রতিটা রিকোয়েস্টে গোপন key লাগে (header: X-Key)। key নোটবুক প্রতিবার নতুন বানায়।
  - CORS এ শুধু আপনার সাইটের ডোমেইন অনুমতি পায় (SITE_ORIGIN)।
  - ইউজারের পাঠানো কোড কখনো চালানো হয় না, শুধু ফাইল (txt, mp3) নেওয়া হয়।
"""
import hmac
import os
import queue
import shutil
import tempfile
import threading
import time
import uuid

from fastapi import FastAPI, File, Form, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

import process as engine

KEY = os.environ.get("DUB_KEY", "")
SITE_ORIGIN = os.environ.get("SITE_ORIGIN", "").rstrip("/")
MAX_UPLOAD_MB = int(os.environ.get("MAX_UPLOAD_MB", "90"))  # Cloudflare ফ্রি টানেলের ১০০MB সীমার নিচে
WORK_DIR = os.environ.get("DUB_WORK_DIR") or tempfile.mkdtemp(prefix="dub_")
VERSION = os.environ.get("ENGINE_VERSION", "dev")

STOP = threading.Event()          # Disconnect চাপলে এটা সেট হয়, নোটবুক সেশন বন্ধ করে
JOBS = {}                         # id -> dict
_Q = queue.Queue()
_LOCK = threading.Lock()

app = FastAPI(title="Dubbing Engine", docs_url=None, redoc_url=None, openapi_url=None)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[SITE_ORIGIN] if SITE_ORIGIN else [],
    allow_methods=["GET", "POST", "DELETE"],
    allow_headers=["X-Key", "Content-Type"],
    max_age=600,
)


def _auth(x_key):
    if not KEY or not x_key or not hmac.compare_digest(x_key, KEY):
        raise HTTPException(status_code=401, detail="key মেলেনি")


def _save_upload(up: UploadFile, dest: str):
    limit = MAX_UPLOAD_MB * 1024 * 1024
    size = 0
    with open(dest, "wb") as f:
        while True:
            chunk = up.file.read(1024 * 1024)
            if not chunk:
                break
            size += len(chunk)
            if size > limit:
                f.close()
                os.remove(dest)
                raise HTTPException(status_code=413, detail=f"ফাইল {MAX_UPLOAD_MB}MB এর বেশি বড়")
            f.write(chunk)
    if size == 0:
        raise HTTPException(status_code=400, detail="ফাইল ফাঁকা")


def _worker():
    while True:
        jid = _Q.get()
        job = JOBS.get(jid)
        if not job:
            continue

        def progress(pct, msg, job=job):
            job["progress"], job["message"] = int(pct), msg

        job["status"] = "running"
        try:
            engine.process(job["text"], job["music"], job["out"], job["options"], progress)
            job["status"], job["progress"], job["message"] = "done", 100, "শেষ"
        except engine.DubError as e:
            job["status"], job["error"] = "error", str(e)
        except Exception as e:  # noqa: BLE001
            job["status"], job["error"] = "error", f"অপ্রত্যাশিত সমস্যা: {e}"
        finally:
            job["updated"] = time.time()


threading.Thread(target=_worker, daemon=True).start()


def _cleanup_old(max_age=3 * 3600):
    now = time.time()
    for jid, j in list(JOBS.items()):
        if j["status"] in ("done", "error") and now - j.get("updated", now) > max_age:
            shutil.rmtree(j["dir"], ignore_errors=True)
            JOBS.pop(jid, None)


@app.get("/health")
def health():
    busy = any(j["status"] in ("queued", "running") for j in JOBS.values())
    return {"ok": True, "busy": busy, "version": VERSION}


@app.post("/jobs")
def create_job(
    text: UploadFile = File(...),
    music: UploadFile = File(...),
    voice: str = Form(default=""),
    music_db: str = Form(default="-14"),
    rate: str = Form(default="+0%"),
    x_key: str = Header(default=None),
):
    _auth(x_key)
    _cleanup_old()
    if voice and voice not in engine.VOICES:
        raise HTTPException(status_code=400, detail="অজানা ভয়েস")
    if not (rate.startswith(("+", "-")) and rate.endswith("%") and rate[1:-1].isdigit()):
        rate = "+0%"

    jid = uuid.uuid4().hex[:12]
    d = os.path.join(WORK_DIR, jid)
    os.makedirs(d, exist_ok=True)
    try:
        t, m, out = os.path.join(d, "bangla.txt"), os.path.join(d, "music.mp3"), os.path.join(d, "final_audio.mp3")
        _save_upload(text, t)
        _save_upload(music, m)
    except HTTPException:
        shutil.rmtree(d, ignore_errors=True)
        raise

    JOBS[jid] = {
        "id": jid, "dir": d, "text": t, "music": m, "out": out,
        "options": {"voice": voice or None, "music_db": music_db, "rate": rate},
        "status": "queued", "progress": 0, "message": "লাইনে আছে", "error": None,
        "updated": time.time(),
    }
    _Q.put(jid)
    return {"id": jid}


@app.get("/jobs/{jid}")
def job_status(jid: str, x_key: str = Header(default=None)):
    _auth(x_key)
    j = JOBS.get(jid)
    if not j:
        raise HTTPException(status_code=404, detail="কাজ পাওয়া যায়নি")
    return {k: j[k] for k in ("id", "status", "progress", "message", "error")}


@app.get("/jobs/{jid}/result")
def job_result(jid: str, x_key: str = Header(default=None)):
    _auth(x_key)
    j = JOBS.get(jid)
    if not j or j["status"] != "done" or not os.path.exists(j["out"]):
        raise HTTPException(status_code=404, detail="রেজাল্ট এখনো তৈরি হয়নি")
    return FileResponse(j["out"], media_type="audio/mpeg", filename="final_audio.mp3")


@app.get("/voices")
def voices(x_key: str = Header(default=None)):
    _auth(x_key)
    return {"default": engine.DEFAULT_VOICE, "voices": engine.VOICES}


@app.post("/shutdown")
def shutdown(x_key: str = Header(default=None)):
    _auth(x_key)
    STOP.set()
    return {"ok": True}
