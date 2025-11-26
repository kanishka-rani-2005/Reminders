import os
import pandas as pd
from datetime import datetime, timedelta


DATA_DIR = "data"
OUTPUT_FILE = os.path.join(DATA_DIR, "customers_master.csv")
OUTPUT_FILE_SPOKEN = os.path.join(DATA_DIR, "customers_master_spoken.csv")

COLUMN_MAP = {
    "LOAN ACCOUNT NO": "loan_account_number",
    "CUSTOMER NAME": "name",
    "SANCTIONED LOAN AMOUNT": "loan_amount",
    "EFFECTIVE INSTALLMENT AMOUNT": "emi_amount",
    "IFSC Code": "ifsc",
    "Account Last 4 Digits": "account_last4"
}

def process_language_csv(filepath: str, language: str) -> pd.DataFrame:
    df = pd.read_csv(filepath)
    df.rename(columns=COLUMN_MAP, inplace=True)
    df["language"] = language
    next_due = datetime.now().replace(day=5)
    if next_due < datetime.now():
        next_due += timedelta(days=30)
    df["due_date"] = next_due.strftime("%d-%b-%Y")
    df = df[[
        "name", "language", "loan_account_number",
        "loan_amount", "due_date", "ifsc", "account_last4"
    ]]
    return df

def create_master_csv():
    combined = []

    for lang_file in os.listdir(DATA_DIR):
        if lang_file.endswith(".csv") and lang_file not in ["customers_master.csv", "customers_master_spoken.csv"]:
            language = lang_file.replace(".csv", "")
            filepath = os.path.join(DATA_DIR, lang_file)
            print(f"📂 Processing {filepath} ...")
            combined.append(process_language_csv(filepath, language))

    if not combined:
        print("⚠️ No CSV files found in 'data' directory.")
        return

    master_df = pd.concat(combined, ignore_index=True)
    master_df.insert(0, "id", range(1, len(master_df) + 1))

    # Save normal CSV
    master_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Master CSV successfully created at: {OUTPUT_FILE}")



def main():
    print("🚀 Starting preprocessing of language CSVs...\n")
    os.makedirs(DATA_DIR, exist_ok=True)
    create_master_csv()
    print("\n🎯 Processing complete!")


if __name__ == "__main__":
    main()
