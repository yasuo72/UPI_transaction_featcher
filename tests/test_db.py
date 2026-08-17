"""
Unit tests for DatabaseManager using standard unittest.
"""

import os
import unittest
from datetime import datetime
from core.db import DatabaseManager

TEST_DB_PATH = "test_transactions.db"


class TestDatabaseManager(unittest.TestCase):

    def setUp(self):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except PermissionError:
                pass
        self.db = DatabaseManager(TEST_DB_PATH)

    def tearDown(self):
        if os.path.exists(TEST_DB_PATH):
            try:
                os.remove(TEST_DB_PATH)
            except PermissionError:
                pass

    def test_insert_and_deduplicate(self):
        # Insert first time
        saved1, msg1 = self.db.save_transaction(
            amount=250.0,
            merchant="Netflix",
            category="Entertainment & OTT",
            transaction_type="Debit",
            source="SMS",
            transaction_date=datetime(2025, 2, 7, 19, 30),
            raw_hash="hash_netflix_123"
        )
        self.assertTrue(saved1)

        # Insert duplicate
        saved2, msg2 = self.db.save_transaction(
            amount=250.0,
            merchant="Netflix",
            category="Entertainment & OTT",
            transaction_type="Debit",
            source="SMS",
            transaction_date=datetime(2025, 2, 7, 19, 30),
            raw_hash="hash_netflix_123"
        )
        self.assertFalse(saved2)
        self.assertIn("Duplicate", msg2)

    def test_fetch_and_filter(self):
        self.db.save_transaction(amount=300.0, merchant="Swiggy", category="Food & Dining", transaction_type="Debit", raw_hash="h1")
        self.db.save_transaction(amount=5000.0, merchant="Salary", category="Other", transaction_type="Credit", raw_hash="h2")

        # Fetch all
        txns, total = self.db.fetch_transactions()
        self.assertEqual(total, 2)

        # Filter by Debit
        debits, debit_count = self.db.fetch_transactions(transaction_type="Debit")
        self.assertEqual(debit_count, 1)
        self.assertEqual(debits[0]['merchant'], "Swiggy")

        # Search filter
        search_res, search_count = self.db.fetch_transactions(search="Salary")
        self.assertEqual(search_count, 1)
        self.assertEqual(search_res[0]['merchant'], "Salary")

    def test_stats_calculation(self):
        self.db.save_transaction(amount=400.0, merchant="Swiggy", category="Food & Dining", transaction_type="Debit", raw_hash="h1")
        self.db.save_transaction(amount=600.0, merchant="Zomato", category="Food & Dining", transaction_type="Debit", raw_hash="h2")
        self.db.save_transaction(amount=2000.0, merchant="Bonus", category="Other", transaction_type="Credit", raw_hash="h3")

        stats = self.db.get_stats()
        self.assertEqual(stats['total_debit'], 1000.0)
        self.assertEqual(stats['total_credit'], 2000.0)
        self.assertEqual(stats['net_balance'], 1000.0)
        self.assertEqual(stats['total_count'], 3)
        self.assertEqual(stats['top_category'], "Food & Dining")

    def test_delete_transaction(self):
        self.db.save_transaction(amount=100.0, merchant="Chai", category="Food & Dining", transaction_type="Debit", raw_hash="h1")
        txns, _ = self.db.fetch_transactions()
        txn_id = txns[0]['id']

        self.assertTrue(self.db.delete_transaction(txn_id))
        _, total = self.db.fetch_transactions()
        self.assertEqual(total, 0)


if __name__ == "__main__":
    unittest.main()
