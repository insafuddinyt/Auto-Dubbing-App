"""
ডাবিং ইঞ্জিন (এই ফাইলটাই আপনার "আসল কোড" বসানোর জায়গা)।

server.py শুধু process() ফাংশনটা ডাকে। আপনার নিজের ডাবিং কোড চাইলে
শুধু synthesize() ফাংশনটা বদলে দিন। বাকি সব (টেক্সট ভাগ করা, জোড়া লাগানো,
মিউজিকের সাথে মিক্স) যেমন আছে তেমন থাকবে।

ইনপুট : bangla.txt (বাংলা অনুবাদ/স্ক্রিপ্ট) + music.mp3
আউটপুট: final_audio.mp3
"""
import asyncio
import json
import os
import re
import subprocess
import tempfile

# ---------------------------------------------------------------------------
# সেটিংস
# ---------------------------------------------------------------------------
DEFAULT_VOICE = "bn-BD-NabanitaNeural"
VOICES = {
    "bn-BD-NabanitaNeural": "নবনীতা (বাংলাদেশ, মহিলা)",
    "bn-BD-PradeepNeural": "প্রদীপ (বাংলাদেশ, পুরুষ)",
    "bn-IN-TanishaaNeural": "তানিশা (ভারত, মহিলা)",
    "bn-IN-BashkarNeural": "ভাস্কর (ভারত, পুরুষ)",
}
MAX_CHUNK_CHARS = 900   # একবারে এর বেশি অক্ষর TTS এ পাঠানো হবে না
TAIL_SECONDS = 3        # ভয়েস শেষের পর মিউজিক আরও কতক্ষণ বাজবে


class DubError(Exception):
    """ইউজারকে দেখানোর মতো পরিষ্কার এরর।"""


# ---------------------------------------------------------------------------
# ধাপ ১: টেক্সটকে ছোট ছোট অংশে ভাগ করা
# ---------------------------------------------------------------------------
def split_text(text, limit=MAX_CHUNK_CHARS):
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    # বাক্যের শেষে (। . ? ! ॥ নতুন লাইন) ভাঙা
    parts = re.split(r"(?<=[।?!.॥])\s+|\n+", text)
    parts = [p.strip() for p in parts if p and p.strip()]

    chunks, cur = [], ""
    for p in parts:
        # একটা বাক্যই যদি লিমিটের চেয়ে বড় হয়, কমা/স্পেসে ভাঙি
        while len(p) > limit:
            cut = max(p.rfind(",", 0, limit), p.rfind("،", 0, limit), p.rfind(" ", 0, limit))
            if cut <= 0:
                cut = limit
            chunks.append(p[:cut].strip())
            p = p[cut:].strip(" ,،")
        if len(cur) + len(p) + 1 <= limit:
            cur = (cur + " " + p).strip()
        else:
            if cur:
                chunks.append(cur)
            cur = p
    if cur:
        chunks.append(cur)
    return [c for c in chunks if c]


# ---------------------------------------------------------------------------
# ধাপ ২: বাংলা টেক্সট থেকে ভয়েস  <<<  আপনার নিজের কোড এখানে বসান  >>>
# ---------------------------------------------------------------------------
def synthesize(text, out_path, options):
    """একটা টেক্সট অংশ থেকে একটা অডিও ফাইল (out_path, mp3) বানাবে।

    এখন এখানে Microsoft Edge TTS (edge-tts) আছে, বাংলা সাপোর্ট করে।
    নিজের ডাবিং/TTS কোড ব্যবহার করতে চাইলে এই ফাংশনের ভেতরটা বদলান।
    শুধু শর্ত: শেষে out_path এ একটা অডিও ফাইল লিখতে হবে।
    """
    import edge_tts  # দেরিতে ইমপোর্ট, যাতে ইনস্টল না থাকলে বাকি অংশ চলে

    voice = options.get("voice") or DEFAULT_VOICE
    rate = options.get("rate") or "+0%"

    async def _run():
        await edge_tts.Communicate(text, voice, rate=rate).save(out_path)

    last = None
    for _ in range(3):  # নেটওয়ার্কের ছোটখাটো সমস্যায় আবার চেষ্টা
        try:
            asyncio.run(_run())
            if os.path.exists(out_path) and os.path.getsize(out_path) > 0:
                return
        except Exception as e:  # noqa: BLE001
            last = e
    raise DubError(f"ভয়েস বানানো যায়নি: {last}")


