"""Simple AI Business Strategy & Executive Decision Platform.

Run with:
    uvicorn app:app --reload
"""

import io
import os
from collections import Counter
from pathlib import Path
from typing import Optional

import pandas as pd
from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from google import genai
from pydantic import BaseModel
from pypdf import PdfReader


# ------------------------------------------------------------
# 1. BASIC APP SETUP
# ------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent


def load_simple_env(env_path):
    """Load KEY=VALUE lines without requiring an extra package."""
    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            os.environ.setdefault(key.strip(), value.strip())


load_simple_env(BASE_DIR / ".env")

app = FastAPI(title="AI Business Decision Platform")
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# This keeps the latest analysis available for scenario and chat questions.
# It is intentionally simple for a student project.
LATEST_ANALYSIS = {}


# ------------------------------------------------------------
# 2. HELPER FUNCTIONS
# ------------------------------------------------------------
def safe_number(value):
    """Convert NumPy values into normal Python numbers for JSON."""
    if pd.isna(value):
        return 0
    return float(value)


def percentage_change(current, previous):
    """Calculate percentage change without division-by-zero errors."""
    if previous == 0:
        return 0.0
    return round(((current - previous) / previous) * 100, 2)


def prepare_sales(file_bytes):
    """Read, validate and clean the uploaded sales CSV."""
    try:
        sales = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as error:
        raise HTTPException(400, f"Could not read sales CSV: {error}")

    required = {
        "Date", "Region", "Product", "Category", "Revenue",
        "Cost", "Profit", "Orders", "Customers"
    }
    missing = required - set(sales.columns)
    if missing:
        raise HTTPException(400, f"Missing sales columns: {', '.join(sorted(missing))}")

    sales["Date"] = pd.to_datetime(sales["Date"], errors="coerce")
    numeric_columns = ["Revenue", "Cost", "Profit", "Orders", "Customers"]
    for column in numeric_columns:
        sales[column] = pd.to_numeric(sales[column], errors="coerce")

    sales = sales.dropna(subset=["Date", *numeric_columns]).drop_duplicates()
    if sales.empty:
        raise HTTPException(400, "The sales CSV has no valid records.")

    return sales


def calculate_sales_analysis(sales):
    """Calculate KPIs, trends, comparisons and anomalies."""
    revenue = sales["Revenue"].sum()
    profit = sales["Profit"].sum()
    cost = sales["Cost"].sum()
    orders = sales["Orders"].sum()
    customers = sales["Customers"].sum()

    kpis = {
        "total_revenue": safe_number(revenue),
        "total_profit": safe_number(profit),
        "total_cost": safe_number(cost),
        "total_orders": int(orders),
        "total_customers": int(customers),
        "average_order_value": round(safe_number(revenue / orders), 2) if orders else 0,
        "profit_margin": round(safe_number((profit / revenue) * 100), 2) if revenue else 0,
    }

    monthly = (
        sales.assign(Month=sales["Date"].dt.to_period("M").astype(str))
        .groupby("Month", as_index=False)[["Revenue", "Profit", "Orders"]]
        .sum()
        .sort_values("Month")
    )

    latest = monthly.iloc[-1]
    previous = monthly.iloc[-2] if len(monthly) > 1 else latest
    comparison = {
        "current_period": latest["Month"],
        "previous_period": previous["Month"],
        "revenue_change": percentage_change(latest["Revenue"], previous["Revenue"]),
        "profit_change": percentage_change(latest["Profit"], previous["Profit"]),
        "orders_change": percentage_change(latest["Orders"], previous["Orders"]),
    }

    # Flag monthly revenue changes greater than 20% as easy-to-explain anomalies.
    monthly["Revenue_Change"] = monthly["Revenue"].pct_change() * 100
    anomaly_rows = monthly[monthly["Revenue_Change"].abs() > 20]
    anomalies = [
        {
            "period": row["Month"],
            "change": round(row["Revenue_Change"], 2),
            "message": f"Revenue changed by {row['Revenue_Change']:.1f}% in {row['Month']}.",
        }
        for _, row in anomaly_rows.iterrows()
    ]

    region = (
        sales.groupby("Region", as_index=False)[["Revenue", "Profit"]]
        .sum().sort_values("Revenue", ascending=False)
    )
    product = (
        sales.groupby("Product", as_index=False)[["Revenue", "Profit", "Orders"]]
        .sum().sort_values("Revenue", ascending=False)
    )

    return {
        "kpis": kpis,
        "comparison": comparison,
        "anomalies": anomalies,
        "monthly": monthly[["Month", "Revenue", "Profit", "Orders"]].to_dict("records"),
        "regions": region.to_dict("records"),
        "products": product.to_dict("records"),
    }


