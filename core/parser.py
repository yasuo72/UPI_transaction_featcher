"""
UPI Transaction Parser & Categorizer Module
Handles multi-bank Indian UPI SMS and Email notification parsing.
"""

import re
import hashlib
from datetime import datetime
from typing import Optional, Dict, Any, Tuple


class UPITransactionParser:
    """Parser for extracting structured transaction details from SMS and email texts."""

    # Default category mapping based on merchant name keywords
    CATEGORY_KEYWORDS = {
        'Food & Dining': [
            'swiggy', 'zomato', 'dominos', 'pizza', 'restaurant', 'cafe', 'mcdonald',
            'kfc', 'burger king', 'starbucks', 'chai', 'dhaba', 'bakery', 'eats', 'kitchen',
            'food', 'bistro', 'biryani'
        ],
        'Groceries & Essentials': [
            'blinkit', 'zepto', 'instamart', 'bigbasket', 'dmart', 'mart', 'supermarket',
            'grocery', 'spencer', 'nature basket', 'milk', 'dairy', 'provisions'
        ],
        'Bills & Utilities': [
            'electricity', 'water', 'gas', 'bill', 'recharge', 'airtel', 'jio', 'vi',
            'bescom', 'tneb', 'cesc', 'bsnl', 'broadband', 'tatasky', 'dish tv', 'fastag'
        ],
        'Entertainment & OTT': [
            'netflix', 'primevideo', 'prime video', 'hotstar', 'disney', 'spotify',
            'bookmyshow', 'pvr', 'inox', 'youtube', 'apple music', 'steam', 'sony liv', 'zee5'
        ],
        'Shopping & E-Commerce': [
            'amazon', 'amzn', 'flipkart', 'myntra', 'ajio', 'meesho', 'nykaa', 'tata cliq',
            'reliance', 'croma', 'digital', 'electronics', 'zara', 'h&m', 'uniqlo', 'retail', 'store', 'shop'
        ],
        'Travel & Commute': [
            'ola', 'uber', 'rapido', 'makemytrip', 'irctc', 'goibibo', 'redbus',
            'indigo', 'air india', 'petrol', 'hpcl', 'bpcl', 'iocil', 'fuel', 'metro'
        ],
        'Health & Medical': [
            'pharmacy', 'pharmeasy', 'apollo', '1mg', 'tata 1mg', 'medplus', 'hospital',
            'clinic', 'doctor', 'diagnostic', 'medicals', 'netmeds'
        ],
        'Investments & Finance': [
            'zerodha', 'groww', 'indmoney', 'upstox', 'angelone', 'kuvera', 'mutual fund',
            'lic', 'insurance', 'policybazaar', 'cred', 'et money'
        ],
        'Transfers & Personal': [
            'transfer to', 'sent to', 'received from', 'vpa', 'self'
        ],
        'Other': []
    }

    @classmethod
    def extract_amount(cls, text: str) -> Optional[float]:
        """Extract monetary amount in INR / Rs / ₹ from text with priority for Net Deposited / Net Pay in payslips."""
        # 1. High-priority structured keys (payslips, invoices, explicit debit/credit statements)
        priority_patterns = [
            r'(?:Net\s+Amount(?:\s+Deposited|\s+Credited|\s+Disbursed|\s+Paid)?|Net\s+Pay(?:ment)?|Net\s+Salary|Amount\s+Deposited|Amount\s+Credited|Total\s+Credited|Total\s+Debited|Spend\s+of|Total\s+Paid|Total\s+Amount)\s*:\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d{0,2})',
            r'(?:debited|credited|paid|spent|sent|received)(?:\s+for|\s+by|\s+of)?\s+(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d{0,2})',
            r'(?:INR|Rs\.?|₹)\s*([\d,]+\.?\d{0,2})\s+(?:has\s+been\s+credited|has\s+been\s+debited|has\s+been\s+paid|credited|debited|deposited)',
            r'Amount\s*:\s*(?:INR|Rs\.?|₹)?\s*([\d,]+\.?\d{0,2})',
        ]

        for pattern in priority_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "").strip()
                if val_str and val_str != ".":
                    try:
                        amt = float(val_str)
                        if amt > 0:
                            return amt
                    except ValueError:
                        continue

        # 2. General fallback
        general_patterns = [
            r'(?:INR|Rs\.?|₹|INR\.)\s*([\d,]+\.?\d{0,2})',
            r'([\d,]+\.?\d{2})\s*(?:INR|Rs\.?|₹)',
        ]

        for pattern in general_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                val_str = match.group(1).replace(",", "").strip()
                if val_str and val_str != ".":
                    try:
                        amt = float(val_str)
                        if amt > 0:
                            return amt
                    except ValueError:
                        continue
        return None

    @classmethod
    def extract_merchant(cls, text: str) -> str:
        """Extract merchant, payee or counterparty name from message."""
        # Pattern 0: Structured Email Key-Value e.g. "Merchant Name: AMZN Mktp US", "Company: TechCorp"
        kv_match = re.search(r'(?:Merchant(?:\s+Name)?|Payee(?:\s+Name)?|Paid\s+To|Beneficiary(?:\s+Name)?|Employer(?:\s+Name)?|Company(?:\s+Name)?):\s*([A-Za-z0-9\s\.\@\-\&]+?)(?:\r|\n|$)', text, re.IGNORECASE)
        if kv_match:
            merchant = kv_match.group(1).strip()
            if merchant and len(merchant) > 1 and not merchant.isdigit():
                return merchant

        # Pattern 0.5: Company signature e.g. TechCorp India Private Limited
        company_match = re.search(r'(?:Sincerely|Regards|From),\s*(?:[^\r\n]+\r?\n)?([A-Za-z0-9\s\.\@\-\&]+(?:Private Limited|Pvt Ltd|Ltd|Inc|LLC|Corporation|Corp|Services|Technologies))', text, re.IGNORECASE)
        if company_match:
            merchant = company_match.group(1).strip()
            if merchant and len(merchant) > 1:
                return merchant

        # Pattern 1: POS/PUR format e.g. at PUR/M S GLOBAL MART/100000000089018/...
        pur_match = re.search(r'(?:at|at PUR|PUR)\/([^\/]+)(?:\/|\.|\s|$)', text, re.IGNORECASE)
        if pur_match:
            merchant = pur_match.group(1).strip()
            if merchant and not merchant.isdigit():
                return merchant

        # Pattern 2: "notification from <Company>"
        notif_match = re.search(r'notification\s+from\s+([A-Za-z0-9\s\.\@\-\&]+?)(?:\.|\r|\n|$)', text, re.IGNORECASE)
        if notif_match:
            merchant = notif_match.group(1).strip()
            if merchant and len(merchant) > 1:
                return merchant

        # Pattern 3: "transfer to <Name>", "Paid to <Name>", "sent to <Name>", "towards <Name>", "to VPA <VPA>"
        to_match = re.search(r'(?:transfer to|paid to|sent to|towards|for purchase at|to VPA|to info|to)\s+([A-Za-z0-9\s\.\@\-\&]+?)(?:\s+(?:Ref|on|via|UPI|dated|Avl|Avail|Bal|using|from|A\/c|for)|\.|$)', text, re.IGNORECASE)
        if to_match:
            merchant = to_match.group(1).strip()
            # Filter out false positives
            if merchant and len(merchant) > 1 and not merchant.lower().startswith(('a/c', 'account', 'your', 'rs', 'inr', 'debited', 'credited')):
                return merchant

        # Pattern 4: "credited to your A/c ... from <Merchant>" or "received from <Merchant>"
        from_match = re.search(r'(?:credited(?:\s+to[^\.]+)?\s+from|received\s+from|from)\s+([A-Za-z0-9\s\.\@\-\&]+?)(?:\s+(?:Ref|on|via|UPI|dated|Avl|Avail|Bal|using)|\.|$)', text, re.IGNORECASE)
        if from_match:
            merchant = from_match.group(1).strip()
            if merchant and len(merchant) > 1 and not merchant.lower().startswith(('a/c', 'account', 'your', 'bank')):
                return merchant

        # Pattern 5: "at <Merchant>"
        at_match = re.search(r'\bat\s+([A-Za-z0-9\s\.\@\-\&]+?)(?:\s+(?:on|Ref|UPI|dated|Avl|Avail|Bal|using|from|via)|\.|$)', text, re.IGNORECASE)
        if at_match:
            merchant = at_match.group(1).strip()
            if merchant and len(merchant) > 1 and not merchant.lower().startswith(('a/c', 'account', 'your', 'rs', 'inr', '1-800', '1800')):
                return merchant

        # Pattern 6: "UPI/<Ref>/<Merchant>" or "UPI:<Merchant>"
        upi_match = re.search(r'UPI(?:\/|\:|\s+ref\s+)([A-Za-z0-9\s\.\@\-\&]+?)(?:\s+credited|\s+debited|\.|$)', text, re.IGNORECASE)
        if upi_match:
            candidate = upi_match.group(1).strip()
            if candidate and not candidate.isdigit():
                return candidate

        return 'Unknown Merchant'

    @classmethod
    def extract_date(cls, text: str, fallback_date: Optional[datetime] = None) -> datetime:
        """Extract transaction timestamp from text with structured key priority and fallback."""
        # 1. Structured explicit keys: "Value Date: 31-Jul-2026", "Date & Time: 18-Aug-2026 04:25 AM", "Transaction Date: ..."
        kv_date = re.search(r'(?:Value\s+Date|Date\s*(?:&|and)?\s*Time|Transaction\s+Date|Txn\s+Date|Dated)\s*:\s*([0-9A-Za-z\s\:\-\/]+?)(?:\r|\n|$)', text, re.IGNORECASE)
        if kv_date:
            d_raw = kv_date.group(1).strip()
            # Try multiple parsing formats on the structured date string
            for fmt in (
                "%d-%b-%Y %I:%M %p", "%d-%b-%Y %I:%M:%S %p", "%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M",
                "%d %b %Y %I:%M %p", "%d %b %Y %I:%M:%S %p", "%d %b %Y %H:%M:%S", "%d %b %Y %H:%M",
                "%d-%b-%Y", "%d %b %Y", "%d-%b-%y", "%d %b %y",
                "%d-%m-%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d-%m-%Y",
                "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"
            ):
                try:
                    return datetime.strptime(d_raw, fmt)
                except ValueError:
                    pass

        # 2. Date preceded by 'on' keyword e.g. "on 14-Feb-2025 13:20:00" or "on 08-02-2025"
        on_match = re.search(r'\bon\s+(\d{1,2}[-\/\s][A-Za-z0-9]{2,4}[-\/\s]\d{2,4}(?:\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)?)', text, re.IGNORECASE)
        if on_match:
            d_str = on_match.group(1).strip()
            for fmt in (
                "%d-%b-%Y %I:%M %p", "%d-%b-%Y %I:%M:%S %p", "%d-%b-%Y %H:%M:%S", "%d-%b-%Y %H:%M",
                "%d-%b-%Y", "%d-%b-%y", "%d %b %Y",
                "%d-%m-%Y %H:%M:%S", "%d/%m/%Y %H:%M:%S", "%d-%m-%Y %H:%M", "%d/%m/%Y %H:%M",
                "%d-%m-%Y", "%d/%m/%Y", "%d-%m-%y", "%d/%m/%y"
            ):
                try:
                    return datetime.strptime(d_str.replace("/", "-"), fmt)
                except ValueError:
                    pass

        # 3. Date with AM/PM e.g. "18-Aug-2026 04:25 AM" or "18-08-2026 04:25 PM"
        ampm_match = re.search(r'(\d{1,2}[-\/\s][A-Za-z]{3}[-\/\s]\d{2,4}\s+\d{1,2}:\d{2}(?::\d{2})?\s*(?:AM|PM)?)', text, re.IGNORECASE)
        if ampm_match:
            d_str = ampm_match.group(1).strip()
            for fmt in ("%d-%b-%Y %I:%M %p", "%d-%b-%Y %I:%M:%S %p", "%d %b %Y %I:%M %p", "%d-%b-%Y %H:%M", "%d-%b-%Y %H:%M:%S"):
                try:
                    return datetime.strptime(d_str, fmt)
                except ValueError:
                    pass

        # 4. Standard full datetime: "DD-MM-YYYY HH:MM:SS"
        dt_match = re.search(r'(\d{2}[-\/]\d{2}[-\/]\d{4}\s+\d{2}:\d{2}:\d{2})', text)
        if dt_match:
            date_str = dt_match.group(1).replace("/", "-")
            for fmt in ("%d-%m-%Y %H:%M:%S", "%Y-%m-%d %H:%M:%S"):
                try:
                    return datetime.strptime(date_str, fmt)
                except ValueError:
                    pass

        # 5. Standard Date only: "DD-MM-YYYY"
        d_only = re.search(r'(\d{2}[-\/]\d{2}[-\/]\d{4})', text)
        if d_only:
            date_str = d_only.group(1).replace("/", "-")
            try:
                return datetime.strptime(date_str, "%d-%m-%Y")
            except ValueError:
                pass

        return fallback_date or datetime.now()

    @classmethod
    def extract_transaction_type(cls, text: str) -> str:
        """Determine whether transaction is Debit or Credit."""
        text_lower = text.lower()
        debit_keywords = ['debited', 'debit', 'paid', 'sent', 'transferred', 'spent', 'purchase', 'pur/', 'withdrawn', 'gross earnings']
        credit_keywords = ['credited', 'credit', 'received', 'refund', 'added to account', 'deposited', 'salary', 'net amount deposited', 'direct deposit']

        for word in credit_keywords:
            if word in text_lower:
                return "Credit"

        for word in debit_keywords:
            if word in text_lower:
                return "Debit"

        return "Debit"

    @classmethod
    def extract_reference(cls, text: str) -> Optional[str]:
        """Extract UPI Reference Number, UTR, or Txn ID."""
        patterns = [
            r'(?:Transaction\s+Reference|Txn\s+Ref|UPI\s*(?:Ref|txn|id|reference)?\s*(?:no\.?|:)?\s*|Ref\s*(?:no\.?|:)?\s*|UTR\s*(?:no\.?|:)?\s*):\s*([A-Za-z0-9]{8,24})',
            r'(?:UPI\s*(?:Ref|txn|id|reference)?\s*(?:no\.?|:)?\s*|Ref\s*(?:no\.?|:)?\s*|UTR\s*(?:no\.?|:)?\s*)([A-Za-z0-9]{8,18})',
            r'\/(\d{12})\b',
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    @classmethod
    def extract_account_suffix(cls, text: str) -> Optional[str]:
        """Extract masked account number suffix (e.g. *******5432 or XX172263)."""
        match = re.search(r'(?:A\/c|Account|card|Acct)\s*(?:Number|no\.?)?\s*(?:ending\s*)?(?:in\s*)?:?\s*([X\*]*\d{3,6})', text, re.IGNORECASE)
        if match:
            return match.group(1)
        return None

    @classmethod
    def classify_category(cls, merchant: str, custom_rules: Optional[Dict[str, list]] = None) -> str:
        """Classify transaction into an expense category using merchant keywords."""
        if not merchant or merchant.lower() in ('unknown merchant', 'unknown'):
            return 'Other'

        merchant_lower = merchant.lower()
        rules = custom_rules or cls.CATEGORY_KEYWORDS

        for category, keywords in rules.items():
            if category == 'Other':
                continue
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', merchant_lower) or keyword in merchant_lower:
                    return category

        return 'Other'

    @classmethod
    def generate_transaction_hash(cls, amount: float, merchant: str, date_str: str, txn_type: str, ref: Optional[str] = None) -> str:
        """Create a deterministic hash string to identify unique transactions and prevent duplicates."""
        if ref and len(ref) >= 6:
            raw = f"{ref}:{amount:.2f}:{txn_type}".lower().strip()
        else:
            raw = f"{merchant}:{amount:.2f}:{date_str}:{txn_type}".lower().strip()
        return hashlib.sha256(raw.encode('utf-8')).hexdigest()

    @classmethod
    def parse_message(cls, message: str, source: str = 'SMS', fallback_date: Optional[datetime] = None) -> Dict[str, Any]:
        """Parse raw SMS/Email text into a standardized transaction dictionary."""
        amount = cls.extract_amount(message)
        merchant = cls.extract_merchant(message)
        transaction_date = cls.extract_date(message, fallback_date=fallback_date)
        transaction_type = cls.extract_transaction_type(message)
        reference_id = cls.extract_reference(message)
        account = cls.extract_account_suffix(message)
        category = cls.classify_category(merchant)

        date_str = transaction_date.strftime("%Y-%m-%d %H:%M:%S")
        txn_hash = cls.generate_transaction_hash(amount or 0.0, merchant, date_str, transaction_type, reference_id) if amount else None

        return {
            'amount': amount,
            'merchant': merchant,
            'category': category,
            'transaction_date': transaction_date,
            'transaction_date_str': date_str,
            'transaction_type': transaction_type,
            'source': source,
            'reference_id': reference_id,
            'account': account,
            'raw_hash': txn_hash,
            'raw_text': message.strip()
        }
