import os
import requests
from pathlib import Path

# ========= CONFIG =========
HEYGEN_API_KEY = "sk_V2_hgu_kxLruCQ2C0a_mDsDfxQfiirKohMpJ26PXDz1q4P0YAo0"   # <-- Put your HeyGen API key here
API_URL = "https://api.heygen.com/v2/video/generate"

BASE_DIR = Path("assets/base_videos")
BASE_DIR.mkdir(parents=True, exist_ok=True)

HEADERS = {
    "Authorization": f"Bearer {HEYGEN_API_KEY}",
    "Content-Type": "application/json"
}

LANG_AUDIO = {
    "hindi": {
        "audio_asset_id": "f76c8f3256414b57b8a3f947bb31c179"
    },
    "tamil": {
        "audio_asset_id": "def1b576e7d143839e37f4e197490e77"
    },
    "telugu": {
        "audio_asset_id": "b648ad812daa461db61243938be41afd"
    },
    "kannada": {
        "audio_asset_id": "9fbc36bd9d404158b0644ab7ec9782b6"
    }
}

AVATAR_ID = "Adriana_Business_Front_public"   
VIDEO_DIMENSIONS = {"width": 1280, "height": 720}


def generate_video(lang: str, asset_id: str):
    """Generate video using an existing audio asset."""
    payload = {
        "video_inputs": [
            {
                "character": {
                    "type": "avatar",
                    "avatar_id": AVATAR_ID,
                    "avatar_style": "normal"
                },
                "voice": {
                    "type": "audio",
                    "audio_asset_id": asset_id
                }
            }
        ],
        "dimension": VIDEO_DIMENSIONS
    }

    print(f"🎬 Generating {lang} base video...")
    resp = requests.post(API_URL, headers=HEADERS, json=payload)

    if resp.status_code == 200:
        data = resp.json().get("data", {})
        video_id = data.get("video_id")
        print(f"✅ {lang} video started (ID: {video_id})")
        return video_id
    else:
        print(f"❌ Failed for {lang}: {resp.status_code} - {resp.text}")
        return None


def main():
    for lang, info in LANG_AUDIO.items():
        asset_id = info["audio_asset_id"]
        if asset_id.startswith("PUT_"):
            print(f"⚠️  Skipping {lang} (no asset ID configured)")
            continue

        vid = generate_video(lang, asset_id)
        if vid:
            print(f"🚀 Requested {lang} base video: {vid}\n")


if __name__ == "__main__":
    main()
