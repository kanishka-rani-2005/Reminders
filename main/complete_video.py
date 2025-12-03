import subprocess
from pathlib import Path
import pandas as pd
import re
import sys
import json
from collections import defaultdict

# ---------- CONFIG ----------
ROOT = Path(".")
DATA_CSV = ROOT / "data" / "customers_master.csv"
GENERATED = ROOT / "assets" / "generated"
BASE_VIDEOS_DIR = ROOT / "assets" / "base_videos"
STATIC_DIR = ROOT / "assets" / "static"
OUTPUT_DIR = ROOT / "assets" / "generated_videos"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

TSPEC = "c1=0:06-0:12, c2=0:12-0:21 , c3=0:23-0:47"

FF_VCODEC = "libx264"
FF_CRf = "20"
FF_PRESET = "veryfast"
FF_AUDIO_CODEC = "aac"
FF_AUDIO_BITRATE = "128k"

# ---------- helpers ----------
def parse_time_token(t):
    if not t:
        return 0.0
    t = t.strip().replace('.', ':')
    parts = t.split(':')
    try:
        parts_i = list(map(int, parts))
    except ValueError:
        return float(t)
    if len(parts_i) == 1:
        return float(parts_i[0])
    if len(parts_i) == 2:
        mm, ss = parts_i
        return mm*60 + ss
    if len(parts_i) == 3:
        hh, mm, ss = parts_i
        return hh*3600 + mm*60 + ss
    raise ValueError(f"Unsupported time format: {t}")

def parse_range(rng):
    rng = rng.strip()
    if '-' not in rng:
        raise ValueError("Range must include dash '-'")
    a,b = rng.split('-',1)
    return parse_time_token(a), parse_time_token(b)

def parse_tspec(spec):
    out = {}
    for part in re.split(r'[,\n]+', spec):
        if not part.strip():
            continue
        if '=' not in part:
            continue
        key, rng = part.split('=',1)
        key = key.strip().lower()
        s,e = parse_range(rng.strip())
        out[key] = (float(s), float(e))
    return out

