"""
Steps 3 & 4: Run the SQL queries and visualize the results.

Input : data/processed/retail_sales.db, sql/queries.sql
Output: results/*.csv (one per query) and charts/*.png

Run from the project root:  python src/03_run_analysis.py
"""
import re
import sqlite3
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # draw charts to files, no window needed
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
DB_FILE = ROOT / "data" / "processed" / "retail_sales.db"
SQL_FILE = ROOT / "sql" / "queries.sql"
RESULTS_DIR = ROOT / "results"
CHARTS_DIR = ROOT / "charts"

# ---------------------------------------------------------------
# 1. RUN EVERY QUERY IN queries.sql AND SAVE THE RESULT AS CSV
# The "-- name: xyz" comment above each query is its label.
# ---------------------------------------------------------------
conn = sqlite3.connect(DB_FILE)
parts = re.split(r"^-- name: (\w+)\s*$", SQL_FILE.read_text(), flags=re.M)
results = {}
for name, body in zip(parts[1::2], parts[2::2]):
    results[name] = pd.read_sql(body.strip(), conn)
    results[name].to_csv(RESULTS_DIR / f"{name}.csv", index=False)
    print(f"{name:35} -> {len(results[name]):>3} rows")
conn.close()

# ---------------------------------------------------------------
# 2. CHART STYLE (one consistent, clean look)
# ---------------------------------------------------------------
BLUE, ORANGE, GREY, DARK = "#2563EB", "#F59E0B", "#9CA3AF", "#111827"
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.edgecolor": "#D1D5DB",
    "axes.titleweight": "bold",
    "axes.titlesize": 13,
    "axes.titlelocation": "left",
    "axes.labelcolor": "#374151",
    "xtick.color": "#374151",
    "ytick.color": "#374151",
    "figure.facecolor": "white",
})


def k_format(x, _=None):
    """40000 -> '40k' for readable axis labels."""
    return "0" if x == 0 else f"{x / 1000:.0f}k"


# ---------------------------------------------------------------
# 3. CHART FUNCTIONS (each draws onto a given axis so we can reuse
#    them for both the single charts and the dashboard)
# ---------------------------------------------------------------
def chart_top_products(ax):
    d = results["q1_top_10_products_by_revenue"].iloc[::-1]  # biggest on top
    bars = ax.barh(d["item"], d["revenue"], color=BLUE)
    ax.bar_label(bars, labels=[f"{v:,.0f}" for v in d["revenue"]], padding=4, fontsize=9)
    ax.set_title("Top 10 products by revenue")
    ax.set_xlabel("Revenue")
    ax.xaxis.set_major_formatter(k_format)
    ax.set_xlim(0, d["revenue"].max() * 1.15)


def chart_monthly_trend(ax):
    d = results["q2_monthly_sales_trend"].copy()
    d = d[d["year_month"] < "2025-01"]  # Jan 2025 is partial (data ends Jan 18)
    d["date"] = pd.to_datetime(d["year_month"] + "-01")
    ax.plot(d["date"], d["revenue"], color=BLUE, linewidth=2, marker="o", markersize=3.5)
    # Highlight every January: it is consistently the strongest month
    jan = d[d["date"].dt.month == 1]
    ax.scatter(jan["date"], jan["revenue"], color=ORANGE, s=60, zorder=3, label="January")
    ax.axhline(d["revenue"].mean(), color=GREY, linestyle="--", linewidth=1,
               label=f"Average ({d['revenue'].mean() / 1000:.1f}k)")
    ax.set_title("Monthly revenue, Jan 2022 – Dec 2024")
    ax.set_ylabel("Revenue")
    ax.yaxis.set_major_formatter(k_format)
    ax.legend(frameon=False, fontsize=9, loc="lower right")


def chart_category(ax):
    d = results["q3_sales_by_category"].iloc[::-1]
    bars = ax.barh(d["category"], d["revenue"], color=BLUE)
    labels = [f"{r:,.0f}  ({s:.1f}%)" for r, s in zip(d["revenue"], d["revenue_share_pct"])]
    ax.bar_label(bars, labels=labels, padding=4, fontsize=9)
    ax.set_title("Revenue by category (share of total)")
    ax.set_xlabel("Revenue")
    ax.xaxis.set_major_formatter(k_format)
    ax.set_xlim(0, d["revenue"].max() * 1.3)


def chart_aov(ax):
    ch = results["q5_average_order_value"].query("segment != 'All orders'")
    dc = results["q8_discount_impact"].query("discount_applied != 'Unknown'")
    labels = [f"{s}\norders" for s in ch["segment"]] + [
        f"Discount:\n{s}" for s in dc["discount_applied"]]
    values = list(ch["avg_order_value"]) + list(dc["avg_order_value"])
    colors = [BLUE] * len(ch) + [ORANGE] * len(dc)
    bars = ax.bar(labels, values, color=colors)
    ax.bar_label(bars, labels=[f"{v:.1f}" for v in values], padding=3, fontsize=9)
    ax.set_title("Average order value: channel & discount")
    ax.set_ylabel("Avg order value")
    ax.set_ylim(0, max(values) * 1.2)
    ax.tick_params(axis="x", labelsize=8.5)


CHARTS = {
    "01_top_10_products.png": (chart_top_products, (9, 5.5)),
    "02_monthly_sales_trend.png": (chart_monthly_trend, (10, 5)),
    "03_revenue_by_category.png": (chart_category, (10, 5.5)),
    "04_avg_order_value.png": (chart_aov, (9, 5)),
}

# ---------------------------------------------------------------
# 4. SAVE EACH CHART AS ITS OWN IMAGE
# ---------------------------------------------------------------
for filename, (func, size) in CHARTS.items():
    fig, ax = plt.subplots(figsize=size)
    func(ax)
    fig.tight_layout()
    fig.savefig(CHARTS_DIR / filename, dpi=160)
    plt.close(fig)
    print(f"Saved chart: {filename}")

# ---------------------------------------------------------------
# 5. DASHBOARD: all key charts in one image (great as a portfolio
#    thumbnail or Fiverr/Upwork gig cover)
# ---------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(16, 10))
chart_top_products(axes[0, 0])
chart_monthly_trend(axes[0, 1])
chart_category(axes[1, 0])
chart_aov(axes[1, 1])
fig.suptitle("Retail Sales Dashboard  |  11,971 orders  •  Jan 2022 – Jan 2025",
             fontsize=18, fontweight="bold", x=0.01, ha="left", color=DARK)
fig.tight_layout(rect=(0, 0, 1, 0.95))
fig.savefig(CHARTS_DIR / "00_dashboard.png", dpi=140)
plt.close(fig)
print("Saved chart: 00_dashboard.png")
