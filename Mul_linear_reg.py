import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from sklearn.model_selection import train_test_split
from sklearn.linear_model import LinearRegression
from sklearn.metrics import mean_squared_error, r2_score

# Load the dataset
df = pd.read_csv('multiple_linear_regression_dataset.csv')  # Replace with your actual file path
print("Dataset loaded successfully!")

# Display the columns of the dataset
print("Columns in the dataset:", df.columns)

# Define independent (X) and dependent (y) variables
X = df[['age', 'experience']]  # Independent variables
y = df['income']  # Dependent variable

# Split the data into training and testing sets (80% training, 20% testing)
X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)

# Create the linear regression model
model = LinearRegression()

# Train the model on the training data
model.fit(X_train, y_train)

# Make predictions using the test data
y_pred = model.predict(X_test)

# Print the coefficients (weights) and intercept
print("Coefficients:", model.coef_)
print("Intercept:", model.intercept_)

# Evaluate the model
mse = mean_squared_error(y_test, y_pred)  # Mean Squared Error
r2 = r2_score(y_test, y_pred)  # R-squared score

print("Mean Squared Error:", mse)
print("R-squared:", r2)

# Visualizing the results: Actual vs Predicted values
plt.figure(figsize=(10, 6))
plt.scatter(y_test, y_pred, color='blue', label='Actual vs Predicted')
plt.plot([min(y_test), max(y_test)], [min(y_test), max(y_test)], color='red', label='Ideal Fit')
plt.xlabel('Actual Income')
plt.ylabel('Predicted Income')
plt.title('Actual vs Predicted Income')
plt.legend()
plt.show()

# Visualize the coefficients
plt.figure(figsize=(8, 5))
features = ['Age', 'Experience']
plt.bar(features, model.coef_, color='orange')
plt.xlabel('Features')
plt.ylabel('Coefficient Value')
plt.title('Feature Importance (Coefficients)')
plt.show()
