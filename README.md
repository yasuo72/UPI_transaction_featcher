# 🚀 FinTrack UPI — Intelligent Transaction Fetcher & Financial Analytics

[![Python 3.9+](https://img.shields.io/badge/Python-3.9%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/Flask-2.0%2B-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
[![SQLite](https://img.shields.io/badge/SQLite-WAL%20Mode-003B57?style=for-the-badge&logo=sqlite&logoColor=white)](https://www.sqlite.org/)
[![Chart.js](https://img.shields.io/badge/Chart.js-4.4-FF6384?style=for-the-badge&logo=chartdotjs&logoColor=white)](https://www.chartjs.org/)
[![Tests](https://img.shields.io/badge/Tests-18%2F18%20Passing-10B981?style=for-the-badge&logo=pytest&logoColor=white)](https://github.com/)

**FinTrack UPI** is a modern, high-performance financial intelligence platform and transaction telemetry parser designed for the Indian banking and UPI ecosystem. It seamlessly synchronizes real-time transaction emails from **Gmail (IMAP SSL)**, parses multi-bank SMS alerts, auto-categorizes expenses, prevents duplicates with SHA-256 hashing, and presents rich financial insights on a glassmorphic dashboard.

---

## 📸 Dashboard Showcase

- **Smart AI Cashflow Health Score**: Real-time evaluation of income retention and spending trajectory.
- **Hero Financial Metrics**: Outflow (Spends), Inflow (Income), Net Cashflow, Top Category, and Deduplicated Records.
- **Interactive Visualizations**: Expense Distribution Doughnut Chart & Monthly Cashflow Flow Bar Chart via Chart.js.
- **Live Alert Simulator**: Test and simulate parsing for real-world SMS and bank payslips with 1-click database commit.
- **Transaction Ledger**: Instant debounce search, quick filter pills, category emoji badges, copyable reference IDs, and CSV export.

---

## 🏛️ System Architecture

```
                               ┌─────────────────────────────┐
                               │   Gmail Inbox (IMAP SSL)   │
                               │   & Bank SMS Notifications  │
                               └──────────────┬──────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │    core/email_fetcher.py       │
                             │    • Batch Header Pre-Filter    │
                             │    • Multi-Part MIME Decoder    │
                             └────────────────┬────────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │       core/parser.py            │
                             │    • Multi-Bank Regex Engine    │
                             │    • INR / Rs / ₹ Extractor     │
                             │    • Net Pay vs Gross Parser    │
                             │    • 10 Expense Categories      │
                             │    • SHA-256 Idempotency Hash   │
                             └────────────────┬────────────────┘
                                              │
                                              ▼
                             ┌─────────────────────────────────┐
                             │         core/db.py              │
                             │    • SQLite WAL Mode            │
                             │    • Unique Hash Deduplication  │
                             │    • Auto-Recalculating Stats   │
                             └────────────────┬────────────────┘
                                              │
                     ┌────────────────────────┴────────────────────────┐
                     ▼                                                 ▼
      ┌─────────────────────────────┐                   ┌─────────────────────────────┐
      │          app.py             │                   │ upi_transaction_processor.py│
      │   • Flask REST API          │                   │   • CLI Financial Report    │
      │   • Background Auto-Sync    │                   │   • Batch Sync Engine       │
      │   • Glassmorphic Dashboard  │                   │   • Formatted Summary Table │
      └─────────────────────────────┘                   └─────────────────────────────┘
```

---

## ⚡ Key Features

### 1. 🔄 Real-Time Gmail IMAP Synchronization
- Connects securely using **Google App Passwords** over SSL (`imap.gmail.com:993`).
- Single-query batch header scanning scans hundreds of emails in under a second.
- Background worker thread automatically polls for new transaction alerts every 10 minutes.
- **`🔄 Refresh & Sync`** button on the dashboard enables instant zero-friction manual sync.

### 2. 🧠 Smart Multi-Bank Indian UPI Parser
- Supports formats across **HDFC, SBI, ICICI, Axis, Paytm, PhonePe, Google Pay, CRED, and Corporate Payrolls**.
- Accurately captures amounts in `INR`, `Rs`, `Rs.`, and `₹`.
- Prioritizes **Net Credited Salary** over gross earnings in corporate payslips.
- Extracts Reference Numbers (UTR / UPI Ref), Account Suffixes (`*******5432`), and Value Dates.

### 3. 🏷️ Intelligent Auto-Categorization
Merchants are categorized across 10 buckets:
| Category | Emojis & Keywords |
|---|---|
| **Food & Dining** | 🍔 Swiggy, Zomato, McDonald's, Starbucks, Dominos, KFC, Cafe |
| **Groceries & Essentials** | 🛒 Blinkit, Zepto, Instamart, BigBasket, DMart, Nature's Basket |
| **Shopping & E-Commerce** | 🛍️ Amazon, Flipkart, Myntra, Ajio, Reliance Digital, Croma, Tata CLiQ |
| **Travel & Commute** | 🚗 Uber, Ola, Rapido, MakeMyTrip, IRCTC, Fuel, Petrol, Metro |
| **Health & Medical** | 🏥 Apollo Pharmacy, Pharmeasy, 1mg, Hospitals, Clinics, Netmeds |
| **Bills & Utilities** | ⚡ BESCOM, Tata Power, Airtel, Jio, Adani Gas, Water, Broadband |
| **Entertainment & OTT** | 🎬 Netflix, Hotstar, Prime Video, Spotify, BookMyShow, Steam |
| **Investments & Finance** | 📈 Zerodha, Groww, AngelOne, Mutual Funds, Upstox, Coin |
| **Salary / Income** | 💼 Corporate Payroll, Direct Deposit, TechCorp, Employer EFT |
| **Transfers & Personal** | 💸 Personal P2P UPI transfers, Bank Transfers |

### 4. 🛡️ Deduplication & Zero False-Positive Engine
- Computes deterministic **SHA-256 transaction hashes** from `reference_id`, `amount`, and `type`.
- Re-running the sync or refreshing the page **never creates duplicates** or inflates expense reports.
- Non-financial marketing newsletters (e.g. security alerts, news digests) are filtered out automatically.

---

## 🛠️ Installation & Setup

### Prerequisites
- **Python 3.9+** installed on your system.
- A **Google Account** with 2-Step Verification enabled to generate a Google App Password.

### 1. Clone & Navigate
```bash
git clone https://github.com/your-username/UPI_transaction_featcher.git
cd UPI_transaction_featcher
```

### 2. Create a Virtual Environment
```bash
python -m venv venv

# On Windows (PowerShell):
.\venv\Scripts\Activate.ps1

# On macOS / Linux:
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables (`.env`)
Copy the template configuration:
```bash
cp .env.example .env
```
Edit `.env` with your Gmail credentials:
```ini
EMAIL_USER=your_email@gmail.com
EMAIL_PASS=your_16_char_app_password
DATABASE_PATH=transactions.db
FLASK_PORT=5000
```

> **How to get a Google App Password:**
> 1. Go to [Google Account Security](https://myaccount.google.com/security).
> 2. Enable **2-Step Verification**.
> 3. Search for **App passwords** in the search bar.
> 4. Create an App Password for **"Mail" / "Windows Computer"**.
> 5. Copy the 16-character code into `EMAIL_PASS` (spaces are stripped automatically).

---

## 🏃 Running the Application

### 🌐 Start the Web Dashboard
```bash
python app.py
```
Open **[http://127.0.0.1:5000](http://127.0.0.1:5000)** in your browser.
- Background email sync will automatically check your inbox on startup and every 10 minutes.
- Use the **`🔄 Refresh & Sync`** button for instant manual sync.

---

## ☁️ Deploying to Vercel

The application is pre-configured for **1-click Vercel deployment** with serverless WSGI routing and `/tmp` SQLite persistence.

### Option A: Deploy via GitHub (Recommended)
1. Push your repository to **GitHub**.
2. Go to **[vercel.com/new](https://vercel.com/new)** and import your repository.
3. In **Environment Variables**, add:
   - `EMAIL_USER`: `your_email@gmail.com`
   - `EMAIL_PASS`: `your_16_character_app_password`
4. Click **Deploy**. Vercel will automatically build and host the application!

### Option B: Deploy via Vercel CLI
```bash
# 1. Install Vercel CLI (if not already installed)
npm install -g vercel

# 2. Deploy to preview
vercel

# 3. Deploy to production
vercel --prod
```

---

### 💻 Run the CLI Processor
```bash
python upi_transaction_processor.py
```
Outputs a terminal summary report:
```
=======================================================
           UPI EXPENSE & FINANCIAL SUMMARY           
=======================================================
 Total Spent (Debits) : INR     5,998.00
 Total Income/Credits : INR   1,06,600.00
 Net Cashflow         : INR   1,00,602.00
 Total Transactions   :                3
 Top Expense Category : Shopping & E-Commerce
-------------------------------------------------------
 Category                  Total Amount    Count
-------------------------------------------------------
 Shopping & E-Commerce     INR 5,998.00       2
=======================================================
```

---

## 🔌 REST API Documentation

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/api/stats` | Returns high-level financial metrics, health score, category breakdown, and monthly trends. |
| `GET` | `/api/transactions` | Paginated, searchable, filterable transaction records (`?page=1&limit=15&search=...`). |
| `POST` | `/api/transactions` | Manually add a transaction record. |
| `DELETE` | `/api/transactions/<id>` | Delete a transaction and recalculate summary reports. |
| `POST` | `/api/sync` | Trigger an immediate IMAP sync (`{"source": "email"}`). |
| `POST` | `/api/parse-sms` | Test and preview regex extraction for any SMS string (`{"message": "...", "save": false}`). |
| `GET` | `/api/categories` | Returns the list of supported expense categories. |
| `GET` | `/api/export` | Downloads the full transaction ledger as a CSV file. |

---

## 🤖 Machine Learning & Predictive Analytics

The `ml_analytics/` package provides additional coursework and forecasting tools:
- **`ml_analytics/spending_predictor.py`**: Linear regression budget forecaster and anomalous spending detector.
- **`ml_analytics/decision_tree.py`**: Custom ID3 decision tree classifier for merchant expense categorization with ASCII visualization.
- **`ml_analytics/linear_regression.py`**: Headless linear regression visualizer with non-blocking plot exports.

To run the predictive analytics engine:
```bash
python -m ml_analytics.spending_predictor
```

---

## 🧪 Automated Test Suite

FinTrack includes a comprehensive unit test suite covering parsing edge cases, database migrations, deduplication, and REST API security:

```bash
python -m unittest discover tests
```

**Output:**
```
..................
----------------------------------------------------------------------
Ran 18 tests in 0.179s

OK
```

---

## 📁 Repository Structure

```
UPI_transaction_featcher/
├── app.py                          # Flask backend & REST API controllers
├── upi_transaction_processor.py    # CLI transaction processor & report generator
├── requirements.txt                # Production dependencies
├── .env.example                    # Environment variable template
├── README.md                       # Comprehensive documentation
│
├── core/                           # Core Engine Modules
│   ├── __init__.py
│   ├── parser.py                   # Multi-bank UPI regex & AI categorizer
│   ├── db.py                       # SQLite manager, migrations & deduplication
│   └── email_fetcher.py            # Gmail IMAP sync with fast batch header parsing
│
├── ml_analytics/                   # Machine Learning Modules
│   ├── __init__.py
│   ├── spending_predictor.py       # Budget forecaster & anomaly detector
│   ├── decision_tree.py            # ID3 decision tree merchant categorizer
│   └── linear_regression.py        # Headless regression visualizer
│
├── templates/
│   └── index.html                  # FinTech Glassmorphic Dashboard View
│
├── static/
│   ├── css/
│   │   └── dashboard.css           # Glassmorphic stylesheet & dark/light themes
│   └── js/
│       └── dashboard.js            # Chart.js analytics & simulator controllers
│
└── tests/                          # Automated Unittest Suite
    ├── __init__.py
    ├── test_parser.py              # Bank alert regex & payslip tests
    ├── test_db.py                  # Database CRUD, deduplication & aggregates
    └── test_api.py                 # REST API endpoints & security tests
```

---

## 📄 License
This project is licensed under the MIT License — feel free to use and customize for personal or commercial financial telemetry tracking.
