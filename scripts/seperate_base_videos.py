import subprocess
import os

INPUT = "assets/base_videos/base_hindi.mp4"
OUTPUT_DIR = "output/merged_videos"
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Define parts
parts = [
    ("0", "4", "base_hindi_part1.mp4"),
    ("30", "50", "base_hindi_part2.mp4")
]

# Run FFmpeg for each segment
for start, end, output in parts:
    output_path = os.path.join(OUTPUT_DIR, output)
    cmd = [
        "ffmpeg", "-y",  # overwrite if exists
        "-i", INPUT,
        "-ss", start,
        "-to", end,
        "-c", "copy",
        output_path
    ]
    subprocess.run(cmd, check=True)
    print(f"✅ Created: {output_path}")
