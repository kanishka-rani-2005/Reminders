import os
import subprocess
import pandas as pd

# ===============================================================
# CONFIGURATION
# ===============================================================
BASE_VIDEO_PATH = "assets/base_videos/base_hindi.mp4"
GENERATED_DIR = "assets/generated"
STATIC_DIR = "assets/static"
OUTPUT_DIR = "output/final_videos"
AUDIO_DIR = "output_dynamic_speech"
LANGUAGE = "hindi" # Default language, will be overridden

os.makedirs(OUTPUT_DIR, exist_ok=True)

# ===============================================================
# PER-LANGUAGE TIMESTAMPS
# ===============================================================

# 🖼 CARD (IMAGE) OVERLAY TIMESTAMPS
CARD_TIMESTAMPS_MAP = {
    "hindi": {
        "static1": (1, 2),
        "card1": (3, 13),#loan
        "card2": (14,28),#emi
        "static2": (35, 43)#penality
    },
    "tamil": {
        "static1": (1, 3),
        "card1": (6, 12),
        "card2": (18, 22),
        "static2": (37, 42)
    },
    "telugu": {
        "static1": (0.5, 2.5),
        "card1": (5, 11),
        "card2": (17, 23),
        "static2": (36, 41)
    },
    "kannada": {
        "static1": (1, 2.5),
        "card1": (5.5, 11),
        "card2": (16, 21),
        "static2": (34, 39)
    }
}

# 🎧 AUDIO TIMESTAMPS PER LANGUAGE
AUDIO_TIMESTAMPS_MAP = {
    "hindi": {
        1: 0,
        2: 6,
        3: 13,
        4: 18,
        5: 25,
        6: 30,
        7: 38
    },
    "tamil": {
        1: 0,
        2: 5,
        3: 12,
        4: 17,
        5: 23,
        6: 29,
        7: 36
    },
    "telugu": {
        1: 0,
        2: 7,
        3: 15,
        4: 21,
        5: 27,
        6: 32,
        7: 40
    },
    "kannada": {
        1: 0,
        2: 5,
        3: 10,
        4: 16,
        5: 22,
        6: 28,
        7: 35
    }
}

# ===============================================================
# HELPERS
# ===============================================================

def build_audio_filter(customer_id: int, language: str, AUDIO_TIMESTAMPS: dict):
    """
    Controls base audio volume to duck/mute during generated voice segments
    using direct volume reduction in the amix.
    """
    folder = os.path.join(AUDIO_DIR, f"{customer_id}_{language}")
    filters = []
    amix_inputs = []
    new_ffmpeg_inputs = [] # Only for generated audio files

    # Configurable parameters
    SPEECH_DURATION_ESTIMATE = 4.0 # seconds - Crucial for accurate muting
    BASE_AUDIO_DUCK_VOLUME = 0.0 # Set to 0.0 for full mute, 0.1-0.2 for subtle background
    FADE_DURATION = 0.1 # seconds for fade in/out

    # Collect all generated audio info
    generated_audio_info = [] # List of (start_time, end_time, file_path)
    for i in range(1, 8):
        file = os.path.join(folder, f"0{i}_{language}.mp3")
        if os.path.exists(file):
            start = AUDIO_TIMESTAMPS.get(i, 0)
            generated_audio_info.append((start, start + SPEECH_DURATION_ESTIMATE, file))
    
    # Sort segments by start time to correctly build the mute expression
    generated_audio_info.sort(key=lambda x: x[0])

    # --- Step 1: Process the base video's audio ---
    mute_expr_parts = []
    if generated_audio_info:
        for start_gen, end_gen, _ in generated_audio_info:
            mute_expr_parts.append(f"between(t,{start_gen},{end_gen})")
        
        # If any generated audio exists, build the enable expression for the base audio's volume.
        # It's at BASE_AUDIO_DUCK_VOLUME when generated audio is playing, else 1.0.
        mute_expression = "+".join(mute_expr_parts)
        filters.append(
            f"[0:a]volume=enable='{mute_expression}':volume={BASE_AUDIO_DUCK_VOLUME},"
            f"volume=enable='not({mute_expression})':volume=1.0[a_base_ducked]"
        )
    else:
        # If no generated audio, base audio just plays normally
        filters.append("[0:a]volume=1.0[a_base_ducked]")
    
    amix_inputs.append("[a_base_ducked]")


    # --- Step 2: Process the generated overlay audios ---
    # The input index for the first audio file will be after the base video (0) and all image overlays (4)
    audio_input_idx_offset = 1 + 4 # 0 for base video, 4 for image overlays

    for idx, (start, _, file) in enumerate(generated_audio_info):
        new_ffmpeg_inputs.extend(["-i", file]) # Add this audio file as an input
        
        # Apply delay and fade to the generated speech
        # The stream for this audio file will be at input index (audio_input_idx_offset + idx)
        filters.append(
            f"[{audio_input_idx_offset + idx}:a]adelay={int(start * 1000)}|{int(start * 1000)},"
            f"volume=1.2," # Slightly boost volume for generated speech
            f"afade=t=in:st={start}:d={FADE_DURATION},"
            f"afade=t=out:st={start + SPEECH_DURATION_ESTIMATE - FADE_DURATION}:d={FADE_DURATION}[a_gen_{idx}]"
        )
        amix_inputs.append(f"[a_gen_{idx}]")

    # --- Step 3: Combine all audio streams using amix ---
    if len(amix_inputs) > 1: # At least base audio + one generated audio
        mix_inputs_str = "".join(amix_inputs)
        filters.append(f"{mix_inputs_str}amix=inputs={len(amix_inputs)}:duration=longest:dropout_transition=0[aout]")
    elif amix_inputs: # Only base audio or only one generated audio
        filters.append(f"{amix_inputs[0]}anull[aout]") # Just pass through if only one stream
    else: # Should not happen if there's a base video, but as a fallback
        filters.append("anullsrc=channel_layout=stereo:sample_rate=48000[aout]")

    return new_ffmpeg_inputs, ";".join(filters), "[aout]"


