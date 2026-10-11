# AI Business Strategy & Executive Decision Platform

A  FastAPI project that analyzes sales data, customer feedback and a PDF market report. It calculates KPIs, identifies trends and risks, supports scenario analysis and uses Gemini for executive summaries and business questions.


## Features

- Sales KPI calculation
- Monthly revenue and profit trends
- Period comparison
- Simple anomaly detection
- Customer sentiment and feedback themes
- Business risks and opportunities
- Gemini executive summary
- What-if scenario analysis
- AI business assistant

## Project structure

```text
AI_Business_Decision_Platform/
|-- app.py
|-- requirements.txt
|-- .env.example
|-- templates/
|   `-- index.html
|-- static/
|   |-- style.css
|   `-- app.js
`-- sample_data/
    |-- sales.csv
    |-- customer_feedback.csv
    `-- business_market_report.pdf
```

## Run in VS Code on Windows

### 1. Open the project

Open the `AI_Business_Decision_Platform` folder in VS Code and open its terminal.

### 2. Create a virtual environment

```powershell
python -m venv .venv
```

### 3. Activate it

```powershell
.venv\Scripts\activate
```

If PowerShell blocks activation, run:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\activate
```

### 4. Install packages

```powershell
pip install -r requirements.txt
```

### 5. Configure Gemini

Copy `.env.example`, rename the copy to `.env`, and replace the example value:

```text
GEMINI_API_KEY=your_real_api_key
```

The dashboard still works without Gemini by using a local summary.

### 6. Start the application

```powershell
uvicorn app:app --reload
```

Open [http://127.0.0.1:8000](http://127.0.0.1:8000) in your browser.

## Test the project

Upload the three files inside `sample_data`:

1. `sales.csv`
2. `customer_feedback.csv`
3. `business_market_report.pdf`

Then click **Analyze business**.


