"""
FinTrack UPI Core Engine Package
Provides multi-bank transaction parsing, SQLite persistence, and IMAP email synchronization.
"""

from core.parser import UPITransactionParser
from core.db import DatabaseManager
from core.email_fetcher import EmailTransactionFetcher

__all__ = [
    "UPITransactionParser",
    "DatabaseManager",
    "EmailTransactionFetcher"
]
