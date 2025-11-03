import os
import pandas as pd
from datetime import datetime, timedelta


DATA_DIR = "data"   # Folder containing all language CSVs
OUTPUT_FILE = os.path.join(DATA_DIR, "customers_master.csv")

# Map original column names to standardized names
COLUMN_MAP = {
    "LOAN ACCOUNT NO": "loan_account_number",
    "CUSTOMER NAME": "name",
    "SANCTIONED LOAN AMOUNT": "loan_amount",
    "EFFECTIVE INSTALLMENT AMOUNT": "emi_amount",
    "IFSC Code": "ifsc",
    "Account Last 4 Digits": "account_last4"
}


# ============================================
# FUNCTION: Process a single language CSV
# ============================================
def process_language_csv(filepath: str, language: str) -> pd.DataFrame:
    """Reads and standardizes a language CSV file."""
    df = pd.read_csv(filepath)

    # Rename columns to standardized names
    df.rename(columns=COLUMN_MAP, inplace=True)

    # Add language column
    df["language"] = language

    # Add next 5th of month as due date
    next_due = datetime.now().replace(day=5)
    if next_due < datetime.now():
        next_due += timedelta(days=30)
    df["due_date"] = next_due.strftime("%d-%b-%Y")

    # Keep only relevant columns (in desired order)
    df = df[[
        "name", "language", "loan_account_number",
        "loan_amount", "emi_amount", "due_date", "ifsc", "account_last4"
    ]]
    return df


# ============================================
# FUNCTION: Merge all CSVs into one master file
# ============================================
def create_master_csv():
    combined = []

    for lang_file in os.listdir(DATA_DIR):
        if lang_file.endswith(".csv") and lang_file != "customers_master.csv":
            language = lang_file.replace(".csv", "")
            filepath = os.path.join(DATA_DIR, lang_file)
            print(f"📂 Processing {filepath} ...")
            combined.append(process_language_csv(filepath, language))

    if not combined:
        print("⚠️ No CSV files found in 'data' directory.")
        return

    master_df = pd.concat(combined, ignore_index=True)

    # Add incremental ID
    master_df.insert(0, "id", range(1, len(master_df) + 1))

    # Save to master CSV
    master_df.to_csv(OUTPUT_FILE, index=False)
    print(f"\n✅ Master CSV successfully created at: {OUTPUT_FILE}")


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
