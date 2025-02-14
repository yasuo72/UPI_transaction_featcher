import math
import numpy as np
import pandas as pd


class DecisionTreeClassifier:
    def __init__(self):
        self.tree = {}

    def entropy(self, labels):
        """Calculate entropy of a dataset"""
        _, counts = np.unique(labels, return_counts=True)
        probabilities = counts / counts.sum()
        return -np.sum(probabilities * np.log2(probabilities))

    def information_gain(self, data, attribute):
        """Calculate information gain for splitting on a given attribute"""
        total_entropy = self.entropy(data.iloc[:, -1])
        values, counts = np.unique(data[attribute], return_counts=True)

        weighted_entropy = sum(
            (counts[i] / sum(counts)) * self.entropy(data[data[attribute] == values[i]].iloc[:, -1])
            for i in range(len(values))
        )

        return total_entropy - weighted_entropy

    def best_attribute_to_split(self, data):
        """Find the best attribute to split on"""
        attributes = data.columns[:-1]
        gains = {attr: self.information_gain(data, attr) for attr in attributes}
        return max(gains, key=gains.get)

    def build_tree(self, data):
        """Build the decision tree recursively"""
        labels = data.iloc[:, -1]

        # If all labels are the same, return that label
        if len(np.unique(labels)) == 1:
            return labels.iloc[0]

        best_attr = self.best_attribute_to_split(data)
        tree = {best_attr: {}}

        for value in np.unique(data[best_attr]):
            subset = data[data[best_attr] == value].drop(columns=[best_attr])
            tree[best_attr][value] = self.build_tree(subset)

        return tree

    def fit(self, data):
        """Fit the decision tree to the dataset"""
        self.tree = self.build_tree(data)

    def print_tree(self, tree=None, indent=""):
        """Print the decision tree"""
        if tree is None:
            tree = self.tree

        if not isinstance(tree, dict):
            print(indent + "Label:", tree)
            return

        for attribute, sub_tree in tree.items():
            print(indent + f"[Attribute: {attribute}]")
            for value, branch in sub_tree.items():
                print(indent + f"  ├── {value}:")
                self.print_tree(branch, indent + "  │  ")


# Sample dataset
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

# Train the decision tree
dt = DecisionTreeClassifier()
dt.fit(df)

# Print the decision tree
print("\nDecision Tree Structure:")
dt.print_tree()

# Additional Information
print("\nName: ROHIT SINGH")
print("ERP NO: 2203031050643")
