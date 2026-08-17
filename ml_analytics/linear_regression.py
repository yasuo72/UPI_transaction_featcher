"""
Multiple Linear Regression Model
Demonstrates multiple linear regression on age and experience vs income.
Supports headless execution and chart export.
"""

import os
import matplotlib
# Use Agg backend if non-interactive
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score


def train_income_predictor(csv_path: str = None,
                           output_plot: str = 'ml_analytics/plots/linear_regression_plot.png'):
    """Train linear regression and save evaluation plot."""
    if csv_path is None:
        csv_path = os.path.join(os.path.dirname(__file__), 'data', 'multiple_linear_regression_dataset.csv')

    if not os.path.exists(csv_path):
        # Fallback to current working directory
        csv_path = 'multiple_linear_regression_dataset.csv'

    if not os.path.exists(csv_path):
        print(f"Error: Dataset {csv_path} not found.")
        return None

    df = pd.read_csv(csv_path)
    print(f"Dataset loaded: {len(df)} rows")
    print(f"Columns: {list(df.columns)}")

    X = df[['age', 'experience']]
    y = df['income']

    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

    model = LinearRegression()
    model.fit(X_train, y_train)

    y_pred = model.predict(X_test)

    mse = mean_squared_error(y_test, y_pred)
    r2 = r2_score(y_test, y_pred)

    print("Model Evaluation:")
    print(f"  Coefficients: {dict(zip(['Age', 'Experience'], model.coef_))}")
    print(f"  Intercept   : {model.intercept_:.2f}")
    print(f"  MSE         : {mse:.2f}")
    print(f"  R-Squared   : {r2:.4f}")

    # Generate Visualization Figure
    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

    # Subplot 1: Actual vs Predicted
    ax1.scatter(y_test, y_pred, color='#4f46e5', label='Actual vs Predicted', s=60)
    min_val, max_val = min(y_test), max(y_test)
    ax1.plot([min_val, max_val], [min_val, max_val], color='#ef4444', linestyle='--', label='Ideal Fit')
    ax1.set_xlabel('Actual Income (INR)')
    ax1.set_ylabel('Predicted Income (INR)')
    ax1.set_title('Actual vs Predicted Income')
    ax1.legend()
    ax1.grid(True, alpha=0.3)

    # Subplot 2: Feature Coefficients
    ax2.bar(['Age', 'Experience'], model.coef_, color=['#0ea5e9', '#10b981'])
    ax2.set_ylabel('Coefficient Value')
    ax2.set_title('Feature Importance')
    ax2.grid(True, alpha=0.3)

    plt.tight_layout()
    plt.savefig(output_plot, dpi=150)
    plt.close()
    print(f"Plot saved to: {output_plot}")

    return model


if __name__ == "__main__":
    train_income_predictor()
