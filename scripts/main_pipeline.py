import subprocess
import os
import pandas as pd

SCRIPTS_DIR = "scripts"
STEPS = [
    "prepare_customer_csv.py",      
    "generate_audio_snippets.py",
    "generate_cards.py",         
    "compose_videos.py"           
]

def run_pipeline():
    print("🚀 Starting full video generation pipeline...\n")
    for step in STEPS:
        path = os.path.join(SCRIPTS_DIR, step)
        print(f"🟢 Running: {step}")
        try:
            subprocess.run([os.sys.executable, path], check=True)
            print(f"✅ Completed: {step}\n")
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed at {step}: {e}")
            break

    print("🎯 All steps executed successfully!")

if __name__ == "__main__":
    run_pipeline()