# ---------------------------------------------------------------------------
# ffmpeg সাহায্যকারী
# ---------------------------------------------------------------------------
def _run(cmd):
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise DubError("ffmpeg এ সমস্যা: " + (r.stderr or "")[-400:])
    return r.stdout


def _duration(path):
    out = _run(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                "-of", "json", path])
    try:
        return float(json.loads(out)["format"]["duration"])
    except Exception as e:  # noqa: BLE001
        raise DubError(f"অডিওর দৈর্ঘ্য পড়া যায়নি: {path}") from e


def _concat(files, out_path):
    """একাধিক অডিও ফাইল এক ফাইলে জোড়া (একই মানে এনকোড করে)।"""
    with tempfile.TemporaryDirectory() as td:
        lst = os.path.join(td, "list.txt")
        with open(lst, "w", encoding="utf-8") as f:
            for p in files:
                f.write("file '" + p.replace("'", "'\\''") + "'\n")
        _run(["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0",
              "-i", lst, "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame",
              "-q:a", "2", out_path])


# ---------------------------------------------------------------------------
# ধাপ ৩: ভয়েস + মিউজিক মিক্স
# ---------------------------------------------------------------------------
def mix(voice_path, music_path, out_path, music_db=-14.0):
    """মিউজিক ভয়েসের নিচে থাকবে (ভয়েস চললে নিজে থেকে আরও নামবে),
    ভয়েসের দৈর্ঘ্যের সাথে মিলিয়ে কাটা/লুপ হবে, শেষে ফেড আউট।"""
    vdur = _duration(voice_path)
    total = vdur + TAIL_SECONDS
    fade_start = max(total - TAIL_SECONDS, 0)
    fg = (
        f"[0:a]apad=pad_dur={TAIL_SECONDS},asplit=2[vsc][vmix];"
        f"[1:a]volume={music_db}dB,afade=t=in:st=0:d=2[m];"
        "[m][vsc]sidechaincompress=threshold=0.02:ratio=6:attack=20:release=500[duck];"
        "[vmix][duck]amix=inputs=2:duration=first:normalize=0,"
        f"afade=t=out:st={fade_start:.2f}:d={TAIL_SECONDS}[out]"
    )
    _run(["ffmpeg", "-y", "-loglevel", "error",
          "-i", voice_path, "-stream_loop", "-1", "-i", music_path,
          "-filter_complex", fg, "-map", "[out]", "-t", f"{total:.2f}",
          "-ar", "44100", "-ac", "2", "-c:a", "libmp3lame", "-q:a", "2", out_path])


# ---------------------------------------------------------------------------
# মূল ফাংশন (server.py এটাই ডাকে)
# ---------------------------------------------------------------------------
def process(text_path, music_path, out_path, options=None, progress=None):
    """bangla.txt + music.mp3  ->  final_audio.mp3

    progress(percent:int, message:str) বললে সাইটে প্রগ্রেস দেখা যাবে।
    """
    options = options or {}
    progress = progress or (lambda pct, msg: None)

    with open(text_path, "r", encoding="utf-8-sig", errors="replace") as f:
        text = f.read().strip()
    if not text:
        raise DubError("bangla.txt ফাঁকা।")

    chunks = split_text(text)
    if not chunks:
        raise DubError("টেক্সট থেকে কিছু পড়া যায়নি।")

    try:
        music_db = float(options.get("music_db", -14))
    except (TypeError, ValueError):
        music_db = -14.0
    music_db = max(-40.0, min(0.0, music_db))

    with tempfile.TemporaryDirectory() as td:
        parts = []
        n = len(chunks)
        for i, ch in enumerate(chunks, 1):
            progress(5 + int(80 * (i - 1) / n), f"ভয়েস বানানো হচ্ছে ({i}/{n})")
            p = os.path.join(td, f"part_{i:04d}.mp3")
            synthesize(ch, p, options)
            parts.append(p)

        progress(86, "ভয়েসের অংশগুলো জোড়া লাগানো হচ্ছে")
        voice = os.path.join(td, "voice.mp3")
        _concat(parts, voice)

        progress(92, "মিউজিকের সাথে মেশানো হচ্ছে")
        mix(voice, music_path, out_path, music_db)

    progress(100, "শেষ")
    return out_path
