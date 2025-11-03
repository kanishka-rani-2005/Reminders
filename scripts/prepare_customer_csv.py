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
    """Reads and standardizes a language CSV file."""
    df = pd.read_csv(filepath)

    df.rename(columns=COLUMN_MAP, inplace=True)
    df["language"] = language

    # Add next 5th of month as due date
    next_due = datetime.now().replace(day=5)
    if next_due < datetime.now():
        next_due += timedelta(days=30)
    df["due_date"] = next_due.strftime("%d-%b-%Y")

    df = df[[
        "name", "language", "loan_account_number",
        "loan_amount", "due_date", "ifsc", "account_last4"
    ]]
    return df


def make_spoken_version(df: pd.DataFrame) -> pd.DataFrame:
    df_spoken = df.copy()

    def hyphenate_value(x):
        s = str(x).strip()
        if s == "" or s.lower() == "nan":
            return s

        # For numeric or alphanumeric strings → separate all characters
        return "-".join(list(s))

    # Apply to selected columns
    for col in ["loan_account_number", "emi_amount", "account_last4", "ifsc"]:
        if col in df_spoken.columns:
            df_spoken[col] = df_spoken[col].astype(str).apply(hyphenate_value)

    return df_spoken


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

    # Save spoken-friendly version
    spoken_df = make_spoken_version(master_df)
    spoken_df.to_csv(OUTPUT_FILE_SPOKEN, index=False)
    print(f"🔉 Spoken-friendly CSV created at: {OUTPUT_FILE_SPOKEN}")


# ============================================
# MAIN EXECUTION
# ============================================
def main():
    print("🚀 Starting preprocessing of language CSVs...\n")
    os.makedirs(DATA_DIR, exist_ok=True)
    create_master_csv()
    print("\n🎯 Processing complete!")


if __name__ == "__main__":
    main()
