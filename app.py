from flask import Flask, jsonify, render_template, request
import sqlite3

app = Flask(__name__)


def get_db_connection():
    """Create a new database connection"""
    conn = sqlite3.connect('transactions.db')
    conn.row_factory = sqlite3.Row  # Allows fetching columns by name
    return conn


def fetch_transactions(limit=50, offset=0, sort_by='transaction_date', order='DESC'):
    """Fetch transactions with sorting and pagination"""
    conn = get_db_connection()
    cursor = conn.cursor()
    query = f"""
        SELECT transaction_date, merchant, category, amount, transaction_type 
        FROM transactions 
        ORDER BY {sort_by} {order} 
        LIMIT ? OFFSET ?
    """
    cursor.execute(query, (limit, offset))
    transactions = cursor.fetchall()
    conn.close()

    return [dict(t) for t in transactions]


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/get_transactions", methods=["GET"])
def get_transactions():
    try:
        limit = int(request.args.get("limit", 50))  # Default 50 records
        offset = int(request.args.get("offset", 0))  # Pagination offset
        sort_by = request.args.get("sort_by", "transaction_date")
        order = request.args.get("order", "DESC").upper()

        if order not in ["ASC", "DESC"]:
            order = "DESC"

        transactions = fetch_transactions(limit, offset, sort_by, order)
        return jsonify(transactions)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    app.run(debug=True)
