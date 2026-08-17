"""
Decision Tree Classifier (ID3 Algorithm)
Calculates entropy, information gain, builds recursive decision tree, and makes predictions.
Compatible with Windows console encoding.
"""

import numpy as np
import pandas as pd
from typing import Any, Dict, Optional


class DecisionTreeClassifier:
    """ID3 Decision Tree Classifier from scratch."""

    def __init__(self):
        self.tree: Dict[str, Any] = {}

    @staticmethod
    def entropy(labels: pd.Series) -> float:
        """Calculate Shannon entropy of a label distribution."""
        _, counts = np.unique(labels, return_counts=True)
        probabilities = counts / counts.sum()
        # Avoid log2(0)
        probabilities = probabilities[probabilities > 0]
        return float(-np.sum(probabilities * np.log2(probabilities)))

    def information_gain(self, data: pd.DataFrame, attribute: str) -> float:
        """Calculate Information Gain by splitting on a given attribute."""
        target_col = data.columns[-1]
        total_entropy = self.entropy(data[target_col])
        values, counts = np.unique(data[attribute], return_counts=True)
        total_samples = len(data)

        weighted_entropy = sum(
            (counts[i] / total_samples) * self.entropy(data[data[attribute] == values[i]][target_col])
            for i in range(len(values))
        )

        return total_entropy - weighted_entropy

    def best_attribute_to_split(self, data: pd.DataFrame) -> str:
        """Find the attribute with highest information gain."""
        attributes = data.columns[:-1]
        gains = {attr: self.information_gain(data, attr) for attr in attributes}
        return max(gains, key=gains.get)

    def build_tree(self, data: pd.DataFrame) -> Any:
        """Build decision tree recursively."""
        labels = data.iloc[:, -1]

        # Base case 1: Pure node (all labels identical)
        if len(np.unique(labels)) == 1:
            return labels.iloc[0]

        # Base case 2: No more attributes to split on
        if len(data.columns) <= 1:
            return labels.mode()[0]

        best_attr = self.best_attribute_to_split(data)
        tree = {best_attr: {}}

        for value in np.unique(data[best_attr]):
            subset = data[data[best_attr] == value].drop(columns=[best_attr])
            tree[best_attr][value] = self.build_tree(subset)

        return tree

    def fit(self, data: pd.DataFrame) -> None:
        """Fit decision tree model."""
        self.tree = self.build_tree(data)

    def predict_sample(self, sample: pd.Series, tree: Optional[Any] = None) -> Any:
        """Predict class label for a single input record."""
        if tree is None:
            tree = self.tree

        if not isinstance(tree, dict):
            return tree

        attribute = next(iter(tree))
        val = sample.get(attribute)

        if val in tree[attribute]:
            return self.predict_sample(sample, tree[attribute][val])
        else:
            return "Unknown"

    def print_tree(self, tree: Optional[Any] = None, indent: str = "") -> None:
        """Print tree structure safely across all OS consoles (ASCII lines)."""
        if tree is None:
            tree = self.tree

        if not isinstance(tree, dict):
            print(f"{indent}-> Result: {tree}")
            return

        for attribute, branches in tree.items():
            print(f"{indent}[Feature: {attribute}]")
            for value, sub_branch in branches.items():
                print(f"{indent}  +-- ({value})")
                self.print_tree(sub_branch, indent + "  |   ")


if __name__ == "__main__":
    # Sample Weather Dataset
    data = {
        'Outlook': ['Sunny', 'Sunny', 'Overcast', 'Rain', 'Rain', 'Rain', 'Overcast', 'Sunny', 'Sunny', 'Rain',
                    'Sunny', 'Overcast', 'Overcast', 'Rain'],
        'Temperature': ['Hot', 'Hot', 'Hot', 'Mild', 'Cool', 'Cool', 'Cool', 'Mild', 'Cool', 'Mild', 'Mild',
                        'Mild', 'Hot', 'Mild'],
        'Humidity': ['High', 'High', 'High', 'High', 'Normal', 'Normal', 'Normal', 'High', 'Normal', 'Normal',
                     'Normal', 'High', 'Normal', 'High'],
        'Windy': [False, True, False, False, False, True, True, False, False, False, True, True, False, True],
        'PlayTennis': ['No', 'No', 'Yes', 'Yes', 'Yes', 'No', 'Yes', 'No', 'Yes', 'Yes', 'Yes', 'Yes', 'Yes', 'No']
    }

    df = pd.DataFrame(data)

    dt = DecisionTreeClassifier()
    dt.fit(df)

    print("Decision Tree Structure:")
    print("=" * 40)
    dt.print_tree()
    print("=" * 40)
