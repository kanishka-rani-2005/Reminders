import subprocess
import os
import pandas as pd

# =========================
# CONFIGURATION
# =========================
CSV_PATH = "data/customers_master.csv"
MERGED_DIR = "output/merged_videos"
FINAL_DIR = "output/final_videos"

BASE_PART1 = "base_hindi_part1.mp4"
BASE_PART2 = "base_hindi_part2.mp4"



def normalize_clip(src_path: str, dest_path: str):
    """Normalize a video clip to fix timestamps and audio."""
    cmd = [
        "ffmpeg", "-y",
        "-i", src_path,
        "-c:v", "libx264", "-preset", "fast",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-fflags", "+genpts",
        dest_path
    ]
    subprocess.run(cmd, check=True)


def merge_videos(video_list, output_path):
    """Merge multiple video clips into one final file."""
    list_file = os.path.join(os.path.dirname(output_path), "temp_concat_list.txt")
    with open(list_file, "w", encoding="utf-8") as f:
        for v in video_list:
            abs_path = os.path.abspath(v).replace("\\", "/")
            f.write(f"file '{abs_path}'\n")

    cmd = [
        "ffmpeg", "-y",
        "-f", "concat", "-safe", "0",
        "-i", list_file,
        "-c:v", "libx264", "-preset", "medium",
        "-c:a", "aac", "-b:a", "192k", "-ar", "48000", "-ac", "2",
        "-movflags", "+faststart",
        output_path
    ]
    subprocess.run(cmd, check=True)
    os.remove(list_file)


def process_customer(cid):
    """Process video merging for a single customer ID."""
    print(f"\n🔹 Processing ID: {cid}")
    part1 = os.path.join(MERGED_DIR, BASE_PART1)
    middle = os.path.join(MERGED_DIR, f"{cid}_hindi.mp4")
    part2 = os.path.join(MERGED_DIR, BASE_PART2)

    # Ensure files exist
    for clip in [part1, middle, part2]:
        if not os.path.exists(clip):
            print(f"⚠️ Missing file: {clip}")

    # Normalize each clip
    fixed_files = []
    for clip in [part1, middle, part2]:
        if os.path.exists(clip):
            fixed_path = os.path.join(MERGED_DIR, f"fixed_{cid}_{os.path.basename(clip)}")
            print(f"🎧 Normalizing: {os.path.basename(clip)}")
            normalize_clip(clip, fixed_path)
            fixed_files.append(fixed_path)

    # Merge them
    output_path = os.path.join(FINAL_DIR, f"final_hindi_{cid}.mp4")
    print(f"🎬 Merging for ID {cid}...")
    merge_videos(fixed_files, output_path)
    print(f"✅ Done: {output_path}")


def main():
    os.makedirs(FINAL_DIR, exist_ok=True)
    os.makedirs(MERGED_DIR, exist_ok=True)

    # Load CSV
    df = pd.read_csv(CSV_PATH)
    if "id" in df.columns:
        ids = df["id"].astype(str).tolist()
    elif "ID" in df.columns:
        ids = df["ID"].astype(str).tolist()
    else:
        raise ValueError("❌ CSV must contain a column named 'id' or 'ID'")

    print(f"🧾 Found {len(ids)} customers in CSV")

    if TEST_MODE:
        # 🧪 Run only for one specific ID
        test_id = ids[0]
        print(f"\n🧪 TEST MODE ON → Running only for ID: {test_id}")
        process_customer(test_id)
    else:
        # 🚀 Run for all customers
        for cid in ids:
            process_customer(cid)

    print("\n🏁 All done!")


# =============================
# ENTRY POINT
# =============================
TEST_MODE = False  # 👈 Set to False to run for all customers

if __name__ == "__main__":
    main()
