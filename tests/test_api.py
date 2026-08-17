"""
Integration tests for Flask REST API using standard unittest.
"""

import unittest
import json
from app import app, db


class TestFlaskAPI(unittest.TestCase):

    def setUp(self):
        app.config['TESTING'] = True
        self.client = app.test_client()

    def test_index_route(self):
        response = self.client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"FinTrack", response.data)
        self.assertIn(b"Analytics", response.data)

    def test_get_categories_route(self):
        response = self.client.get('/api/categories')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn("Food & Dining", data['categories'])

    def test_get_stats_route(self):
        response = self.client.get('/api/stats')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertIn('total_debit', data['stats'])
        self.assertIn('total_credit', data['stats'])

    def test_parse_sms_endpoint(self):
        sms_payload = {
            "message": "Dear UPI user, A/c *2263 debited by Rs. 385.00 on 14-Feb-2025 13:20:00 transfer to Swiggy Ref: 504512345678.",
            "save": False
        }
        response = self.client.post('/api/parse-sms',
                                    data=json.dumps(sms_payload),
                                    content_type='application/json')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])
        self.assertEqual(data['parsed']['amount'], 385.0)
        self.assertEqual(data['parsed']['merchant'], "Swiggy")
        self.assertEqual(data['parsed']['category'], "Food & Dining")

    def test_sql_injection_immunity(self):
        malicious_sort = "amount; DROP TABLE transactions; --"
        response = self.client.get(f'/api/transactions?sort_by={malicious_sort}')
        self.assertEqual(response.status_code, 200)
        data = response.get_json()
        self.assertTrue(data['success'])

    def test_manual_transaction_crud(self):
        new_txn = {
            "merchant": "Test Cafe",
            "amount": 150.00,
            "category": "Food & Dining",
            "transaction_type": "Debit",
            "transaction_date": "2025-02-18 10:00:00"
        }
        # Create
        create_res = self.client.post('/api/transactions',
                                      data=json.dumps(new_txn),
                                      content_type='application/json')
        self.assertEqual(create_res.status_code, 200)
        create_data = create_res.get_json()
        self.assertTrue(create_data['success'])

        # Fetch
        fetch_res = self.client.get('/api/transactions?search=Test%20Cafe')
        fetch_data = fetch_res.get_json()
        self.assertGreaterEqual(fetch_data['pagination']['total'], 1)
        txn_id = fetch_data['data'][0]['id']

        # Delete
        del_res = self.client.delete(f'/api/transactions/{txn_id}')
        self.assertEqual(del_res.status_code, 200)
        del_data = del_res.get_json()
        self.assertTrue(del_data['success'])

    def test_export_route(self):
        response = self.client.get('/api/export')
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["Content-Disposition"], "attachment;filename=upi_transactions.csv")
        self.assertIn(b"ID,Date,Merchant,Category,Amount (INR)", response.data)


if __name__ == "__main__":
    unittest.main()
