import os
import subprocess

# ===============================================================
# CONFIGURATION
# ===============================================================
BASE_VIDEO_PATH = "assets/base_videos/base_hindi.mp4"
GENERATED_DIR = "assets/generated"
STATIC_DIR = "assets/static"
OUTPUT_DIR = "output/final_videos"
AUDIO_DIR = "output_dynamic_speech"
LANGUAGE = "hindi"

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===============================================================
# TIMESTAMP SETTINGS (seconds)
# ===============================================================
TIMESTAMPS = {
    "static1": (1, 2),
    "card1": (5, 10),
    "card2": (15, 20),
    "static2": (35, 40)
}

# Audio start times (seconds)
AUDIO_TIMESTAMPS = {
    1: 0,
    2: 6,
    3: 13,
    4: 18,
    5: 25,
    6: 30,
    7: 38
}

# ===============================================================
# HELPERS
# ===============================================================
def build_audio_filter(customer_id: int, language: str):
    """
    Create FFmpeg filter to keep base audio but replace only segments
    defined in AUDIO_TIMESTAMPS with new generated audio clips.
    """
    folder = os.path.join(AUDIO_DIR, f"{customer_id}_{language}")
    filters, amix_inputs, inputs = [], [], []

    # Input 0:a will be base audio
    filters.append("[0:a]volume=1.0[a_base]")  # keep base audio

    input_offset = 1  # video = 0, images = 1–4 → first audio input is index 5

    idx = 0
    for i in range(1, 8):
        file = os.path.join(folder, f"0{i}_{language}.mp3")
        if not os.path.exists(file):
            continue

        delay = int(AUDIO_TIMESTAMPS.get(i, 0) * 1000)
        inputs += ["-i", file]
        # Slight fade to blend better
        filters.append(f"[{input_offset + 4 + idx}:a]adelay={delay}|{delay},volume=1.2,afade=t=in:st={delay/1000}:d=0.2,afade=t=out:st={delay/1000+2}:d=0.2[a{idx}]")
        amix_inputs.append(f"[a{idx}]")
        idx += 1

    # Combine base + overlays
    if idx > 0:
        mix = "[a_base]" + "".join(amix_inputs)
        filters.append(f"{mix}amix=inputs={idx+1}:duration=longest[aout]")
        return inputs, ";".join(filters), "[aout]"
    else:
        return inputs, "[0:a]anull[aout]", "[aout]"


def build_overlay_filter():
    """
    Create overlay chain for static and generated images.
    """
    filters = []
    prev = "[0:v]"
    next_input = 1
    for i, name in enumerate(["static1", "card1", "card2", "static2"]):
        start, end = TIMESTAMPS[name]
        filters.append(
            f"{prev}[{next_input}:v]overlay=(W-w)/2:(H-h)/2:enable='between(t,{start},{end})'[v{i+1}]"
        )
        prev = f"[v{i+1}]"
        next_input += 1

    return ";".join(filters), prev


# ===============================================================
# MAIN COMPOSING
# ===============================================================
def compose_customer_video(customer_id: int, language: str):
    print(f"🎬 Composing video for customer {customer_id} ({language}) ...")

    # Prepare image paths
    card1 = os.path.join(GENERATED_DIR, f"{customer_id}_loan.png")
    card2 = os.path.join(GENERATED_DIR, f"{customer_id}_emi.png")
    static1 = os.path.join(STATIC_DIR, "1.jpg")
    static2 = os.path.join(STATIC_DIR, f"{language.capitalize()}_Card_3.jpg")

    overlay_inputs = ["-i", static1, "-i", card1, "-i", card2, "-i", static2]
    audio_inputs, audio_filter, audio_out = build_audio_filter(customer_id, language)
    overlay_filter, video_out = build_overlay_filter()

    filter_complex = f"{overlay_filter};{audio_filter}"

    output_path = os.path.join(OUTPUT_DIR, f"{customer_id}_{language}.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", BASE_VIDEO_PATH,
        *overlay_inputs,
        *audio_inputs,
        "-filter_complex", filter_complex,
        "-map", video_out,
        "-map", audio_out,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    subprocess.run(cmd, check=True)
    print(f"✅ Saved: {output_path}\n")


import pandas as pd
import os

CUSTOMER_CSV = "data/customers_master.csv"  # 👈 change to your actual CSV path

def main():
    # Read customer details
    df = pd.read_csv(CUSTOMER_CSV)

    # Extract customer IDs and languages
    customers = df["id"].tolist()
    languages = df["language"].unique().tolist()  # assumes you have a 'language' column

    print(f"🧾 Found {len(customers)} customers: {customers}")
    print(f"🌐 Languages found: {languages}\n")

    # Generate videos
    for lang in languages:
        lang_customers = df[df["language"] == lang]["id"].tolist()
        for cust in lang_customers:
            compose_customer_video(cust, lang)

    print("\n🎯 All videos composed successfully!")

if __name__ == "__main__":
    main()

if __name__ == "__main__":
    main()
