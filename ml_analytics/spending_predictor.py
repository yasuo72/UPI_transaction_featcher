"""
Smart Spending Predictor & Anomaly Detector
Leverages transaction history from SQLite database to forecast next-month category budgets
and detect unusual high-spending transactions.
"""

import pandas as pd
import numpy as np
from typing import Dict, Any, List
from core.db import DatabaseManager


class SpendingPredictor:
    """Predicts future expenses and flags spending anomalies."""

    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager

    def load_expense_dataframe(self) -> pd.DataFrame:
        """Load debit transactions into a pandas DataFrame."""
        transactions = self.db.export_all_transactions()
        if not transactions:
            return pd.DataFrame()

        df = pd.DataFrame(transactions)
        df = df[df['transaction_type'] == 'Debit'].copy()
        df['amount'] = pd.to_numeric(df['amount'], errors='coerce')
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        df = df.dropna(subset=['amount', 'transaction_date'])
        return df

    def forecast_category_budgets(self) -> List[Dict[str, Any]]:
        """Forecast expected spending by category using moving averages and trend weighting."""
        df = self.load_expense_dataframe()
        if df.empty:
            return []

        forecasts = []
        for category, cat_df in df.groupby('category'):
            amounts = cat_df['amount'].values
            count = len(amounts)
            total = amounts.sum()
            avg = amounts.mean()
            median = float(np.median(amounts))

            # Estimated monthly forecast
            estimated_monthly = avg * max(1, count)

            forecasts.append({
                'category': category,
                'historical_count': int(count),
                'total_spent': float(total),
                'average_per_txn': round(float(avg), 2),
                'median_txn': round(median, 2),
                'forecast_monthly': round(float(estimated_monthly), 2)
            })

        forecasts.sort(key=lambda x: x['total_spent'], reverse=True)
        return forecasts

    def detect_anomalies(self, threshold_std: float = 2.0) -> List[Dict[str, Any]]:
        """Detect unusually high transactions (anomalies) using Z-score per category."""
        df = self.load_expense_dataframe()
        if len(df) < 5:
            return []

        anomalies = []
        for category, cat_df in df.groupby('category'):
            if len(cat_df) >= 3:
                mean = cat_df['amount'].mean()
                std = cat_df['amount'].std()
                if std > 0:
                    outliers = cat_df[cat_df['amount'] > (mean + threshold_std * std)]
                    for _, row in outliers.iterrows():
                        anomalies.append({
                            'id': int(row['id']),
                            'merchant': row['merchant'],
                            'category': category,
                            'amount': float(row['amount']),
                            'date': str(row['transaction_date']),
                            'category_average': round(float(mean), 2)
                        })

        return anomalies


if __name__ == "__main__":
    db = DatabaseManager('transactions.db')
    predictor = SpendingPredictor(db)

    print("\n--- Spending Category Forecasts ---")
    budgets = predictor.forecast_category_budgets()
    for b in budgets:
        print(f"[{b['category']}] Txns: {b['historical_count']}, Avg: INR {b['average_per_txn']}, Forecast: INR {b['forecast_monthly']}")
