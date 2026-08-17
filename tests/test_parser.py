"""
Unit tests for UPITransactionParser using standard unittest.
"""

import unittest
from datetime import datetime
from core.parser import UPITransactionParser


class TestUPITransactionParser(unittest.TestCase):

    def test_hdfc_sms_parsing(self):
        sms = "INR 1400.00 has been debited from your A/c no. XX172263 on 08-02-2025 21:43:50 at PUR/M S GLOBAL MART/100000000089018/503921456192."
        parsed = UPITransactionParser.parse_message(sms)

        self.assertEqual(parsed['amount'], 1400.00)
        self.assertEqual(parsed['merchant'], "M S GLOBAL MART")
        self.assertEqual(parsed['transaction_type'], "Debit")
        self.assertEqual(parsed['category'], "Groceries & Essentials")
        self.assertEqual(parsed['transaction_date'].day, 8)
        self.assertEqual(parsed['transaction_date'].month, 2)
        self.assertEqual(parsed['transaction_date'].year, 2025)

    def test_sbi_swiggy_parsing(self):
        sms = "Dear UPI user, A/c *2263 debited by Rs. 385.00 on 14-Feb-2025 13:20:00 transfer to Swiggy Ref: 504512345678."
        parsed = UPITransactionParser.parse_message(sms)

        self.assertEqual(parsed['amount'], 385.00)
        self.assertEqual(parsed['merchant'], "Swiggy")
        self.assertEqual(parsed['transaction_type'], "Debit")
        self.assertEqual(parsed['category'], "Food & Dining")
        self.assertEqual(parsed['reference_id'], "504512345678")

    def test_icici_blinkit_parsing(self):
        sms = "Your A/c ending 1722 is debited for Rs 1250.00 on 15-Feb-2025 at Blinkit Grocery. UPI txn id 504612349999."
        parsed = UPITransactionParser.parse_message(sms)

        self.assertEqual(parsed['amount'], 1250.00)
        self.assertIn("Blinkit", parsed['merchant'])
        self.assertEqual(parsed['transaction_type'], "Debit")
        self.assertEqual(parsed['category'], "Groceries & Essentials")

    def test_credit_salary_parsing(self):
        sms = "Salary of INR 65000.00 has been credited to your A/c no. XX172263 on 01-02-2025 09:00:00 from TechCorp Systems."
        parsed = UPITransactionParser.parse_message(sms)

        self.assertEqual(parsed['amount'], 65000.00)
        self.assertEqual(parsed['merchant'], "TechCorp Systems")
        self.assertEqual(parsed['transaction_type'], "Credit")

    def test_corporate_salary_payslip_email(self):
        email_text = """Dear Rohit Sharma, 
This is an automated notification from Corporate Payroll Services. Your salary for the pay period 01-Jul-2026 to 31-Jul-2026 has been successfully processed and credited via Electronic Fund Transfer (EFT). 

--- TRANSACTION SUMMARY ---
Employee Name: Rohit Sharma
Payment Mode: Direct Deposit / NeFT
Value Date: 31-Jul-2026
Transaction Reference: HDFCR5202607310084321
Status: CREDITED 

--- DESTINATION ACCOUNT ---
Bank Name: HDFC Bank Ltd
Account Number: *******5432

--- DISBURSEMENT BREAKDOWN ---
Gross Earnings: Rs 1,25,000.00
Total Deductions (Tax & Statutory): Rs 18,400.00
Net Amount Deposited: Rs 1,06,600.00 

Sincerely,
Global Payroll & HR Operations
TechCorp India Private Limited"""

        parsed = UPITransactionParser.parse_message(email_text, source='Email')
        self.assertEqual(parsed['amount'], 106600.00)
        self.assertEqual(parsed['transaction_type'], "Credit")
        self.assertIn("TechCorp", parsed['merchant'])
        self.assertEqual(parsed['reference_id'], "HDFCR5202607310084321")
        self.assertIn("5432", parsed['account'])
        self.assertEqual(parsed['transaction_date'].day, 31)
        self.assertEqual(parsed['transaction_date'].month, 7)
        self.assertEqual(parsed['transaction_date'].year, 2026)

    def test_category_classification(self):
        self.assertEqual(UPITransactionParser.classify_category("Zomato"), "Food & Dining")
        self.assertEqual(UPITransactionParser.classify_category("Netflix Subscription"), "Entertainment & OTT")
        self.assertEqual(UPITransactionParser.classify_category("Amazon Shopping"), "Shopping & E-Commerce")
        self.assertEqual(UPITransactionParser.classify_category("Uber Trip"), "Travel & Commute")
        self.assertEqual(UPITransactionParser.classify_category("Apollo Pharmacy"), "Health & Medical")
        self.assertEqual(UPITransactionParser.classify_category("Zerodha Broking"), "Investments & Finance")
        self.assertEqual(UPITransactionParser.classify_category("Electricity Bill"), "Bills & Utilities")

    def test_transaction_hash_idempotency(self):
        hash1 = UPITransactionParser.generate_transaction_hash(500.0, "Swiggy", "2025-02-14 13:00:00", "Debit", "504312345678")
        hash2 = UPITransactionParser.generate_transaction_hash(500.0, "Swiggy", "2025-02-14 13:00:00", "Debit", "504312345678")
        hash3 = UPITransactionParser.generate_transaction_hash(500.0, "Zomato", "2025-02-14 13:00:00", "Debit", "504312345679")

        self.assertEqual(hash1, hash2)
        self.assertNotEqual(hash1, hash3)


if __name__ == "__main__":
    unittest.main()
