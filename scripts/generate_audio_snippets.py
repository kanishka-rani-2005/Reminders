import pandas as pd
import os
import requests

# ==================================================
# 🗣️ STEP 1: Generate Speech Function
# ==================================================
def generate_speech(text, lang_code, output_path):
    ELEVEN_API_KEY = "sk_f69d64ab5822565596479fab3500a503cf72a50a133794ba"   # Replace safely
    MODEL_ID = "eleven_multilingual_v2"
    VOICE_ID = "EXAVITQu4vr4xnSDxMaL"  # Multilingual voice

    url = f"https://api.elevenlabs.io/v1/text-to-speech/{VOICE_ID}"

    headers = {
        "Accept": "audio/mpeg",
        "Content-Type": "application/json",
        "xi-api-key": ELEVEN_API_KEY,
    }

    payload = {
        "text": text,
        "model_id": MODEL_ID,
        "voice_settings": {"stability": 0.4, "similarity_boost": 0.8},
    }

    response = requests.post(url, headers=headers, json=payload)

    if response.status_code == 200:
        with open(output_path, "wb") as f:
            f.write(response.content)
        print(f"✅ Saved: {output_path}")
    else:
        print(f"❌ Error {response.status_code}: {response.text}")


# ==================================================
# 💬 STEP 2: Simplified dynamic segments (7 per language)
# ==================================================
def make_dynamic_segments(row):
    name = row["name"]
    loan_no = row["loan_account_number"]
    loan_amount = row["loan_amount"]
    emi_amount = row["emi_amount"]
    due_date = row["due_date"]
    ifsc = row["ifsc"]
    last4 = str(row.get("account_last4", "XXXX"))
    lang = row["language"].strip().lower()

    segments = {
        "hindi": [
            f"प्रिय {name}.",
            f"लोन नंबर {loan_no}.",
            f"लोन राशि {loan_amount} रुपये.",
            f"ई एम आई राशि {emi_amount} रुपये.",
            f"देय तिथि {due_date}.",
            f"खाते के अंतिम चार अंक {last4}.",
            f"आई एफ एस सी कोड {ifsc}.",
        ],

        "tamil": [
            f"வாடிக்கையாளர் பெயர் {name}.",
            f"கடன் எண் {loan_no}.",
            f"கடன் தொகை {loan_amount} ரூபாய்.",
            f"இஎம்ஐ தொகை {emi_amount} ரூபாய்.",
            f"கட்டண தேதி {due_date}.",
            f"கணக்கின் கடைசி நான்கு எண்கள் {last4}.",
            f"ஐஎப்எஸ்சி குறியீடு {ifsc}.",
        ],

        "telugu": [
            f"పేరు {name}.",
            f"రుణ సంఖ్య {loan_no}.",
            f"రుణ మొత్తం {loan_amount} రూపాయలు.",
            f"ఇఎమ్ఐ మొత్తం {emi_amount} రూపాయలు.",
            f"చెల్లించవలసిన తేదీ {due_date}.",
            f"ఖాతా చివరి నాలుగు అంకెలు {last4}.",
            f"ఐఎఫ్ఎస్సీ కోడ్ {ifsc}.",
        ],

        "kannada": [
            f"ಗ್ರಾಹಕರ ಹೆಸರು {name}.",
            f"ಸಾಲ ಸಂಖ್ಯೆ {loan_no}.",
            f"ಸಾಲ ಮೊತ್ತ {loan_amount} ರೂಪಾಯಿ.",
            f"ಇಎಂಐ ಮೊತ್ತ {emi_amount} ರೂಪಾಯಿ.",
            f"ಪಾವತಿ ದಿನಾಂಕ {due_date}.",
            f"ಖಾತೆಯ ಕೊನೆಯ ನಾಲ್ಕು ಸಂಖ್ಯೆ {last4}.",
            f"ಐಎಫ್ಎಸ್ಜಿ ಕೋಡ್ {ifsc}.",
        ],

        "english": [
            f"Customer name {name}.",
            f"Loan number {loan_no}.",
            f"Loan amount {loan_amount} rupees.",
            f"EMI amount {emi_amount} rupees.",
            f"Due date {due_date}.",
            f"Last four digits {last4}.",
            f"IFSC code {ifsc}.",
        ],
    }

    return segments.get(lang, segments["english"]), lang


# ==================================================
# 🧩 STEP 3: Process CSV and Generate 7 Audio Clips
# ==================================================
def process_csv(csv_path, output_dir="output_dynamic_speech"):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(csv_path)

    for _, row in df.iterrows():
        segments, lang = make_dynamic_segments(row)
        cid = str(row["id"])
        customer_dir = os.path.join(output_dir, f"{cid}_{lang}")
        os.makedirs(customer_dir, exist_ok=True)

        print(f"\n🎙️ Generating 7 dynamic clips for {row['name']} ({lang})...")

        for i, text in enumerate(segments, start=1):
            file_path = os.path.join(customer_dir, f"{i:02d}_{lang}.mp3")
            generate_speech(text, lang, file_path)


# ==================================================
# 🚀 MAIN
# ==================================================
if __name__ == "__main__":
    process_csv("data/customers_master.csv")
