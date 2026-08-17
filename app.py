"""
UPI Transaction Dashboard & REST API
Flask backend for transaction management, analytics, parsing, and data export.
"""

import os
import io
import csv
from datetime import datetime
from flask import Flask, jsonify, render_template, request, Response, send_file
from dotenv import load_dotenv

from core.db import DatabaseManager
from core.parser import UPITransactionParser
from core.email_fetcher import EmailTransactionFetcher

# Load environment variables
load_dotenv()

app = Flask(__name__, static_folder='static', template_folder='templates')
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
db = DatabaseManager('transactions.db')
email_fetcher = EmailTransactionFetcher(db)


@app.after_request
def add_cache_control(response):
    """Ensure browser never caches stale JS/CSS during development."""
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate, max-age=0"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response


@app.route("/")
def index():
    """Serve main dashboard view."""
    return render_template("index.html")


@app.route("/get_transactions", methods=["GET"])
@app.route("/api/transactions", methods=["GET"])
def get_transactions():
    """
    Fetch paginated, filtered, and sorted transactions.
    Secured against SQL Injection.
    """
    try:
        limit = max(1, min(int(request.args.get("limit", 25)), 200))
        page = max(1, int(request.args.get("page", 1)))
        offset = (page - 1) * limit

        sort_by = request.args.get("sort_by", "transaction_date")
        order = request.args.get("order", "DESC")
        search = request.args.get("search", "")
        category = request.args.get("category", "")
        transaction_type = request.args.get("type", "")
        start_date = request.args.get("start_date", "")
        end_date = request.args.get("end_date", "")

        transactions, total_count = db.fetch_transactions(
            limit=limit,
            offset=offset,
            sort_by=sort_by,
            order=order,
            search=search,
            category=category,
            transaction_type=transaction_type,
            start_date=start_date,
            end_date=end_date
        )

        total_pages = (total_count + limit - 1) // limit if total_count > 0 else 1

        # Return backward-compatible array for /get_transactions if raw format requested
        if request.path == "/get_transactions" and not request.args.get("paginated"):
            return jsonify(transactions)

        return jsonify({
            'success': True,
            'data': transactions,
            'pagination': {
                'total': total_count,
                'page': page,
                'limit': limit,
                'total_pages': total_pages
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/stats", methods=["GET"])
def get_stats():
    """Return high-level summary metrics, breakdown, and monthly trends."""
    try:
        stats = db.get_stats()
        return jsonify({'success': True, 'stats': stats})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/categories", methods=["GET"])
def get_categories():
    """Return available category list."""
    categories = list(UPITransactionParser.CATEGORY_KEYWORDS.keys())
    return jsonify({'success': True, 'categories': categories})


@app.route("/api/transactions", methods=["POST"])
def add_transaction():
    """Manually add a transaction."""
    try:
        data = request.get_json() or {}
        amount = float(data.get("amount", 0))
        merchant = str(data.get("merchant", "")).strip()
        category = str(data.get("category", "")).strip() or UPITransactionParser.classify_category(merchant)
        transaction_type = str(data.get("transaction_type", "Debit")).capitalize()
        source = str(data.get("source", "Manual")).strip()
        date_str = data.get("transaction_date")
        reference_id = str(data.get("reference_id", "")).strip() or None
        account = str(data.get("account", "")).strip() or None

        if not merchant:
            return jsonify({'success': False, 'error': 'Merchant name is required'}), 400
        if amount <= 0:
            return jsonify({'success': False, 'error': 'Amount must be greater than 0'}), 400
        if transaction_type not in ["Debit", "Credit"]:
            transaction_type = "Debit"

        txn_date = datetime.now()
        if date_str:
            try:
                txn_date = datetime.strptime(date_str, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                try:
                    txn_date = datetime.strptime(date_str, "%Y-%m-%d")
                except ValueError:
                    pass

        saved, msg = db.save_transaction(
            amount=amount,
            merchant=merchant,
            category=category,
            transaction_type=transaction_type,
            source=source,
            transaction_date=txn_date,
            reference_id=reference_id,
            account=account
        )

        if not saved:
            return jsonify({'success': False, 'error': msg}), 400

        return jsonify({'success': True, 'message': 'Transaction added successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/transactions/<int:txn_id>", methods=["DELETE"])
def delete_transaction(txn_id):
    """Delete a transaction by ID."""
    try:
        res = db.delete_transaction(txn_id)
        if isinstance(res, tuple):
            success, msg = res
        else:
            success = bool(res)
            msg = "Transaction deleted successfully" if success else "Transaction not found"

        if success:
            return jsonify({'success': True, 'message': msg})
        return jsonify({'success': False, 'error': msg}), 404
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/parse-sms", methods=["POST"])
def parse_sms():
    """
    Parse a raw SMS message and optionally save it.
    Payload: {"message": "...", "save": true/false}
    """
    try:
        data = request.get_json() or {}
        message = data.get("message", "").strip()
        should_save = bool(data.get("save", False))

        if not message:
            return jsonify({'success': False, 'error': 'SMS text is required'}), 400

        parsed = UPITransactionParser.parse_message(message, source='SMS')

        if not parsed['amount']:
            return jsonify({
                'success': False,
                'error': 'Could not extract valid transaction amount from text.',
                'parsed': parsed
            }), 422

        saved = False
        save_msg = ""
        if should_save:
            saved, save_msg = db.save_transaction(
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

        return jsonify({
            'success': True,
            'parsed': {
                'amount': parsed['amount'],
                'merchant': parsed['merchant'],
                'category': parsed['category'],
                'transaction_date': parsed['transaction_date_str'],
                'transaction_type': parsed['transaction_type'],
                'reference_id': parsed['reference_id'],
                'account': parsed['account'],
                'source': parsed['source']
            },
            'saved': saved,
            'save_message': save_msg
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/sync", methods=["POST"])
def sync_transactions():
    """
    Trigger transaction sync.
    Payload: {"source": "sms"|"email"|"all"}
    """
    try:
        data = request.get_json() or {}
        sync_source = data.get("source", "all").lower()

        results = {'sms_saved': 0, 'email_saved': 0, 'errors': []}

        if sync_source == "sms" and data.get("message"):
            from upi_transaction_processor import UPITransactionProcessor
            processor = UPITransactionProcessor()
            results['sms_saved'] = processor.process_sms(data.get("message"))

        if sync_source in ["email", "all"]:
            email_user = os.getenv("EMAIL_USER")
            email_pass = os.getenv("EMAIL_PASS")

            if EmailTransactionFetcher.is_valid_credential(email_user, email_pass):
                email_res = email_fetcher.sync_emails(email_user, email_pass, max_emails=100)
                results['email_saved'] = email_res.get('saved', 0)
                if not email_res.get('success') and email_res.get('error'):
                    results['errors'].append(email_res['error'])
            else:
                results['errors'].append("Email sync skipped: Credentials not configured in .env")

        return jsonify({'success': True, 'results': results})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route("/api/export", methods=["GET"])
def export_transactions():
    """Export all transactions as a CSV file download."""
    try:
        transactions = db.export_all_transactions()

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow([
            "ID", "Date", "Merchant", "Category", "Amount (INR)",
            "Type", "Source", "Reference ID", "Account"
        ])

        for t in transactions:
            writer.writerow([
                t.get('id'),
                t.get('transaction_date'),
                t.get('merchant'),
                t.get('category'),
                t.get('amount'),
                t.get('transaction_type'),
                t.get('source'),
                t.get('reference_id') or '',
                t.get('account') or ''
            ])

        output.seek(0)
        return Response(
            output.getvalue(),
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment;filename=upi_transactions.csv"}
        )
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


import threading
import time
import logging

def auto_sync_worker(interval_seconds: int = 600):
    """Background worker that automatically syncs transaction emails on startup and every N seconds."""
    # Run once shortly after startup
    time.sleep(2)
    while True:
        email_user = os.getenv("EMAIL_USER")
        email_pass = os.getenv("EMAIL_PASS")
        if EmailTransactionFetcher.is_valid_credential(email_user, email_pass):
            try:
                logging.info(f"[Auto-Sync] Checking Gmail for new transaction alerts ({email_user})...")
                res = email_fetcher.sync_emails(email_user, email_pass, max_emails=25)
                if res.get('saved', 0) > 0:
                    logging.info(f"[Auto-Sync] Success! Added {res['saved']} new transactions from Gmail.")
                else:
                    logging.info("[Auto-Sync] Up to date. No new unrecorded transactions.")
            except Exception as e:
                logging.error(f"[Auto-Sync] Background sync error: {e}")
        time.sleep(interval_seconds)


def start_background_sync():
    """Start background auto-sync thread."""
    t = threading.Thread(target=auto_sync_worker, daemon=True)
    t.start()


if __name__ == "__main__":
    start_background_sync()
    app.run(debug=True, port=5000)
