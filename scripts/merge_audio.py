import os
import subprocess

OUTPUT_CLIPS_DIR = "output_2clips"
GENERATED_DIR = "assets/generated"
FINAL_OUTPUT_DIR = "output/merged_videos"

os.makedirs(FINAL_OUTPUT_DIR, exist_ok=True)

def compose_customer_video(customer_id, lang):
    folder = f"{customer_id}_{lang}"
    folder_path = os.path.join(OUTPUT_CLIPS_DIR, folder)

    audio1 = os.path.join(folder_path, f"01_{lang}.mp3")
    audio2 = os.path.join(folder_path, f"02_{lang}.mp3")
    loan_img = os.path.join(GENERATED_DIR, f"{customer_id}_loan.png")
    emi_img = os.path.join(GENERATED_DIR, f"{customer_id}_emi.png")

    # Step 1: check files
    if not (os.path.exists(audio1) and os.path.exists(audio2)):
        print(f"⚠️ Skipping {folder} — missing audio files")
        return
    if not (os.path.exists(loan_img) and os.path.exists(emi_img)):
        print(f"⚠️ Skipping {folder} — missing image files")
        return

    print(f"🎬 Processing {folder}")

    # Step 2: join both audios
    combined_audio = os.path.join(folder_path, "combined_audio.mp3")
    list_file = os.path.join(folder_path, "audio_list.txt")
    with open(list_file, "w") as f:
        f.write(f"file '{os.path.abspath(audio1)}'\n")
        f.write(f"file '{os.path.abspath(audio2)}'\n")

    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", list_file,
        "-c", "copy", combined_audio
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    # Step 3: get durations using ffprobe
    def get_duration(path):
        result = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "csv=p=0", path],
            capture_output=True, text=True
        )
        return float(result.stdout.strip())

    dur1 = get_duration(audio1)
    dur2 = get_duration(audio2)
    print(f"🕒 Durations → {dur1:.2f}s + {dur2:.2f}s")

    # Step 4: make two image-based video clips
    clip1 = os.path.join(folder_path, "clip1.mp4")
    clip2 = os.path.join(folder_path, "clip2.mp4")

    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", loan_img, "-t", str(dur1),
        "-vf", "scale=1280:720", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        clip1
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    subprocess.run([
        "ffmpeg", "-y", "-loop", "1", "-i", emi_img, "-t", str(dur2),
        "-vf", "scale=1280:720", "-c:v", "libx264", "-pix_fmt", "yuv420p",
        clip2
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    # Step 5: merge both clips
    video_list = os.path.join(folder_path, "video_list.txt")
    with open(video_list, "w") as f:
        f.write(f"file '{os.path.abspath(clip1)}'\n")
        f.write(f"file '{os.path.abspath(clip2)}'\n")

    combined_video = os.path.join(folder_path, "combined_video.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", video_list, "-c", "copy", combined_video
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    # Step 6: add combined audio to final video
    final_output = os.path.join(FINAL_OUTPUT_DIR, f"{customer_id}_{lang}.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-i", combined_video, "-i", combined_audio,
        "-c:v", "copy", "-c:a", "aac", "-shortest", final_output
    ], stdout=subprocess.DEVNULL, stderr=subprocess.STDOUT)

    print(f"✅ Video ready → {final_output}\n")

# -------------------------------------------
# MAIN LOGIC WITH IF-ELSE
# -------------------------------------------
if __name__ == "__main__":
    TEST_MODE = False   # 👈 change this to False to run for all customers

    if TEST_MODE:
        # 🧪 Run only for one specific ID (for testing)
        compose_customer_video(1, "hindi")
    else:
        # 🚀 Run for all folders in output_2clips
        for folder in os.listdir(OUTPUT_CLIPS_DIR):
            if "_" not in folder:
                continue
            cust_id, lang = folder.split("_", 1)
            compose_customer_video(cust_id, lang)
