"""
Step 2: Load the cleaned CSV into a SQLite database with an enforced schema.

Input : data/processed/cleaned_data.csv
Output: data/processed/retail_sales.db

Run from the project root:  python src/02_load_to_sqlite.py
"""
import sqlite3
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
CSV_FILE = ROOT / "data" / "processed" / "cleaned_data.csv"
DB_FILE = ROOT / "data" / "processed" / "retail_sales.db"

# 1. Read the cleaned CSV. Store dates as ISO text (YYYY-MM-DD):
#    SQLite has no date type, and ISO text sorts/filters correctly.
df = pd.read_csv(CSV_FILE, parse_dates=["transaction_date"])
df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")

# 2. Start fresh so re-running never duplicates rows
DB_FILE.unlink(missing_ok=True)

# 3. Connect (SQLite ships with Python; the database is one file)
conn = sqlite3.connect(DB_FILE)
cur = conn.cursor()

# 4. Explicit schema: PRIMARY KEY, NOT NULL and CHECK rules protect data quality
cur.execute("""
CREATE TABLE sales (
    transaction_id   TEXT PRIMARY KEY,
    customer_id      TEXT    NOT NULL,
    category         TEXT    NOT NULL,
    item             TEXT    NOT NULL,
    price_per_unit   REAL    NOT NULL CHECK (price_per_unit > 0),
    quantity         INTEGER NOT NULL CHECK (quantity > 0),
    total_spent      REAL    NOT NULL CHECK (total_spent > 0),
    payment_method   TEXT    NOT NULL,
    location         TEXT    NOT NULL,
    transaction_date TEXT    NOT NULL,
    discount_applied TEXT    NOT NULL CHECK (discount_applied IN ('Yes','No','Unknown')),
    year             INTEGER NOT NULL,
    month            INTEGER NOT NULL,
    year_month       TEXT    NOT NULL
);
""")

# 5. Insert (append keeps our schema instead of letting pandas replace it)
df.to_sql("sales", conn, if_exists="append", index=False)

# 6. Indexes speed up filtering/grouping on large data
for col in ["transaction_date", "category", "item", "customer_id"]:
    cur.execute(f"CREATE INDEX idx_sales_{col} ON sales({col});")
conn.commit()

# 7. Verify the load
db_rows = cur.execute("SELECT COUNT(*) FROM sales").fetchone()[0]
db_revenue = cur.execute("SELECT ROUND(SUM(total_spent), 2) FROM sales").fetchone()[0]
assert db_rows == len(df), "Row count mismatch!"
assert abs(db_revenue - round(df["total_spent"].sum(), 2)) < 0.01, "Revenue mismatch!"

print(f"Rows in database : {db_rows:,}")
print(f"Total revenue    : {db_revenue:,.2f}")
print(f"Saved to         : {DB_FILE}")
conn.close()
