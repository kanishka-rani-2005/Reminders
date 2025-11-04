import subprocess
import os
import pandas as pd

# ==============================
# CONFIGURATION
# ==============================
DATA_PATH = "data/customers_master.csv"
FINAL_VIDEOS_DIR = "output/final_videos"
IMAGE1 = "assets/static/1.jpg"
IMAGE2 = "assets/static/Hindi_Card_3.jpg"

# ✅ Toggle Test Mode
TEST_MODE = False  # 👈 Set to False to process all customers

def apply_templates_with_ffmpeg(input_video, output_video, image1, image2):
    """Applies two overlays to a single video using ffmpeg."""
    os.makedirs(os.path.dirname(output_video), exist_ok=True)

    cmd = [
        "ffmpeg",
        "-i", input_video,
        "-i", image1,
        "-i", image2,
        "-filter_complex",
        "[0:v][1:v]overlay=enable='between(t,0,1)':x=0:y=0[v1];"
        "[v1][2:v]overlay=enable='between(t,30,40)':x=0:y=0[vout]",
        "-map", "[vout]",
        "-map", "0:a?",  # keep original audio if available
        "-c:v", "libx264",
        "-crf", "18",
        "-preset", "veryfast",
        "-c:a", "copy",
        "-y",  # overwrite
        output_video
    ]

    print(f"🎬 Applying templates to {os.path.basename(input_video)} ...")
    subprocess.run(cmd, check=True)
    print(f"✅ Done: {output_video}\n")


def process_customer(cust_id):
    """Apply templates to a single customer's video."""
    input_video = os.path.join(FINAL_VIDEOS_DIR, f"final_hindi_{cust_id}.mp4")
    output_video = os.path.join(FINAL_VIDEOS_DIR, f"final_hindi_with_cards_{cust_id}.mp4")

    if not os.path.exists(input_video):
        print(f"⚠️ Skipping {cust_id} — input video not found.")
        return

    try:
        apply_templates_with_ffmpeg(input_video, output_video, IMAGE1, IMAGE2)
    except subprocess.CalledProcessError as e:
        print(f"❌ FFmpeg failed for {cust_id}: {e}")


def main():
    if not os.path.exists(DATA_PATH):
        print(f"❌ CSV not found: {DATA_PATH}")
        return

    df = pd.read_csv(DATA_PATH)

    if "id" in df.columns:
        ids = df["id"].astype(str).tolist()
    elif "ID" in df.columns:
        ids = df["ID"].astype(str).tolist()
    else:
        raise ValueError("❌ CSV must contain 'id' or 'ID' column")

    print(f"🧾 Found {len(ids)} customers in CSV")

    if TEST_MODE:
        test_id = ids[0]
        print(f"\n🧪 TEST MODE ON → Running only for ID: {test_id}")
        process_customer(test_id)
    else:
        for cid in ids:
            process_customer(cid)

    print("\n🏁 All done!")


if __name__ == "__main__":
    main()
