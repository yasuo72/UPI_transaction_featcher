"""
FinTrack Machine Learning & Predictive Analytics Package
Provides linear regression budgeting, ID3 decision tree classification, and spending forecaster.
"""

from ml_analytics.spending_predictor import SpendingPredictor
from ml_analytics.decision_tree import ID3DecisionTree
from ml_analytics.linear_regression import LinearRegressionVisualizer

__all__ = [
    "SpendingPredictor",
    "ID3DecisionTree",
    "LinearRegressionVisualizer"
]