def build_overlay_filter(language: str, CARD_TIMESTAMPS: dict):
    """
    Create overlay chain for static and generated images.
    """
    filters = []
    prev = "[0:v]" # Start with the base video stream
    next_input = 1 # The first image overlay is input stream #1
    for i, name in enumerate(["static1", "card1", "card2", "static2"]):
        start, end = CARD_TIMESTAMPS[name]
        filters.append(
            f"{prev}[{next_input}:v]overlay=(W-w)/2:(H-h)/2:enable='between(t,{start},{end})'[v{i+1}]"
        )
        prev = f"[v{i+1}]" # The output of this overlay becomes the input for the next
        next_input += 1 # Increment for the next image input stream

    return ";".join(filters), prev


# ===============================================================
# MAIN COMPOSING
# ===============================================================
def compose_customer_video(customer_id: int, language: str):
    print(f"🎬 Composing video for customer {customer_id} ({language}) ...")

    # Prepare image paths - These become ffmpeg inputs 1, 2, 3, 4
    card1 = os.path.join(GENERATED_DIR, f"{customer_id}_loan.png")
    card2 = os.path.join(GENERATED_DIR, f"{customer_id}_emi.png")
    static1 = os.path.join(STATIC_DIR, "1.jpg")
    static2 = os.path.join(STATIC_DIR, f"{language.capitalize()}_Card_3.jpg")

    overlay_inputs = []
    image_paths = [static1, card1, card2, static2]
    for img_path in image_paths:
        if os.path.exists(img_path):
            overlay_inputs.extend(["-i", img_path])
        else:
            print(f"⚠️ Warning: Image file not found: {img_path}. Skipping overlay for it.")
            # If an image is missing, the input count for video overlays will be less than 4.
            # This is automatically handled by build_overlay_filter as it uses next_input += 1
            # so the input indexing will adjust.

    # Get timestamps for this language
    audio_timestamps = AUDIO_TIMESTAMPS_MAP.get(language.lower(), AUDIO_TIMESTAMPS_MAP["hindi"])
    card_timestamps = CARD_TIMESTAMPS_MAP.get(language.lower(), CARD_TIMESTAMPS_MAP["hindi"])

    # Build filters
    # new_ffmpeg_inputs will contain ["-i", file1, "-i", file2, ...] for generated speech
    # audio_filter will be the filter_complex string for audio processing
    # audio_out will be the label for the final combined audio stream (e.g., "[aout]")
    new_ffmpeg_inputs, audio_filter, audio_out = build_audio_filter(customer_id, language, audio_timestamps)
    
    # overlay_filter will be the filter_complex string for video overlays
    # video_out will be the label for the final video stream (e.g., "[v4]")
    overlay_filter, video_out = build_overlay_filter(language, card_timestamps)

    filter_complex = f"{overlay_filter};{audio_filter}"

    output_path = os.path.join(OUTPUT_DIR, f"{customer_id}_{language}.mp4")

    cmd = [
        "ffmpeg", "-y",
        "-i", BASE_VIDEO_PATH, # Input 0: Base video (contains video and audio)
        *overlay_inputs,       # Inputs 1, 2, 3, 4 (for static1, card1, card2, static2)
        *new_ffmpeg_inputs,    # Inputs 5 onwards (for generated audio files)
        "-filter_complex", filter_complex,
        "-map", video_out,
        "-map", audio_out,
        "-c:v", "libx264",
        "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_path
    ]

    print(f"Executing FFmpeg command:\n{' '.join(cmd)}\n")
    subprocess.run(cmd, check=True)
    print(f"✅ Saved: {output_path}\n")


# ===============================================================
# MAIN
# ===============================================================
CUSTOMER_CSV = "data/customers_master.csv"
def main(test_mode: bool = True):
    if not os.path.exists(CUSTOMER_CSV):
        print(f"Error: Customer CSV file not found at {CUSTOMER_CSV}")
        return

    df = pd.read_csv(CUSTOMER_CSV)

    if test_mode:
        customers = [1]
        languages = ["hindi"]
        print("🧪 Running in TEST MODE (1 sample video only)")
    else:
        customers = df["id"].tolist()
        languages = df["language"].unique().tolist()

    print(f"🧾 Found {len(customers)} customers: {customers}")
    print(f"🌐 Languages found: {languages}\n")

    for lang in languages:
        if test_mode:
            for cust in customers:
                compose_customer_video(cust, lang)
        else:
            lang_customers = df[df["language"] == lang]["id"].tolist()
            for cust in lang_customers:
                compose_customer_video(cust, lang)

    print("\n🎯 All videos composed successfully!")


if __name__ == "__main__":
    main(test_mode=True)