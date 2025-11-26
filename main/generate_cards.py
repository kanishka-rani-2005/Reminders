import pandas as pd
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import requests, logging, sys, traceback

ROOT = Path(".")
ASSETS = ROOT / "assets"
TEMPLATES = ASSETS / "templates"
GENERATED = ASSETS / "generated"
FONTS = ASSETS / "fonts"
LOG_PATH = ROOT / "logs" / "card_generation.log"


for d in [TEMPLATES, GENERATED, FONTS, LOG_PATH.parent]:
    d.mkdir(parents=True, exist_ok=True)

logging.basicConfig(filename=LOG_PATH, level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("cards")
console = logging.StreamHandler(sys.stdout)
console.setLevel(logging.INFO)
logger.addHandler(console)

FONT_URLS = {
    "english": ("NotoSans-Regular.ttf", "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSans/NotoSans-Regular.ttf"),
    "hindi":   ("NotoSansDevanagari-Regular.ttf", "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansDevanagari/NotoSansDevanagari-Regular.ttf"),
    "tamil":   ("NotoSansTamil-Regular.ttf", "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTamil/NotoSansTamil-Regular.ttf"),
    "telugu":  ("NotoSansTelugu-Regular.ttf", "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansTelugu/NotoSansTelugu-Regular.ttf"),
    "kannada": ("NotoSansKannada-Regular.ttf", "https://github.com/googlefonts/noto-fonts/raw/main/hinted/ttf/NotoSansKannada/NotoSansKannada-Regular.ttf"),
}

def download_font(fname, url):
    p = FONTS / fname
    if p.exists():
        logger.debug(f"Font exists: {p}")
        return p
    try:
        logger.info(f"Downloading font {fname} ...")
        r = requests.get(url, timeout=30); r.raise_for_status()
        p.write_bytes(r.content)
        logger.info(f"Saved font to {p}")
        return p
    except Exception as e:
        logger.exception(f"Failed to download {fname}: {e}")
        return None

FONT_PATHS = {}
for key,(fname,url) in FONT_URLS.items():
    FONT_PATHS[key] = download_font(fname, url)

def load_truetype(path: Path, size: int):
    try:
        if path is None:
            raise RuntimeError("font path is None")
        return ImageFont.truetype(str(path), size)
    except Exception:
        logger.exception(f"Could not load TTF {path} at size {size}; falling back to default font")
        return ImageFont.load_default()

def get_font_for_lang(lang: str, size: int):
    key = (lang or "english").lower()
    path = FONT_PATHS.get(key) or FONT_PATHS.get("english")
    return load_truetype(path, size)

TEMPLATE_MAP = {
    "hindi":   ["Hindi_Card_1.jpg", "Hindi_Card_2.jpg"],
    "tamil":   ["Tamil_Card_1.jpg", "Tamil_Card_2.jpg"],
    "telugu":  ["Telugu_Card_1.jpg", "Telugu_Card_2.jpg"],
    "kannada": ["Kannada_Card_1.jpg", "Kannada_Card_2.jpg"],
    "english": ["English_Card_1.jpg", "English_Card_2.jpg"],
}

def fmt_cur(v):
    try:
        return f"₹{int(float(v)):,}"
    except Exception:
        return str(v or "")

def draw_text_with_outline(draw: ImageDraw.Draw, xy, text, font, fill, stroke_width=1, stroke_fill=(0,0,0)):
    try:
        draw.text(xy, text, font=font, fill=fill, stroke_width=stroke_width, stroke_fill=stroke_fill)
    except TypeError:
        for dx,dy in [(-1,0),(1,0),(0,-1),(0,1)]:
            draw.text((xy[0]+dx, xy[1]+dy), text, font=font, fill=stroke_fill)
        draw.text(xy, text, font=font, fill=fill)

def draw_text_auto_fit(draw: ImageDraw.Draw, text, x, y, max_width, size=34, anchor="lt", fill=(0,0,153)):
    text = str(text or "").strip()
    if not text:
        return None, None

    current_size = size
    while True:
        font = get_font_for_lang("english", current_size)  # force english font for dynamic fields
        bbox = draw.textbbox((x,y), text, font=font, anchor=anchor)
        width = bbox[2] - bbox[0]
        if width <= max_width or current_size <= 10:
            break
        current_size -= 2

    font = get_font_for_lang("english", current_size)
    bbox = draw.textbbox((x,y), text, font=font, anchor=anchor)
    if bbox[2] - bbox[0] > max_width:
        lo, hi = 0, len(text)
        fit = text
        while lo <= hi:
            mid = (lo + hi) // 2
            cand = text[:mid] + ("…" if mid < len(text) else "")
            bbox = draw.textbbox((x,y), cand, font=font, anchor=anchor)
            if bbox[2] - bbox[0] <= max_width:
                fit = cand
                lo = mid + 1
            else:
                hi = mid - 1
        text = fit

    draw_text_with_outline(draw, (x,y), text, font=font, fill=fill, stroke_width=1, stroke_fill=(0,0,0))
    return font, text

def generate_for_row(row):
    cid = row.get("id", "unknown")
    lang = (row.get("language") or "hindi").lower().strip()
    logger.info(f"Processing id={cid} lang={lang}")

    templates = TEMPLATE_MAP.get(lang) or TEMPLATE_MAP.get("english")
    if not templates or len(templates) < 2:
        logger.error(f"Templates for {lang} not defined correctly in TEMPLATE_MAP")
        return

    for t in templates[:2]:
        p = TEMPLATES / t
        if not p.exists():
            logger.error(f"Missing template {p} for id={cid}; SKIPPING this row")
            return

    name = row.get("name") or ""
    loan_account = row.get("loan_account_number") or ""
    loan_amount = fmt_cur(row.get("loan_amount") or "")
    emi_amount_raw = row.get("emi_amount") or row.get("loan_amount") or ""
    emi_amount = fmt_cur(emi_amount_raw)
    due_date = row.get("due_date") or ""
    ifsc = row.get("ifsc") or ""
    account_last4 = row.get("account_last4") or ""

    try:
        img = Image.open(TEMPLATES / templates[0]).convert("RGBA")
    except Exception as e:
        return
    w, h = img.size
    draw = ImageDraw.Draw(img, "RGBA")

    name_box_w = int(w * 0.60)
    name_box_h = int(h * 0.52)
    name_box_left = int(w * 0.15)
    name_box_top = int(h * 0.20)

    acct_box_left = int(w * 0.43)
    acct_box_top = int(h * 0.62)
    acct_box_w = int(w * 0.30)

    loan_box_left = acct_box_left
    loan_box_top = int(h * 0.75)
    loan_box_w = int(w * 0.30)

    cx = name_box_left + name_box_w // 2
    cy = name_box_top + name_box_h // 2
    draw_text_auto_fit(draw, name, cx, cy, max_width=name_box_w,
                       size=max(20, int(h*0.07)), anchor="lt", fill=(0,0,151))

    draw_text_auto_fit(
    draw,
    loan_account,
    acct_box_left + 6,
    acct_box_top ,
    max_width=name_box_w,
    size=max(20, int(h * 0.02)), 
    anchor="lt",
    fill=(0,0,151)
)
    draw_text_auto_fit(draw, loan_amount, loan_box_left + 6, loan_box_top + 6,
                       max_width=loan_box_w - 12, size=max(16, int(h*0.08)), anchor="lt", fill=(0,0,151))

    loan_path = GENERATED / f"{cid}_loan.png"
    img.save(loan_path)
    logger.info(f"Wrote final loan image: {loan_path}")

    try:
        img2 = Image.open(TEMPLATES / templates[1]).convert("RGBA")
    except Exception as e:
        logger.exception(f"Failed to open template {templates[1]}: {e}")
        return
    w2, h2 = img2.size
    draw2 = ImageDraw.Draw(img2, "RGBA")

    emi_box_left = int(w2 * 0.45)
    emi_box_top = int(h2 * 0.38)
    emi_box_w = int(w2 * 0.30)
    emi_box_h = max(28, int(h2 * 0.20))

    due_box_left = emi_box_left
    due_box_top = int(h2 * 0.52)
    due_box_w = emi_box_w
    due_box_h = max(20, int(h2 * 0.12))

    ifsc_box_left = emi_box_left
    ifsc_box_top = int(h2 * 0.68)
    ifsc_box_w = emi_box_w
    ifsc_box_h = max(20, int(h2 * 0.12))

    acc4_box_left = emi_box_left
    acc4_box_top = int(h2 * 0.79)
    acc4_box_w = int(w2 * 0.48)
    acc4_box_h = max(20, int(h2 * 0.12))

    draw_text_auto_fit(draw2, emi_amount, emi_box_left + 8, emi_box_top + 8,
                       max_width=emi_box_w - 16, size=max(12,int(h2*0.08)), anchor="lt", fill=(0,0,153))
    draw_text_auto_fit(draw2, due_date, due_box_left + 8, due_box_top + 6,
                       max_width=due_box_w - 16, size=max(12,int(h2*0.08)), anchor="lt", fill=(0,0,153))
    draw_text_auto_fit(draw2, ifsc, ifsc_box_left + 8, ifsc_box_top + 6,
                       max_width=ifsc_box_w - 16, size=max(12,int(h2*0.08)), anchor="lt", fill=(0,0,153))
    draw_text_auto_fit(draw2, account_last4, acc4_box_left + 8, acc4_box_top + 6,
                       max_width=acc4_box_w - 12, size=max(12,int(h2*0.08)), anchor="lt", fill=(0,0,153))

    emi_out = GENERATED / f"{cid}_emi.png"
    img2.save(emi_out)
    logger.info(f"Wrote final EMI image: {emi_out}")

def main():
    try:
        df = pd.read_csv("data/customers_master.csv", dtype=str).fillna("")
    except Exception as e:
        logger.exception(f"Failed to read CSV: {e}")
        return
    logger.info(f"Loaded {len(df)} rows from data/customers_master.csv")
    for _, row in df.iterrows():
        try:
            generate_for_row(row)
        except Exception:
            logger.exception("Unhandled error while processing row:\n" + traceback.format_exc())
    logger.info("All done. Check assets/generated/ and logs/card_generation.log")

if __name__ == "__main__":
    main()
