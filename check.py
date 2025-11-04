import os
import subprocess
import pandas as pd
import shutil # For cleaning up directories

# ===============================================================
# CONFIGURATION
# ===============================================================
BASE_VIDEO_PATH = "assets/base_videos/base_hindi.mp4"
GENERATED_DIR = "assets/generated"
STATIC_DIR = "assets/static"
OUTPUT_DIR = "output/final_videos"
# Corrected AUDIO_DIR based on your screenshot
AUDIO_DIR = "output/output_dynamic_speech" # This path is relative to the project root.
TEMP_DIR = "output/temp" # Temporary directory for intermediate files for FFmpeg
CUSTOMER_CSV = "data/customers_master.csv"
TARGET_LANGUAGE = "Hindi" # <--- Specify the target language

# ===============================================================
# TIMESTAMP & SEGMENT SETTINGS (seconds)
# ===============================================================
# Define segments of the base video that will be kept.
# These will be interleaved with your generated card videos.
# Format: {segment_name: (start_time, end_time)}
BASE_VIDEO_SEGMENTS = {
    "intro": (0, 3),    # Before card1
    "middle1": (14, 15), # Between card1 and card2
    "middle2": (20, 35), # Between card2 and static2 (if static2 is also a video)
    "outro": (40, None)  # After static2 (None means to end of video)
}

# Duration of the generated card videos (in seconds)
CARD_VIDEO_DURATION = 5

# Map dynamic audio files to the cards
# The keys here are the card names (e.g., "card1", "card2")
# The values are lists of audio file indices from AUDIO_DIR to be used for that card.
# If a card has multiple audio segments, they will be concatenated.
CARD_AUDIO_MAP = {
    "card1": [1, 2], # Audio 01_Hindi.mp3 and 02_Hindi.mp3 for card1
    "card2": [3, 4], # Audio 03_Hindi.mp3 and 04_Hindi.mp3 for card2
    "static1": [5],  # Example: if static1 should have an audio too
    "static2": [6, 7], # Example: if static2 should have an audio too
}

# ===============================================================
# HELPERS
# ===============================================================

def sanitize_path_for_ffmpeg(path: str) -> str:
    """Converts a Windows path to use forward slashes for FFmpeg compatibility."""
    return path.replace("\\", "/")

def get_audio_filepaths(customer_id: int, language: str, audio_indices: list):
    """Returns a list of full paths for specified dynamic audio files."""
    # Ensure correct capitalization for language in folder name (e.g., 1_Hindi)
    folder_name = f"{customer_id}_{language.capitalize()}"
    
    # Construct the full path to the customer's audio folder
    customer_audio_folder = os.path.join(AUDIO_DIR, folder_name)

    filepaths = []
    for idx in audio_indices:
        # Ensure language capitalization for filename matches your actual files (e.g., 01_Hindi.mp3)
        file_name = f"0{idx}_{language.capitalize()}.mp3"
        full_path = os.path.join(customer_audio_folder, file_name)
        if os.path.exists(full_path):
            filepaths.append(full_path)
        else:
            print(f"Warning: Audio file not found: {full_path}")
    return filepaths

