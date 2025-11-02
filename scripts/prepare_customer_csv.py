# import pandas as pd, os, re, datetime, logging, traceback

# RAW_PATH = "data/customers_raw.csv"
# OUT_PATH = "data/customers_master.csv"
# LOG_PATH = "logs/data_validation.log"

# # Create necessary folders
# os.makedirs("logs", exist_ok=True)

# # Configure logging
# logging.basicConfig(
#     filename=LOG_PATH,
#     level=logging.INFO,
#     format="%(asctime)s [%(levelname)s] %(message)s"
# )

# def validate_phone(phone):
#     """Validate and auto-fix Indian phone numbers."""
#     phone = str(phone).strip().replace(" ", "").replace("\u202f", "").replace("\xa0", "")
#     if phone.startswith("91") and not phone.startswith("+91"):
#         phone = "+" + phone
#     if re.match(r"^\+91\d{10}$", phone):
#         return True, phone
#     return False, phone

# def validate_date(date_str):
#     try:
#         datetime.datetime.strptime(date_str, "%d-%b-%Y")
#         return True
#     except Exception:
#         return False

# def prepare_customer_csv():
#     try:
#         logging.info("=== Starting Data Preparation ===")
#         print(f"📥 Reading {RAW_PATH} ...")

#         if not os.path.exists(RAW_PATH):
#             logging.error(f"❌ File not found: {RAW_PATH}")
#             print(f"❌ File not found: {RAW_PATH}")
#             return

#         df = pd.read_csv(RAW_PATH)
#         logging.info(f"File loaded successfully: {RAW_PATH} ({len(df)} rows)")
#         df.columns = [c.strip().lower() for c in df.columns]
#         print("Columns:", list(df.columns))
#         logging.info(f"Columns detected: {list(df.columns)}")

#         required_cols = [
#             "id","name","language","loan_amount","emi_amount","due_date",
#             "bank_name","branch_name","ifsc","phone_number"
#         ]
#         for col in required_cols:
#             if col not in df.columns:
#                 df[col] = ""
#                 logging.warning(f"Missing column '{col}' added as empty")

#         valid_langs = {"hindi", "tamil", "telugu", "kannada"}
#         valid_rows = []

#         for _, r in df.iterrows():
#             errors = []

#             if not isinstance(r["name"], str) or not r["name"].replace(" ", "").isalpha():
#                 errors.append("Invalid name")

#             if str(r["language"]).lower() not in valid_langs:
#                 errors.append(f"Invalid language ({r['language']})")

#             if not str(r["loan_amount"]).isdigit() or int(r["loan_amount"]) <= 0:
#                 errors.append("Invalid loan_amount")

#             if not str(r["emi_amount"]).isdigit() or int(r["emi_amount"]) <= 0:
#                 errors.append("Invalid emi_amount")

#             if not validate_date(str(r["due_date"])):
#                 errors.append(f"Invalid due_date ({r['due_date']})")

#             ok_phone, fixed_phone = validate_phone(r["phone_number"])
#             if not ok_phone:
#                 errors.append(f"Invalid phone_number ({r['phone_number']})")
#             else:
#                 r["phone_number"] = fixed_phone

#             if errors:
#                 print(f"❌ Row {r.get('id', '?')} skipped → {errors}")
#                 logging.info(f"Row {r.get('id', '?')} skipped: {errors}")
#                 continue

#             valid_rows.append(r)

#         clean_df = pd.DataFrame(valid_rows)
#         clean_df.to_csv(OUT_PATH, index=False)
#         print(f"✅ Cleaned CSV saved: {OUT_PATH} ({len(clean_df)} valid rows)")
#         logging.info(f"✅ Cleaned CSV saved successfully ({len(clean_df)} valid rows)")
#         logging.info("=== Data Preparation Completed ===")

#     except Exception as e:
#         print("❌ Unexpected error occurred. Check logs for details.")
#         logging.error(f"Unhandled exception: {e}")
#         logging.error(traceback.format_exc())

# if __name__ == "__main__":
#     prepare_customer_csv()
