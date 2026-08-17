"""
UPI Transaction Processor CLI & Engine
Processes SMS messages, fetches IMAP emails, and generates expense summaries.
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv

# Ensure stdout handles UTF-8 on Windows
if sys.platform == 'win32':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except AttributeError:
        pass

from core.parser import UPITransactionParser
from core.db import DatabaseManager
from core.email_fetcher import EmailTransactionFetcher

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("UPIProcessor")


class UPITransactionProcessor:
    """High-level transaction processor orchestrating parsing, database, and email sync."""

    def __init__(self, db_path: str = 'transactions.db'):
        self.db = DatabaseManager(db_path)
        self.parser = UPITransactionParser()
        self.email_fetcher = EmailTransactionFetcher(self.db)

    def parse_transaction(self, message: str, source: str = 'SMS'):
        """Extract transaction details from message."""
        parsed = self.parser.parse_message(message, source=source)
        return (
            parsed['amount'],
            parsed['merchant'],
            parsed['transaction_date'],
            parsed['transaction_type']
        )

    def classify_category(self, merchant: str) -> str:
        """Classify category from merchant name."""
        return self.parser.classify_category(merchant)

    def save_transaction(self, amount: float, merchant: str, category: str,
                         transaction_type: str, source: str,
                         transaction_date: datetime) -> bool:
        """Save transaction to database safely with deduplication."""
        saved, _ = self.db.save_transaction(
            amount=amount,
            merchant=merchant,
            category=category,
            transaction_type=transaction_type,
            source=source,
            transaction_date=transaction_date
        )
        return saved

    def process_sms(self, messages=None) -> int:
        """Process SMS messages with deduplication (only if real messages provided)."""
        if not messages:
            return 0

        sms_list = [messages] if isinstance(messages, str) else messages
        saved_count = 0

        for sms in sms_list:
            parsed = self.parser.parse_message(sms, source='SMS')
            if parsed['amount']:
                saved, msg_txt = self.db.save_transaction(
                    amount=parsed['amount'],
                    merchant=parsed['merchant'],
                    category=parsed['category'],
                    transaction_type=parsed['transaction_type'],
                    source='SMS',
                    transaction_date=parsed['transaction_date'],
                    reference_id=parsed['reference_id'],
                    account=parsed['account'],
                    raw_hash=parsed['raw_hash']
                )
                if saved:
                    saved_count += 1
                    logger.info(f"Saved SMS: {parsed['merchant']} - INR {parsed['amount']} [{parsed['transaction_type']}]")

        return saved_count

    def process_emails(self, email_user: str, email_pass: str) -> None:
        """Fetch and process real UPI transaction emails from IMAP inbox."""
        if not self.email_fetcher.is_valid_credential(email_user, email_pass):
            logger.warning("Email credentials appear to be placeholder/unconfigured. Skipping IMAP fetch.")
            return

        logger.info(f"Connecting to IMAP inbox for {email_user}...")
        result = self.email_fetcher.sync_emails(email_user, email_pass, max_emails=100)
        if result['success']:
            logger.info(f"Email fetch finished: {result['saved']} new saved, {result['duplicates']} duplicates skipped.")
        else:
            logger.error(f"Email sync failed: {result.get('error')}")

    def generate_report(self) -> None:
        """Print clean expense summary report to terminal."""
        stats = self.db.get_stats()

        print("\n" + "=" * 55)
        print("           UPI EXPENSE & FINANCIAL SUMMARY           ")
        print("=" * 55)
        print(f" Total Spent (Debits) : INR {stats['total_debit']:>12,.2f}")
        print(f" Total Income/Credits : INR {stats['total_credit']:>12,.2f}")
        print(f" Net Cashflow         : INR {stats['net_balance']:>12,.2f}")
        print(f" Total Transactions   : {stats['total_count']:>16}")
        print(f" Top Expense Category : {stats['top_category']:>16}")
        print("-" * 55)
        print(f" {'Category':<25} {'Total Amount':<15} {'Count'}")
        print("-" * 55)

        for row in stats['category_breakdown']:
            print(f" {row['category']:<25} INR {row['amount']:<11,.2f} {row['count']:>4}")

        print("=" * 55 + "\n")


if __name__ == "__main__":
    processor = UPITransactionProcessor()

    email_user = os.getenv('EMAIL_USER')
    email_pass = os.getenv('EMAIL_PASS')

    if email_user and email_pass:
        print("\n[+] Fetching live bank transactions from Gmail...")
        processor.process_emails(email_user, email_pass)
    else:
        print("\n[!] No email credentials in .env. Configure EMAIL_USER and EMAIL_PASS to fetch real emails.")

    # Check for CLI SMS argument if user provided one
    if len(sys.argv) > 1:
        raw_sms = " ".join(sys.argv[1:])
        print(f"\n[+] Parsing provided SMS text...")
        processor.process_sms(raw_sms)

    processor.generate_report()