POSITIVE_WORDS = {
    "excellent", "good", "great", "fast", "easy", "reliable",
    "attractive", "exceeded", "simple", "value"
}
NEGATIVE_WORDS = {
    "bad", "delayed", "late", "damaged", "poor", "slow", "unclear",
    "problem", "lower", "stopped", "inconvenience", "expensive"
}
THEMES = ["delivery", "battery", "packaging", "support", "price", "quality", "tracking", "setup"]


def sentiment_label(text):
    """A small rule-based sentiment method with no ML download required."""
    words = set(str(text).lower().replace(".", "").replace(",", "").split())
    score = len(words & POSITIVE_WORDS) - len(words & NEGATIVE_WORDS)
    if score > 0:
        return "Positive"
    if score < 0:
        return "Negative"
    return "Neutral"


def analyze_feedback(file_bytes):
    """Read feedback CSV and calculate sentiment and common themes."""
    if not file_bytes:
        return {"total": 0, "average_rating": 0, "sentiment": {}, "themes": []}

    try:
        feedback = pd.read_csv(io.BytesIO(file_bytes))
    except Exception as error:
        raise HTTPException(400, f"Could not read feedback CSV: {error}")

    required = {"Rating", "Feedback"}
    missing = required - set(feedback.columns)
    if missing:
        raise HTTPException(400, f"Missing feedback columns: {', '.join(sorted(missing))}")

    feedback["Rating"] = pd.to_numeric(feedback["Rating"], errors="coerce")
    feedback = feedback.dropna(subset=["Rating", "Feedback"]).drop_duplicates()
    feedback["Sentiment"] = feedback["Feedback"].apply(sentiment_label)

    counts = feedback["Sentiment"].value_counts().to_dict()
    theme_counter = Counter()
    all_feedback = " ".join(feedback["Feedback"].astype(str)).lower()
    for theme in THEMES:
        theme_counter[theme] = all_feedback.count(theme)

    return {
        "total": int(len(feedback)),
        "average_rating": round(safe_number(feedback["Rating"].mean()), 2),
        "sentiment": {
            "Positive": int(counts.get("Positive", 0)),
            "Neutral": int(counts.get("Neutral", 0)),
            "Negative": int(counts.get("Negative", 0)),
        },
        "themes": [
            {"name": name.title(), "count": count}
            for name, count in theme_counter.most_common(5)
            if count > 0
        ],
    }


def extract_pdf_text(file_bytes):
    """Extract text from an optional PDF market report."""
    if not file_bytes:
        return "No market report was uploaded."
    try:
        reader = PdfReader(io.BytesIO(file_bytes))
        return " ".join(page.extract_text() or "" for page in reader.pages)[:12000]
    except Exception as error:
        raise HTTPException(400, f"Could not read PDF report: {error}")


def build_rules(analysis, feedback):
    """Create transparent risks and opportunities from business rules."""
    comparison = analysis["comparison"]
    kpis = analysis["kpis"]
    risks, opportunities = [], []

    if comparison["revenue_change"] < 0:
        risks.append("Latest-month revenue declined compared with the previous month.")
    if comparison["profit_change"] < comparison["revenue_change"]:
        risks.append("Profit is growing more slowly than revenue, indicating margin pressure.")
    if feedback["sentiment"].get("Negative", 0) > feedback["sentiment"].get("Positive", 0) * 0.4:
        risks.append("Negative feedback is relatively high and needs management attention.")
    if kpis["profit_margin"] < 20:
        risks.append("Overall profit margin is below 20%.")

    best_region = analysis["regions"][0]["Region"]
    best_product = analysis["products"][0]["Product"]
    opportunities.append(f"Expand successful activities from the {best_region} region.")
    opportunities.append(f"Increase promotion and inventory planning for {best_product}.")
    if feedback["average_rating"] >= 4:
        opportunities.append("Use strong customer satisfaction in marketing campaigns.")

    return risks or ["No major rule-based risk was detected."], opportunities


