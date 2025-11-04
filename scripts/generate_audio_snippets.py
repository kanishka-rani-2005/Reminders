import pandas as pd
import os
import requests

# ==================================================
# 🗣️ STEP 1: Generate Speech Function
# ==================================================
def generate_speech(text, lang_code, output_path):
    ELEVEN_API_KEY = "sk_f69d64ab5822565596479fab3500a503cf72a50a133794ba"   # Replace safely
    MODEL_ID = "eleven_multilingual_v2"
    VOICE_ID = "21m00Tcm4TlvDq8ikWAM"  # Multilingual voice

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
# 💬 STEP 2: Two-sentence dynamic text
# ==================================================
def make_two_segments(row):
    name = row["name"]
    loan_no = row["loan_account_number"]
    loan_amount = row["loan_amount"]
    emi_amount = row["emi_amount"]
    due_date = row["due_date"]
    ifsc = row["ifsc"]
    last4 = str(row.get("account_last4", "XXXX"))
    lang = row["language"].strip().lower()

    templates = {
        "hindi": [
            f"प्रिय {name}, आपका लोन नंबर {loan_no} है, जिसकी स्वीकृत राशि {loan_amount} है।",
            f" आपकी मासिक ईएमआई {emi_amount} निर्धारित की गई है, जिसकी अगली देय तिथि {due_date} है। आपका बैंक खाता, जिसका अंतिम चार अंक {last4} हैं, और IFSC कोड {ifsc} है, से यह राशि स्वतः काटी जाएगी।"
        ],

        "tamil": [
            f"அன்புடையீர் {name}, உங்கள் கடன் எண் {loan_no}, கடன் தொகை {loan_amount} ரூபாய்.",
            f" மாதாந்திர EMI {emi_amount} ரூபாய், கடைசி தேதி {due_date}. உங்கள் வங்கி கணக்கு (கடைசி நான்கு இலக்கங்கள் {last4}) மற்றும் IFSC குறியீடு {ifsc} இலிருந்து இந்த தொகை தானாகக் கழிக்கப்படும்."
        ],

        "telugu": [
            f"ప్రియమైన {name}, మీ రుణ సంఖ్య {loan_no}, మొత్తం {loan_amount} రూపాయలు.",
            f" మీ EMI {emi_amount} రూపాయలు, గడువు తేదీ {due_date}. మీ బ్యాంక్ ఖాతా చివరి నాలుగు అంకెలు {last4}, IFSC కోడ్ {ifsc} నుండి ఈ మొత్తం స్వయంగా తీసుకోబడుతుంది."
        ],

        "kannada": [
            f"ಆದರನೀಯ {name}, ನಿಮ್ಮ ಸಾಲ ಸಂಖ್ಯೆ {loan_no}, ಸಾಲ ಮೊತ್ತ {loan_amount} ರೂಪಾಯಿ.",
            f" ನಿಮ್ಮ ಇಎಂಐ {emi_amount} ರೂಪಾಯಿ ಆಗಿದ್ದು, ಪಾವತಿ ದಿನಾಂಕ {due_date}. ನಿಮ್ಮ ಬ್ಯಾಂಕ್ ಖಾತೆಯ ಕೊನೆಯ ನಾಲ್ಕು ಅಂಕೆಗಳು {last4}, IFSC ಕೋಡ್ {ifsc} ಇಂದ ಈ ಮೊತ್ತ ಸ್ವಯಂಚಾಲಿತವಾಗಿ ಕಡಿತಗೊಳ್ಳುತ್ತದೆ."
        ],

        "english": [
            f"Dear {name}, your loan number is {loan_no} with a sanctioned amount of {loan_amount} rupees.",
            f" Your monthly EMI is {emi_amount}, due on {due_date}. The amount will be auto-debited from your bank account ending with {last4}, having IFSC code {ifsc}."
        ],
    }

    return templates.get(lang, templates["english"]), lang


# ==================================================
# 🧩 STEP 3: Process CSV and Generate 2 Audio Clips
# ==================================================
def process_csv(csv_path, output_dir="output_2clips"):
    os.makedirs(output_dir, exist_ok=True)
    df = pd.read_csv(csv_path)

    for _, row in df.iterrows():
        segments, lang = make_two_segments(row)
        cid = str(row["id"])
        customer_dir = os.path.join(output_dir, f"{cid}_{lang}")
        os.makedirs(customer_dir, exist_ok=True)

        print(f"\n🎙️ Generating 2 audio clips for {row['name']} ({lang})...")

        for i, text in enumerate(segments, start=1):
            file_path = os.path.join(customer_dir, f"{i:02d}_{lang}.mp3")
            generate_speech(text, lang, file_path)


# ==================================================
# 🚀 MAIN
# ==================================================
if __name__ == "__main__":
    process_csv("data/customers_master_spoken.csv")
