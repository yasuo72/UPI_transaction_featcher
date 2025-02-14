import sqlite3
import re
from datetime import datetime
import imaplib
import email
from email.header import decode_header
import os
import logging
from dotenv import load_dotenv  # Load environment variables

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')


class UPITransactionProcessor:
    def __init__(self) -> None:
        """Initialize database connection and regex patterns"""
        self.db_conn = sqlite3.connect('transactions.db', check_same_thread=False)
        self.create_tables()
        self.category_keywords = {
            'Food': ['swiggy', 'zomato', 'dominos', 'pizza', 'restaurant'],
            'Bills': ['electricity', 'water', 'gas', 'bill', 'recharge'],
            'Entertainment': ['netflix', 'primevideo', 'bookmyshow', 'spotify'],
            'Shopping': ['amazon', 'flipkart', 'myntra', 'ajio'],
            'Travel': ['ola', 'uber', 'makemytrip', 'irctc'],
            'Other': []
        }

    def create_tables(self) -> None:
        """Create required tables if they don’t exist"""
        with self.db_conn:
            self.db_conn.executescript('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    merchant TEXT,
                    category TEXT,
                    transaction_date DATETIME,
                    transaction_type TEXT,
                    source TEXT
                );
                CREATE TABLE IF NOT EXISTS expense_reports (
                    category TEXT PRIMARY KEY,
                    total_amount REAL NOT NULL,
                    last_updated DATETIME
                );
            ''')

    def parse_transaction(self, message: str):
        """Extract transaction details from message"""
        try:
            amount_match = re.search(r'INR\s?([\d,]+\.?\d{2})', message)
            amount = float(amount_match.group(1).replace(",", "")) if amount_match else None

            merchant_match = re.search(r'at PUR/([^/]+)/\d+', message)
            merchant = merchant_match.group(1).strip() if merchant_match else 'Unknown'

            date_match = re.search(r'on (\d{2}-\d{2}-\d{4} \d{2}:\d{2}:\d{2})', message)
            transaction_date = datetime.strptime(date_match.group(1), "%d-%m-%Y %H:%M:%S") if date_match else datetime.now()

            transaction_type = "Debit" if "debited" in message.lower() else "Credit" if "credited" in message.lower() else "Unknown"

            return amount, merchant, transaction_date, transaction_type
        except Exception as e:
            logging.error(f"Parsing error: {e}")
            return None, None, None, "Unknown"

    def classify_category(self, merchant: str) -> str:
        """Classify transaction based on merchant name"""
        merchant_lower = merchant.lower()
        return next((category for category, keywords in self.category_keywords.items() if any(keyword in merchant_lower for keyword in keywords)), 'Other')

    def save_transaction(self, amount: float, merchant: str, category: str, transaction_type: str, source: str, transaction_date: datetime) -> bool:
        """Save transaction into the database"""
        try:
            with self.db_conn:
                self.db_conn.execute('''
                    INSERT INTO transactions (amount, merchant, category, transaction_date, transaction_type, source)
                    VALUES (?, ?, ?, ?, ?, ?)''',
                                     (amount, merchant, category, transaction_date, transaction_type, source))

                if transaction_type == "Debit":
                    self.db_conn.execute('''
                        INSERT INTO expense_reports (category, total_amount, last_updated)
                        VALUES (?, ?, ?)
                        ON CONFLICT(category) DO UPDATE SET 
                        total_amount = total_amount + excluded.total_amount,
                        last_updated = excluded.last_updated
                    ''', (category, amount, datetime.now()))

            logging.info(f"Saved transaction: {merchant} - ₹{amount} on {transaction_date} [{transaction_type}]")
            return True
        except sqlite3.Error as e:
            logging.error(f"Database error: {e}")
            return False

    def process_sms(self) -> None:
        """Process SMS messages (simulated for testing)"""
        sample_sms = [
            "INR 1400.00 has been debited from your A/c no. XX172263 on 08-02-2025 21:43:50 at PUR/M S GLOBAL "
            "MART/100000000089018/503921456192.",
            "INR 250.00 has been debited from your A/c no. XX172263 on 07-02-2025 19:30:20 at PUR/Netflix "
            "Subscription/1029384756.",
            "INR 5000.00 has been credited to your A/c no. XX172263 on 09-02-2025 10:15:30 from Amazon Seller Payments.",
        ]

        for sms in sample_sms:
            amount, merchant, transaction_date, transaction_type = self.parse_transaction(sms)
            if amount:
                category = self.classify_category(merchant)
                self.save_transaction(amount, merchant, category, transaction_type, 'SMS', transaction_date)

    def process_emails(self, email_user: str, email_pass: str) -> None:
        """Fetch and process UPI transaction emails"""
        try:
            mail = imaplib.IMAP4_SSL('imap.gmail.com')
            mail.login(email_user, email_pass)
            mail.select('inbox')

            status, messages = mail.search(None, '(SUBJECT "Transaction Alert" UNSEEN)')
            if status != 'OK':
                return

            for num in messages[0].split():
                status, data = mail.fetch(num, '(RFC822)')
                if status != 'OK':
                    continue

                msg = email.message_from_bytes(data[0][1])
                body = next((part.get_payload(decode=True).decode() for part in msg.walk() if part.get_content_type() == 'text/plain'), msg.get_payload(decode=True).decode())

                amount, merchant, transaction_date, transaction_type = self.parse_transaction(body)
                if amount:
                    category = self.classify_category(merchant)
                    self.save_transaction(amount, merchant, category, transaction_type, 'Email', transaction_date)

                mail.store(num, '+FLAGS', '\\Seen')

            mail.logout()
        except Exception as e:
            logging.error(f"Email processing error: {e}")

    def generate_report(self) -> None:
        """Generate expense report"""
        try:
            cur = self.db_conn.cursor()
            cur.execute('''
                SELECT category, ROUND(total_amount, 2), last_updated 
                FROM expense_reports 
                ORDER BY total_amount DESC''')

            report = cur.fetchall()
            print("\n=== Expense Report ===")
            print("{:<15} {:<12} {}".format('Category', 'Amount', 'Last Updated'))
            for row in report:
                print("{:<15} ₹{:<10} {}".format(row[0], row[1], row[2]))
        except sqlite3.Error as e:
            logging.error(f"Report generation error: {e}")


if __name__ == "__main__":
    processor = UPITransactionProcessor()
    processor.process_sms()

    email_user = os.getenv('EMAIL_USER')
    email_pass = os.getenv('EMAIL_PASS')

    if email_user and email_pass:
        processor.process_emails(email_user, email_pass)

    processor.generate_report()
    processor.db_conn.close()