def local_executive_summary(analysis, feedback, risks, opportunities):
    """Fallback summary shown when no Gemini API key is configured."""
    kpis = analysis["kpis"]
    comparison = analysis["comparison"]
    return (
        f"The business generated total revenue of INR {kpis['total_revenue']:,.0f} "
        f"and profit of INR {kpis['total_profit']:,.0f}, with a {kpis['profit_margin']:.1f}% margin. "
        f"In {comparison['current_period']}, revenue changed by {comparison['revenue_change']:.1f}% "
        f"and profit changed by {comparison['profit_change']:.1f}% from the previous month. "
        f"Customer feedback averages {feedback['average_rating']:.1f}/5. "
        f"Priority: {risks[0]} Recommended action: {opportunities[0]}"
    )


def ask_gemini(prompt):
    """Call Gemini only when GEMINI_API_KEY is available."""
    api_key = os.getenv("GEMINI_API_KEY")
    if not api_key:
        return None
    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(model="gemini-3.5-flash", contents=prompt)
        return response.text
    except Exception:
        return None


# ------------------------------------------------------------
# 3. WEB ROUTES
# ------------------------------------------------------------
@app.get("/", response_class=HTMLResponse)
def home():
    return (BASE_DIR / "templates" / "index.html").read_text(encoding="utf-8")


@app.post("/api/analyze")
async def analyze(
    sales_file: UploadFile = File(...),
    feedback_file: Optional[UploadFile] = File(None),
    report_file: Optional[UploadFile] = File(None),
):
    """Main endpoint: analyze all uploaded business files."""
    sales_bytes = await sales_file.read()
    feedback_bytes = await feedback_file.read() if feedback_file else b""
    report_bytes = await report_file.read() if report_file else b""

    sales = prepare_sales(sales_bytes)
    sales_analysis = calculate_sales_analysis(sales)
    feedback_analysis = analyze_feedback(feedback_bytes)
    report_text = extract_pdf_text(report_bytes)
    risks, opportunities = build_rules(sales_analysis, feedback_analysis)

    prompt = f"""
You are a senior business strategy analyst. Use only the supplied facts.
Write a short executive summary followed by three actionable recommendations.

KPIs: {sales_analysis['kpis']}
Period comparison: {sales_analysis['comparison']}
Customer feedback: {feedback_analysis}
Risks: {risks}
Opportunities: {opportunities}
Market report context: {report_text[:5000]}
"""
    summary = ask_gemini(prompt) or local_executive_summary(
        sales_analysis, feedback_analysis, risks, opportunities
    )

    result = {
        **sales_analysis,
        "feedback": feedback_analysis,
        "risks": risks,
        "opportunities": opportunities,
        "executive_summary": summary,
        "ai_enabled": bool(os.getenv("GEMINI_API_KEY")),
    }
    LATEST_ANALYSIS.clear()
    LATEST_ANALYSIS.update(result)
    return result


class ScenarioInput(BaseModel):
    revenue_growth: float = 10
    cost_growth: float = 6


@app.post("/api/scenario")
def scenario(values: ScenarioInput):
    """Calculate a simple what-if business scenario."""
    if not LATEST_ANALYSIS:
        raise HTTPException(400, "Analyze the business files first.")

    kpis = LATEST_ANALYSIS["kpis"]
    projected_revenue = kpis["total_revenue"] * (1 + values.revenue_growth / 100)
    projected_cost = kpis["total_cost"] * (1 + values.cost_growth / 100)
    projected_profit = projected_revenue - projected_cost

    return {
        "projected_revenue": round(projected_revenue, 2),
        "projected_cost": round(projected_cost, 2),
        "projected_profit": round(projected_profit, 2),
        "profit_change": percentage_change(projected_profit, kpis["total_profit"]),
    }


class ChatInput(BaseModel):
    question: str


@app.post("/api/chat")
def chat(values: ChatInput):
    """Ask Gemini about the latest analysis."""
    if not LATEST_ANALYSIS:
        raise HTTPException(400, "Analyze the business files first.")

    prompt = f"""
Answer the executive's question using only this business analysis:
{LATEST_ANALYSIS}

Question: {values.question}
Keep the answer clear, practical and under 180 words.
"""
    answer = ask_gemini(prompt)
    if not answer:
        answer = (
            "Gemini is not configured. Add GEMINI_API_KEY to the .env file. "
            f"Current executive summary: {LATEST_ANALYSIS['executive_summary']}"
        )
    return {"answer": answer}
