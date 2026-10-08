"""
Step 1: Clean the Retail Store Sales dataset with pandas.

Input : data/raw/retail_store_sales.csv
Output: data/processed/cleaned_data.csv

Run from the project root:  python src/01_clean_data.py
"""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
INPUT_FILE = ROOT / "data" / "raw" / "retail_store_sales.csv"
OUTPUT_FILE = ROOT / "data" / "processed" / "cleaned_data.csv"

# ---------------------------------------------------------------
# 1. LOAD THE DATA
# ---------------------------------------------------------------
df = pd.read_csv(INPUT_FILE)
raw_rows = len(df)
print(f"Raw shape: {df.shape}")

# ---------------------------------------------------------------
# 2. STANDARDIZE COLUMN NAMES
# "Price Per Unit" -> "price_per_unit": no spaces or capitals,
# which makes SQL queries cleaner.
# ---------------------------------------------------------------
df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

# ---------------------------------------------------------------
# 3. REMOVE DUPLICATES
# Check full-row duplicates AND repeated transaction IDs
# (a transaction ID should be unique).
# ---------------------------------------------------------------
df = df.drop_duplicates()
df = df.drop_duplicates(subset="transaction_id")
print(f"Duplicates removed: {raw_rows - len(df)}")

# ---------------------------------------------------------------
# 4. CLEAN TEXT COLUMNS
# Strip stray spaces and make casing consistent so "Online " and
# "online" are never treated as different values.
# ---------------------------------------------------------------
text_cols = ["transaction_id", "customer_id", "category", "item",
             "payment_method", "location"]
for col in text_cols:
    df[col] = df[col].astype("string").str.strip()

for col in ["category", "payment_method", "location"]:
    # Title case, but keep small words like "and" lowercase
    df[col] = df[col].str.title().str.replace(r"\bAnd\b", "and", regex=True)

# ---------------------------------------------------------------
# 5. FIX DATA TYPES
# errors="coerce" turns unparseable values into NaT/NaN instead of
# crashing, so we can handle them explicitly.
# ---------------------------------------------------------------
df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
for col in ["price_per_unit", "quantity", "total_spent"]:
    df[col] = pd.to_numeric(df[col], errors="coerce")

# ---------------------------------------------------------------
# 6. HANDLE MISSING VALUES (recover, don't just delete)
# ---------------------------------------------------------------
missing_before = df.isna().sum()

# Lookup 1: every item has exactly one price
item_price = (df.dropna(subset=["item", "price_per_unit"])
                .drop_duplicates("item")
                .set_index("item")["price_per_unit"])

# Lookup 2: within a category, every price belongs to exactly one item
cat_price_item = (df.dropna(subset=["item", "price_per_unit"])
                    .drop_duplicates(["category", "price_per_unit"])
                    .set_index(["category", "price_per_unit"])["item"])


def fill_price_and_item(frame: pd.DataFrame) -> None:
    """Fill missing price from item, and missing item from (category, price)."""
    m = frame["price_per_unit"].isna() & frame["item"].notna()
    frame.loc[m, "price_per_unit"] = frame.loc[m, "item"].map(item_price)

    m = frame["item"].isna() & frame["price_per_unit"].notna()
    keys = list(zip(frame.loc[m, "category"], frame.loc[m, "price_per_unit"]))
    frame.loc[m, "item"] = pd.Series(keys, index=frame.loc[m].index).map(cat_price_item)


fill_price_and_item(df)

# total_spent = price_per_unit * quantity.
# If exactly one of the three is missing, compute it from the other two.
m = df["total_spent"].isna() & df["price_per_unit"].notna() & df["quantity"].notna()
df.loc[m, "total_spent"] = df["price_per_unit"] * df["quantity"]

m = df["quantity"].isna() & df["price_per_unit"].notna() & df["total_spent"].notna()
df.loc[m, "quantity"] = df["total_spent"] / df["price_per_unit"]

m = df["price_per_unit"].isna() & df["quantity"].notna() & df["total_spent"].notna()
df.loc[m, "price_per_unit"] = df["total_spent"] / df["quantity"]

# Newly recovered prices may unlock more item names
fill_price_and_item(df)

# Rows where revenue can't be reconstructed are useless -> drop
before = len(df)
df = df.dropna(subset=["price_per_unit", "quantity", "total_spent"])
print(f"Rows dropped (unrecoverable revenue columns): {before - len(df)}")

# discount_applied: truth is unknowable, so label it instead of guessing
df["discount_applied"] = (df["discount_applied"]
                          .map({True: "Yes", False: "No", "True": "Yes", "False": "No"})
                          .fillna("Unknown"))
df["item"] = df["item"].fillna("Unknown Item")

# ---------------------------------------------------------------
# 7. FINAL TYPES + VALIDATION
# ---------------------------------------------------------------
df["quantity"] = df["quantity"].round().astype(int)
df["total_spent"] = df["total_spent"].round(2)

assert df["transaction_id"].is_unique
assert (df["quantity"] > 0).all() and (df["price_per_unit"] > 0).all()
assert ((df["price_per_unit"] * df["quantity"] - df["total_spent"]).abs() < 0.01).all()
assert df["transaction_date"].notna().all()

# ---------------------------------------------------------------
# 8. ADD HELPER COLUMNS FOR SQL
# ---------------------------------------------------------------
df["year"] = df["transaction_date"].dt.year
df["month"] = df["transaction_date"].dt.month
df["year_month"] = df["transaction_date"].dt.strftime("%Y-%m")

# ---------------------------------------------------------------
# 9. SAVE
# ---------------------------------------------------------------
df = df.sort_values("transaction_date").reset_index(drop=True)
df.to_csv(OUTPUT_FILE, index=False)

print("\nMissing values BEFORE cleaning:")
print(missing_before[missing_before > 0].to_string())
print(f"\nMissing values AFTER cleaning: {int(df.isna().sum().sum())}")
print(f"Clean shape: {df.shape}  (kept {len(df) / raw_rows:.1%} of rows)")
print(f"Saved to: {OUTPUT_FILE}")