def generate_card_video(image_path: str, audio_filepaths: list, output_filepath: str, duration: int):
    """
    Generates a short video from an image and concatenates multiple audio files.
    """
    print(f"   Generating card video: {output_filepath}")

    # Ensure TEMP_DIR exists for the concat_list_path
    os.makedirs(TEMP_DIR, exist_ok=True)

    concatenated_audio_path = None
    if audio_filepaths:
        if len(audio_filepaths) > 1:
            concat_list_path = os.path.join(TEMP_DIR, f"audio_concat_list_{os.path.basename(output_filepath)}.txt") # Unique name
            with open(concat_list_path, "w") as f:
                for ap in audio_filepaths:
                    f.write(f"file '{sanitize_path_for_ffmpeg(ap)}'\n") # Sanitize path for concat list
            concatenated_audio_path = os.path.join(TEMP_DIR, f"temp_concat_audio_{os.path.basename(output_filepath)}.mp3")
            audio_concat_cmd = [
                "ffmpeg", "-y",
                "-f", "concat",
                "-safe", "0", # Necessary for absolute paths or paths outside current dir
                "-i", sanitize_path_for_ffmpeg(concat_list_path),
                "-c", "copy",
                sanitize_path_for_ffmpeg(concatenated_audio_path)
            ]
            try:
                subprocess.run(audio_concat_cmd, check=True, capture_output=True)
            except subprocess.CalledProcessError as e:
                print(f"Error concatenating audio for {image_path}:")
                print(f"Command: {' '.join(e.cmd)}")
                print(f"STDOUT: {e.stdout.decode()}")
                print(f"STDERR: {e.stderr.decode()}")
                raise
        else:
            concatenated_audio_path = audio_filepaths[0]

    # Step 2: Create video from image and (concatenated) audio using filter_complex
    cmd = [
        "ffmpeg", "-y",
        "-loop", "1", # Loop the image indefinitely until trimmed by -t or -shortest
        "-i", sanitize_path_for_ffmpeg(image_path), # Input 0: Image
    ]

    filter_complex_parts = []
    map_options = []

    # Video filter chain: scale and pad the image
    video_filter = "[0:v]scale=1920:1080:force_original_aspect_ratio=decrease,pad=1920:1080:(ow-iw)/2:(oh-ih)/2,format=yuv420p[v]"
    filter_complex_parts.append(video_filter)
    map_options.extend(["-map", "[v]"]) # Map the output of the video filter chain

    if concatenated_audio_path and os.path.exists(concatenated_audio_path):
        cmd.extend(["-i", sanitize_path_for_ffmpeg(concatenated_audio_path)]) # Input 1: Audio
        map_options.extend(["-map", "1:a:0"]) # Map audio stream from second input
        cmd.append("-shortest") # End video when shortest input stream ends
    else:
        # If no audio, create a silent audio track
        cmd.extend(["-f", "lavfi", "-i", "anullsrc=channel_layout=stereo:sample_rate=44100"]) # Input 1: Silent audio
        map_options.extend(["-map", "1:a:0"]) # Map audio stream from silent audio input

    cmd.extend([
        "-filter_complex", ";".join(filter_complex_parts), # Apply filter_complex
        "-c:v", "libx264",
        "-c:a", "aac",
        "-t", str(duration), # Trim the output to the desired duration
        *map_options,        # Apply all collected map options
        sanitize_path_for_ffmpeg(output_filepath) # Output file
    ])

    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error generating card video for {image_path}:")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"STDOUT: {e.stdout.decode()}")
        print(f"STDERR: {e.stderr.decode()}")
        raise # Re-raise the exception after printing details

    # Clean up temporary concatenated audio if it was created
    if concatenated_audio_path and len(audio_filepaths) > 1 and os.path.exists(concatenated_audio_path):
        os.remove(concatenated_audio_path)
    # Clean up concat_list_path if it was created
    if 'concat_list_path' in locals() and os.path.exists(concat_list_path):
        os.remove(concat_list_path)