def get_video_dimensions(video_path: Path):
    cmd = [
        "ffprobe", "-v", "error",
        "-select_streams", "v:0",
        "-show_entries", "stream=width,height",
        "-of", "json",
        str(video_path)
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    if proc.returncode != 0:
        raise RuntimeError(proc.stderr.decode())
    info = json.loads(proc.stdout.decode())
    streams = info.get("streams") or []
    if not streams:
        raise RuntimeError("No video streams found")
    w = int(streams[0]["width"])
    h = int(streams[0]["height"])
    return w, h

# ---------- parse tspec ----------
slots = parse_tspec(TSPEC)
c1_start, c1_end = slots.get("c1", (None, None))
c2_start, c2_end = slots.get("c2", (None, None))
c3_start, c3_end = slots.get("c3", (None, None))

print(f"Using slots: c1={c1_start}-{c1_end}, c2={c2_start}-{c2_end}, c3={c3_start}-{c3_end}")

# ---------- load customers ----------
df = pd.read_csv(DATA_CSV, dtype=str).fillna("")
rows = df.to_dict(orient="records")
if not rows:
    sys.exit("No rows found in CSV")

# group by language (so we can reuse base video/static per language)
by_lang = defaultdict(list)
for r in rows:
    lang = (r.get("language") or "english").strip()
    by_lang[lang].append(r)

# ---------- process each language group ----------
for lang, recs in by_lang.items():
    print(f"\nLanguage group: '{lang}' ({len(recs)} customers)")

    # locate base video (try common casings)
    candidates = [
        BASE_VIDEOS_DIR / f"{lang}.mp4",
        BASE_VIDEOS_DIR / f"{lang.capitalize()}.mp4",
        BASE_VIDEOS_DIR / f"{lang.lower()}.mp4",
        BASE_VIDEOS_DIR / f"{lang.upper()}.mp4",
    ]
    base_vid = next((c for c in candidates if c.exists()), None)
    if base_vid is None:
        print(f"  No base video found for language '{lang}', skipping all customers in this language.")
        continue

    try:
        vid_w, vid_h = get_video_dimensions(base_vid)
    except Exception as e:
        print(f"  Failed to probe base video: {e}")
        continue

    # static c3 card (language-level)
    static_candidates = [
        STATIC_DIR / f"{lang}_Card_3.jpg",
        STATIC_DIR / f"{lang.capitalize()}_Card_3.jpg",
        STATIC_DIR / f"{lang.lower()}_Card_3.jpg",
        STATIC_DIR / f"{lang.upper()}_Card_3.jpg",
    ]
    static_card = next((c for c in static_candidates if c.exists()), None)
    if static_card:
        print(f"  Found static c3 card: {static_card}")

    # ---------- per-customer processing ----------
    for r in recs:
        id_raw = r.get("id") or ""
        id_ = str(id_raw).strip()
        if not id_:
            print("  Skipping a row with empty id")
            continue

        print(f"  Customer id={id_} ...")

        # customer-specific overlays
        overlays = []
        loan_img = GENERATED / f"{id_}_loan.png"
        emi_img = GENERATED / f"{id_}_emi.png"

        if loan_img.exists() and c1_start is not None:
            overlays.append({"img": str(loan_img), "start": c1_start, "end": c1_end})
            print("    found loan overlay")
        if emi_img.exists() and c2_start is not None:
            overlays.append({"img": str(emi_img), "start": c2_start, "end": c2_end})
            print("    found emi overlay")

        # add language-level static c3 if present
        if static_card and c3_start is not None:
            overlays.append({"img": str(static_card), "start": c3_start, "end": c3_end})
            print("    added static c3 card")

        # output file per customer
        out_file = OUTPUT_DIR / f"{lang.lower()}_{id_}_video.mp4"

        # If no overlays, just fast-copy the base video so every customer gets a file
        if not overlays:
            print("    No overlays for this customer; copying base video to output (fast).")
            cmd = ["ffmpeg", "-y", "-i", str(base_vid), "-c", "copy", str(out_file)]
            proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            if proc.returncode != 0:
                print(f"    Failed to copy base video for id={id_}:")
                print(proc.stderr.decode()[:1000])
            else:
                print(f"    Wrote (copy): {out_file}")
            continue

        # Build ffmpeg inputs: base video + per-overlay inputs
        ff_inputs = [str(base_vid)] + [ov["img"] for ov in overlays]

        # Build filter_complex; we will scale each overlay to video dims and overlay sequentially
        filter_parts = []
        last = "[0:v]"
        tmp_idx = 0
        input_idx = 1

        for ov in overlays:
            img_label = f"[{input_idx}:v]"
            enable = f"between(t,{ov['start']},{ov['end']})"
            filter_parts.append(f"{img_label}scale={vid_w}:{vid_h}[fg{tmp_idx}]")
            filter_parts.append(f"{last}[fg{tmp_idx}]overlay=0:0:enable='{enable}'[tmp{tmp_idx}]")
            last = f"[tmp{tmp_idx}]"
            tmp_idx += 1
            input_idx += 1

        filter_complex = ";".join(filter_parts)

        # Build ffmpeg command
        cmd = ["ffmpeg", "-y"]
        for inp in ff_inputs:
            cmd += ["-i", inp]

        cmd += [
            "-filter_complex", filter_complex,
            "-map", last,
            "-map", "0:a?",
            "-c:v", FF_VCODEC,
            "-crf", FF_CRf,
            "-preset", FF_PRESET,
            "-c:a", FF_AUDIO_CODEC,
            "-b:a", FF_AUDIO_BITRATE,
            str(out_file)
        ]

        # run
        proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if proc.returncode != 0:
            print(f"    FFMPEG FAILED for id={id_}:")
            # show a snippet of stderr for debugging
            print(proc.stderr.decode()[:2000])
        else:
            print(f"    Wrote: {out_file}")

print("\nAll done.")
