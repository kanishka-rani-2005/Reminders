import pandas as pd
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests, logging, sys

# --- Directories ---
ROOT = Path(".")
ASSETS = ROOT / "assets"
TEMPLATES = ASSETS / "templates"
GENERATED = ASSETS / "generated"
FONTS = ASSETS / "fonts"
LOG_PATH = ROOT / "logs" / "card_generation.log"

for d in [GENERATED, FONTS, LOG_PATH.parent]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cards")
console = logging.StreamHandler(sys.stdout)
logger.addHandler(console)

# --- Font URLs ---
FONT_URLS = {
    "english": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf",
    "hindi": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf",
    "tamil": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf",
    "telugu": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTelugu/NotoSansTelugu-Regular.ttf",
    "kannada": "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansKannada/NotoSansKannada-Regular.ttf",
}

def ensure_font(name, url):
    """Download font if not already available."""
    path = FONTS / name
    if not path.exists():
        print(f"Downloading {name}...")
        r = requests.get(url, timeout=30)
        with open(path, "wb") as f:
            f.write(r.content)
    return str(path)

# --- Load fonts ---
FONT_ENGLISH = ImageFont.truetype(ensure_font("NotoSans-Regular.ttf", FONT_URLS["english"]), 28)
FONT_ENGLISH_BOLD = ImageFont.truetype(ensure_font("NotoSans-Regular.ttf", FONT_URLS["english"]), 40)

# --- Colors ---
BLUE = (0, 0, 153)

# --- Template Map ---
TEMPLATE_MAP = {
    "hindi": ["Hindi_Card_1.jpg", "Hindi_Card_2.jpg", "Hindi_Card_3.jpg"],
    "tamil": ["Tamil_Card_1.jpg", "Tamil_Card_2.jpg", "Tamil_Card_3.jpg"],
    "telugu": ["Telugu_Card_1.jpg", "Telugu_Card_2.jpg", "Telugu_Card_3.jpg"],
    "kannada": ["Kannada_Card_1.jpg", "Kannada_Card_2.jpg", "Kannada_Card_3.jpg"],
}

# --- Utility ---
def fmt_cur(v):
    try:
        return f"₹{int(float(v)):,}"
    except:
        return str(v)

# --- Draw text safely ---
def draw_value(draw, pos, text, font=FONT_ENGLISH_BOLD, color=BLUE):
    draw.text(pos, str(text), font=font, fill=color)

# --- Generate Cards ---
def generate_cards(row):
    cid = row.get("id", "unknown")
    lang = (row.get("language") or "hindi").lower().strip()

    templates = TEMPLATE_MAP.get(lang)
    if not templates:
        logger.warning(f"No templates found for {lang}, skipping {cid}")
        return

    name = row.get("name", "")
    loan_account = row.get("loan_account_number", "")
    loan_amount = fmt_cur(row.get("loan_amount", ""))
    emi_amount = fmt_cur(row.get("emi_amount", ""))
    due_date = row.get("due_date", "")
    ifsc = row.get("ifsc", "")
    account_last4 = row.get("account_last4", "")

    # --- Card 1: Loan details ---
    img1 = Image.open(TEMPLATES / templates[0]).convert("RGBA")
    draw = ImageDraw.Draw(img1)
    draw_value(draw, (650, 325), name)
    draw_value(draw, (650, 405), loan_account)
    draw_value(draw, (650, 485), loan_amount)
    img1.save(GENERATED / f"{cid}_loan.png")

    # --- Card 2: EMI details ---
    img2 = Image.open(TEMPLATES / templates[1]).convert("RGBA")
    draw = ImageDraw.Draw(img2)
    draw_value(draw, (750, 277), emi_amount)
    draw_value(draw, (750, 358), due_date)
    draw_value(draw, (750, 430), ifsc)
    draw_value(draw, (750, 510), account_last4)
    img2.save(GENERATED / f"{cid}_emi.png")



# --- Run ---
def main():
    df = pd.read_csv("data/customers_master.csv", dtype=str).fillna("")
    for _, row in df.iterrows():
        generate_cards(row)
    logger.info(f"🎉 All cards saved to {GENERATED}")

if __name__ == "__main__":
    main()
