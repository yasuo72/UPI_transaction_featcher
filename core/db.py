"""
Database Management Module
Provides safe, idempotent SQLite database connection, queries, and aggregations.
"""

import sqlite3
import os
import shutil
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple


class DatabaseManager:
    """Manages SQLite database connections, schema migrations, and queries."""

    ALLOWED_SORT_COLUMNS = {
        'id': 'id',
        'amount': 'amount',
        'merchant': 'merchant',
        'category': 'category',
        'transaction_date': 'transaction_date',
        'transaction_type': 'transaction_type',
        'source': 'source'
    }

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            db_path = os.getenv("DATABASE_PATH", "transactions.db")

        # On Vercel Serverless environment, filesystem outside /tmp is read-only
        if os.getenv("VERCEL") and not db_path.startswith("/tmp"):
            tmp_db = os.path.join("/tmp", os.path.basename(db_path))
            if not os.path.exists(tmp_db) and os.path.exists(db_path):
                try:
                    shutil.copy2(db_path, tmp_db)
                except Exception:
                    pass
            self.db_path = tmp_db
        else:
            self.db_path = db_path

        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        """Create a new database connection with row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA journal_mode = WAL")
        return conn

    def init_db(self) -> None:
        """Initialize database schema and create required indexes."""
        with self.get_connection() as conn:
            # 1. Transactions table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    amount REAL NOT NULL,
                    merchant TEXT NOT NULL,
                    category TEXT NOT NULL,
                    transaction_date DATETIME NOT NULL,
                    transaction_type TEXT NOT NULL,
                    source TEXT DEFAULT 'SMS',
                    reference_id TEXT,
                    account TEXT,
                    raw_hash TEXT UNIQUE,
                    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Migrate existing columns if migrating from old database
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(transactions)")
            existing_cols = {row['name'] for row in cursor.fetchall()}

            for col_name, col_type in [
                ('reference_id', 'TEXT'),
                ('account', 'TEXT'),
                ('raw_hash', 'TEXT'),
                ('created_at', 'DATETIME')
            ]:
                if col_name not in existing_cols:
                    conn.execute(f"ALTER TABLE transactions ADD COLUMN {col_name} {col_type}")

            # 2. Expense reports summary table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS expense_reports (
                    category TEXT PRIMARY KEY,
                    total_amount REAL NOT NULL,
                    transaction_count INTEGER DEFAULT 0,
                    last_updated DATETIME
                )
            ''')

            cursor.execute("PRAGMA table_info(expense_reports)")
            exp_cols = {row['name'] for row in cursor.fetchall()}
            if 'transaction_count' not in exp_cols:
                conn.execute("ALTER TABLE expense_reports ADD COLUMN transaction_count INTEGER DEFAULT 0")

            # 3. Create indexes for high-performance querying
            conn.execute('CREATE INDEX IF NOT EXISTS idx_txn_date ON transactions(transaction_date)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_txn_cat ON transactions(category)')
            conn.execute('CREATE INDEX IF NOT EXISTS idx_txn_type ON transactions(transaction_type)')
            try:
                conn.execute('CREATE UNIQUE INDEX IF NOT EXISTS idx_txn_hash ON transactions(raw_hash)')
            except sqlite3.OperationalError:
                conn.execute('CREATE INDEX IF NOT EXISTS idx_txn_hash ON transactions(raw_hash)')

            # Automatically recalculate expense reports
            self._recalculate_reports_internal(conn)

    def _recalculate_reports_internal(self, conn: sqlite3.Connection) -> None:
        """Internal helper to synchronize expense_reports with debit transactions."""
        conn.execute('DELETE FROM expense_reports')
        conn.execute('''
            INSERT INTO expense_reports (category, total_amount, transaction_count, last_updated)
            SELECT 
                category, 
                COALESCE(SUM(amount), 0) AS total_amount,
                COUNT(*) AS transaction_count,
                MAX(transaction_date) AS last_updated
            FROM transactions
            WHERE transaction_type = 'Debit'
            GROUP BY category
        ''')

    def recalculate_expense_reports(self) -> None:
        """Recalculate expense reports to match exact transaction records."""
        with self.get_connection() as conn:
            self._recalculate_reports_internal(conn)

    def save_transaction(self, amount: float, merchant: str, category: str,
                         transaction_type: str, source: str = 'Manual',
                         transaction_date: Optional[datetime] = None,
                         reference_id: Optional[str] = None,
                         account: Optional[str] = None,
                         raw_hash: Optional[str] = None) -> Tuple[bool, str]:
        """
        Save a transaction with deduplication support.
        Returns (is_success, status_message).
        """
        if amount is None or amount <= 0:
            return False, "Invalid amount"

        txn_date = transaction_date or datetime.now()
        date_str = txn_date.strftime("%Y-%m-%d %H:%M:%S")

        # Generate hash if not provided
        if not raw_hash:
            from core.parser import UPITransactionParser
            raw_hash = UPITransactionParser.generate_transaction_hash(
                amount, merchant, date_str, transaction_type, reference_id
            )

        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                    INSERT OR IGNORE INTO transactions 
                    (amount, merchant, category, transaction_date, transaction_type, source, reference_id, account, raw_hash)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (amount, merchant, category, date_str, transaction_type, source, reference_id, account, raw_hash))

                if cursor.rowcount == 0:
                    return False, "Duplicate transaction skipped"

                self._recalculate_reports_internal(conn)
                return True, "Transaction saved successfully"

        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"

    def delete_transaction(self, transaction_id: int) -> Tuple[bool, str]:
        """
        Delete a transaction by ID and recalculate expense reports.
        Returns (is_success, status_message).
        """
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('DELETE FROM transactions WHERE id = ?', (transaction_id,))
                if cursor.rowcount == 0:
                    return False, "Transaction not found"
                self._recalculate_reports_internal(conn)
                return True, "Transaction deleted successfully"
        except sqlite3.Error as e:
            return False, f"Database error: {str(e)}"

    def fetch_transactions(self, limit: int = 50, offset: int = 0,
                           sort_by: str = 'transaction_date', order: str = 'DESC',
                           search: Optional[str] = None,
                           category: Optional[str] = None,
                           transaction_type: Optional[str] = None,
                           start_date: Optional[str] = None,
                           end_date: Optional[str] = None) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch filtered, sorted, paginated transactions and total matching count.
        Safe against SQL Injection by validating sort column and parameterizing all filters.
        """
        # Validate sorting
        safe_sort_by = self.ALLOWED_SORT_COLUMNS.get(sort_by.lower(), 'transaction_date')
        safe_order = 'ASC' if str(order).upper() == 'ASC' else 'DESC'

        conditions = []
        params = []

        if search and search.strip():
            conditions.append("(merchant LIKE ? OR category LIKE ? OR reference_id LIKE ?)")
            term = f"%{search.strip()}%"
            params.extend([term, term, term])

        if category and category.strip() and category.lower() != 'all':
            conditions.append("category = ?")
            params.append(category.strip())

        if transaction_type and transaction_type.strip() and transaction_type.lower() != 'all':
            conditions.append("transaction_type = ?")
            params.append(transaction_type.strip().capitalize())

        if start_date and start_date.strip():
            conditions.append("transaction_date >= ?")
            params.append(start_date.strip())

        if end_date and end_date.strip():
            conditions.append("transaction_date <= ?")
            params.append(f"{end_date.strip()} 23:59:59")

        where_clause = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        count_query = f"SELECT COUNT(*) FROM transactions {where_clause}"
        data_query = f"""
            SELECT id, amount, merchant, category, transaction_date, transaction_type, source, reference_id, account
            FROM transactions 
            {where_clause}
            ORDER BY {safe_sort_by} {safe_order}
            LIMIT ? OFFSET ?
        """

        with self.get_connection() as conn:
            cursor = conn.cursor()
            # 1. Total count
            cursor.execute(count_query, tuple(params))
            total_count = cursor.fetchone()[0]

            # 2. Paginated rows
            fetch_params = params + [max(1, int(limit)), max(0, int(offset))]
            cursor.execute(data_query, tuple(fetch_params))
            rows = cursor.fetchall()
            transactions = [dict(row) for row in rows]

        return transactions, total_count

    def get_stats(self) -> Dict[str, Any]:
        """Compute high-level spending statistics, balances, and breakdown."""
        with self.get_connection() as conn:
            cursor = conn.cursor()

            # 1. Totals
            # 1. Totals & Counts
            cursor.execute('''
                SELECT 
                    COALESCE(SUM(CASE WHEN transaction_type = 'Debit' THEN amount ELSE 0 END), 0) AS total_debit,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Credit' THEN amount ELSE 0 END), 0) AS total_credit,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Debit' THEN 1 ELSE 0 END), 0) AS debit_count,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Credit' THEN 1 ELSE 0 END), 0) AS credit_count,
                    COUNT(*) AS total_count
                FROM transactions
            ''')
            row = cursor.fetchone()
            total_debit = float(row['total_debit'])
            total_credit = float(row['total_credit'])
            debit_count = int(row['debit_count'])
            credit_count = int(row['credit_count'])
            total_count = int(row['total_count'])
            net_balance = total_credit - total_debit

            # Savings Rate & Average Transaction
            savings_rate = round(((total_credit - total_debit) / total_credit * 100), 1) if total_credit > 0 else 0.0
            avg_debit = round(total_debit / debit_count, 2) if debit_count > 0 else 0.0

            # 2. Category Breakdown (Debits)
            cursor.execute('''
                SELECT category, ROUND(SUM(amount), 2) AS amount, COUNT(*) AS count
                FROM transactions
                WHERE transaction_type = 'Debit'
                GROUP BY category
                ORDER BY amount DESC
            ''')
            category_breakdown = [dict(r) for r in cursor.fetchall()]
            top_category = category_breakdown[0]['category'] if category_breakdown else "None"
            top_cat_amount = category_breakdown[0]['amount'] if category_breakdown else 0.0
            top_cat_pct = round((top_cat_amount / total_debit * 100), 1) if total_debit > 0 else 0.0

            # 3. Top Merchants by Spend
            cursor.execute('''
                SELECT merchant, ROUND(SUM(amount), 2) AS total_spent, COUNT(*) AS txn_count
                FROM transactions
                WHERE transaction_type = 'Debit'
                GROUP BY merchant
                ORDER BY total_spent DESC
                LIMIT 5
            ''')
            top_merchants = [dict(r) for r in cursor.fetchall()]

            # 4. Monthly Trend
            cursor.execute('''
                SELECT 
                    substr(transaction_date, 1, 7) AS month,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Debit' THEN amount ELSE 0 END), 0) AS debit,
                    COALESCE(SUM(CASE WHEN transaction_type = 'Credit' THEN amount ELSE 0 END), 0) AS credit
                FROM transactions
                GROUP BY month
                ORDER BY month ASC
                LIMIT 12
            ''')
            monthly_trends = [dict(r) for r in cursor.fetchall()]

            # 5. Financial Health Score (0-100) & Smart Insights
            health_score = 75
            if total_credit > 0:
                if savings_rate >= 50:
                    health_score = min(98, int(70 + (savings_rate * 0.28)))
                elif savings_rate > 20:
                    health_score = int(50 + savings_rate)
                elif savings_rate > 0:
                    health_score = int(40 + savings_rate)
                else:
                    health_score = max(15, int(40 + savings_rate))
            elif total_debit > 0:
                health_score = 45

            if total_credit > total_debit and savings_rate >= 50:
                smart_insight = f"Excellent financial health! You are retaining {savings_rate}% of your income. Top expense is {top_category} (₹{top_cat_amount:,.2f})."
            elif total_credit > total_debit:
                smart_insight = f"Positive cashflow with a {savings_rate}% savings rate. Keep monitoring {top_category} expenses."
            elif total_debit > 0 and total_credit == 0:
                smart_insight = f"Recorded ₹{total_debit:,.2f} in total expenses across {debit_count} debit transactions."
            else:
                smart_insight = "Sync your emails or paste an SMS to start generating real-time financial insights."

        return {
            'total_debit': total_debit,
            'total_credit': total_credit,
            'net_balance': net_balance,
            'debit_count': debit_count,
            'credit_count': credit_count,
            'total_count': total_count,
            'savings_rate': savings_rate,
            'avg_debit': avg_debit,
            'health_score': health_score,
            'smart_insight': smart_insight,
            'top_category': top_category,
            'top_cat_amount': top_cat_amount,
            'top_cat_pct': top_cat_pct,
            'top_merchants': top_merchants,
            'category_breakdown': category_breakdown,
            'monthly_trends': monthly_trends
        }

    def delete_transaction(self, transaction_id: int) -> bool:
        """Delete a transaction by ID and update expense reports."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            deleted = cursor.rowcount > 0
            if deleted:
                self._recalculate_reports_internal(conn)
            return deleted

    def export_all_transactions(self) -> List[Dict[str, Any]]:
        """Fetch all transaction records for export."""
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('''
                SELECT id, transaction_date, merchant, category, amount, transaction_type, source, reference_id, account
                FROM transactions
                ORDER BY transaction_date DESC
            ''')
            return [dict(r) for r in cursor.fetchall()]