def cut_base_video_segment(start_time: int, end_time: int, output_filepath: str):
    """Cuts a segment from the base video."""
    print(f"   Cutting base video segment: {output_filepath} ({start_time}-{end_time}s)")
    cmd = [
        "ffmpeg", "-y",
        "-i", sanitize_path_for_ffmpeg(BASE_VIDEO_PATH), # Input base video
        "-ss", str(start_time),
    ]
    if end_time is not None:
        cmd.extend(["-to", str(end_time)])
    cmd.extend([
        "-c", "copy", # Copy streams directly (no re-encoding)
        sanitize_path_for_ffmpeg(output_filepath) # Output file
    ])
    try:
        subprocess.run(cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error cutting base video segment: {e.stderr.decode()}")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"STDOUT: {e.stdout.decode()}")
        print(f"STDERR: {e.stderr.decode()}")
        raise

# ===============================================================
# MAIN COMPOSING
# ===============================================================
def compose_customer_video(customer_id: int, language: str):
    print(f"🎬 Composing video for customer {customer_id} ({language}) ...")
    # This temp directory is specific to the customer for intermediate video segments
    customer_temp_dir = os.path.join(TEMP_DIR, f"{customer_id}_{language}")

    # Ensure a clean slate for this customer's temp directory
    if os.path.exists(customer_temp_dir):
        shutil.rmtree(customer_temp_dir)
    os.makedirs(customer_temp_dir, exist_ok=True)

    final_segments = [] # List to hold paths of all video segments to concatenate

    # This is a more explicit sequence definition
    sequence = [
        ("base", "intro"),
        ("card", "static1"), # Treat static1 as a generated card video
        ("base", "middle1"),
        ("card", "card1"),
        ("base", "middle2"),
        ("card", "card2"),
        ("base", "outro") # This implies static2 would also be stitched if it's a generated card
    ]

    for seg_type, seg_name in sequence:
        if seg_type == "base":
            start, end = BASE_VIDEO_SEGMENTS.get(seg_name, (None, None))
            if start is None:
                print(f"   Skipping base segment '{seg_name}': start/end not defined.")
                continue

            segment_output_path = os.path.join(customer_temp_dir, f"{seg_name}.mp4")
            cut_base_video_segment(start, end, segment_output_path)
            final_segments.append(segment_output_path)

        elif seg_type == "card":
            image_path = None
            if seg_name == "card1":
                image_path = os.path.join(GENERATED_DIR, f"{customer_id}_loan.png")
            elif seg_name == "card2":
                image_path = os.path.join(GENERATED_DIR, f"{customer_id}_emi.png")
            elif seg_name == "static1":
                image_path = os.path.join(STATIC_DIR, "1.jpg")
            elif seg_name == "static2": # If static2 is also to be a dedicated video segment
                image_path = os.path.join(STATIC_DIR, f"{language.capitalize()}_Card_3.jpg")

            if not image_path or not os.path.exists(image_path):
                print(f"   Skipping card '{seg_name}': image not found at {image_path}")
                continue

            audio_indices = CARD_AUDIO_MAP.get(seg_name, [])
            audio_filepaths = get_audio_filepaths(customer_id, language, audio_indices)

            card_video_output_path = os.path.join(customer_temp_dir, f"{seg_name}_video.mp4")
            generate_card_video(image_path, audio_filepaths, card_video_output_path, CARD_VIDEO_DURATION)
            final_segments.append(card_video_output_path)

    # 2. Create a file list for FFmpeg concat demuxer
    concat_file_list_path = os.path.join(customer_temp_dir, "concat_list.txt")
    with open(concat_file_list_path, "w") as f:
        for segment_path in final_segments:
            f.write(f"file '{sanitize_path_for_ffmpeg(segment_path)}'\n") # Sanitize path for concat list

    # 3. Concatenate all segments
    # Ensure the output directory exists
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    output_path = os.path.join(OUTPUT_DIR, f"{customer_id}_{language}.mp4")
    concat_cmd = [
        "ffmpeg", "-y",
        "-f", "concat",
        "-safe", "0", # Necessary for absolute paths or paths outside current dir
        "-i", sanitize_path_for_ffmpeg(concat_file_list_path), # Input concat list
        "-c", "copy", # Copy streams directly
        sanitize_path_for_ffmpeg(output_path) # Output file
    ]
    print(f"   Concatenating final video: {output_path}")
    try:
        subprocess.run(concat_cmd, check=True, capture_output=True)
    except subprocess.CalledProcessError as e:
        print(f"Error concatenating final video: {e.stderr.decode()}")
        print(f"Command: {' '.join(e.cmd)}")
        print(f"STDOUT: {e.stdout.decode()}")
        print(f"STDERR: {e.stderr.decode()}")
        raise # Re-raise the exception after printing details


    # 4. Clean up temporary files for this customer
    print(f"   Cleaning up temporary directory: {customer_temp_dir}")
    shutil.rmtree(customer_temp_dir)

    print(f"✅ Saved: {output_path}\n")


def main():
    # Ensure TEMP_DIR exists and is clean at the start of the entire process
    if os.path.exists(TEMP_DIR):
        shutil.rmtree(TEMP_DIR)
    os.makedirs(TEMP_DIR, exist_ok=True)
    
    # Also ensure the main AUDIO_DIR exists if it's meant to be managed by the script
    # (though in your case, output_dynamic_speech is likely pre-populated)
    os.makedirs(AUDIO_DIR, exist_ok=True) 
    os.makedirs(OUTPUT_DIR, exist_ok=True) # Ensure final output directory exists

    df = pd.read_csv(CUSTOMER_CSV)
    
    # Filter for only the TARGET_LANGUAGE customers
    # Use .str.lower() for more robust case-insensitive comparison
    hindi_df = df[df["language"].str.lower() == TARGET_LANGUAGE.lower()]
    
    customers_to_process = hindi_df["id"].tolist()

    if not customers_to_process:
        print(f"No customers found for language '{TARGET_LANGUAGE}'. Exiting.")
        return

    print(f"🧾 Found {len(customers_to_process)} customers for {TARGET_LANGUAGE}: {customers_to_process}")

    # Process only the first customer for now, as requested for debugging
    customer_id = customers_to_process[0]
    compose_customer_video(customer_id, TARGET_LANGUAGE.capitalize()) # Pass capitalized language

    print("\n🎯 Processing complete!")

if _name_ == "_main_":
    main()