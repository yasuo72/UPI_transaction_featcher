"""
IMAP Email Fetcher Module
Robustly connects to IMAP server, downloads unread transaction emails, and parses transactions.
"""

import imaplib
import email
from email.message import Message
from email.header import decode_header
import re
import logging
from typing import Dict, Any, Optional, List
from core.parser import UPITransactionParser
from core.db import DatabaseManager

logger = logging.getLogger(__name__)


class EmailTransactionFetcher:
    """Fetches and parses financial emails via IMAP."""

    def __init__(self, db_manager: Optional[DatabaseManager] = None):
        self.db_manager = db_manager or DatabaseManager()

    @staticmethod
    def is_valid_credential(email_user: Optional[str], email_pass: Optional[str]) -> bool:
        """Check if email credentials look valid (not default placeholders)."""
        if not email_user or not email_pass:
            return False
        user_lower = email_user.lower().strip()
        pass_lower = email_pass.lower().strip()

        if 'xxx' in user_lower or 'your_email' in user_lower or '@' not in user_lower:
            return False
        if 'xxxx' in pass_lower or 'your_password' in pass_lower or len(pass_lower) < 6:
            return False
        return True

    @staticmethod
    def _decode_header_str(header_val: Any) -> str:
        """Safely decode email header."""
        if not header_val:
            return ""
        decoded_parts = decode_header(header_val)
        res = []
        for part, encoding in decoded_parts:
            if isinstance(part, bytes):
                try:
                    res.append(part.decode(encoding or 'utf-8', errors='replace'))
                except Exception:
                    res.append(part.decode('utf-8', errors='replace'))
            else:
                res.append(str(part))
        return "".join(res)

    @staticmethod
    def _extract_body_text(msg: Message) -> str:
        """Extract plain text or cleaned HTML body from an email message."""
        text_parts = []
        html_parts = []

        if msg.is_multipart():
            for part in msg.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))

                if "attachment" in content_disposition:
                    continue

                charset = part.get_content_charset() or 'utf-8'
                payload = part.get_payload(decode=True)
                if not payload:
                    continue

                try:
                    decoded = payload.decode(charset, errors='replace')
                except Exception:
                    decoded = payload.decode('utf-8', errors='replace')

                if content_type == 'text/plain':
                    text_parts.append(decoded)
                elif content_type == 'text/html':
                    html_parts.append(decoded)
        else:
            charset = msg.get_content_charset() or 'utf-8'
            payload = msg.get_payload(decode=True)
            if payload:
                try:
                    decoded = payload.decode(charset, errors='replace')
                except Exception:
                    decoded = payload.decode('utf-8', errors='replace')

                if msg.get_content_type() == 'text/plain':
                    text_parts.append(decoded)
                else:
                    html_parts.append(decoded)

        if text_parts:
            return "\n".join(text_parts)

        if html_parts:
            # Strip html tags to obtain text
            raw_html = "\n".join(html_parts)
            clean_text = re.sub(r'<[^>]+>', ' ', raw_html)
            clean_text = re.sub(r'\s+', ' ', clean_text).strip()
            return clean_text

        return ""

    def sync_emails(self, email_user: str, email_pass: str,
                    imap_host: str = 'imap.gmail.com',
                    imap_port: int = 993,
                    folder: str = 'INBOX',
                    max_emails: int = 25) -> Dict[str, Any]:
        """
        Fetch and parse unread transaction emails.
        Returns summary dictionary.
        """
        if not self.is_valid_credential(email_user, email_pass):
            return {
                'success': False,
                'error': 'Invalid or placeholder email credentials in .env. Please configure real IMAP App Password.',
                'fetched': 0,
                'saved': 0,
                'duplicates': 0
            }

        stats = {'success': True, 'fetched': 0, 'saved': 0, 'duplicates': 0, 'errors': 0}

        mail = None
        try:
            # Clean up credentials (strip spaces in app passwords)
            email_pass_clean = email_pass.replace(" ", "")

            mail = imaplib.IMAP4_SSL(imap_host, imap_port)
            mail.login(email_user, email_pass_clean)
            mail.select(folder)

            # Search recent UIDs
            status, all_msgs = mail.uid('SEARCH', None, 'ALL')
            if status != 'OK' or not all_msgs or not all_msgs[0]:
                return stats

            all_uids = all_msgs[0].split()
            target_uids = all_uids[-max_emails:]
            if not target_uids:
                return stats

            # 1. Fetch all headers in a single fast batch request
            id_str = b",".join(target_uids)
            status, hdata_list = mail.uid('FETCH', id_str, '(BODY.PEEK[HEADER.FIELDS (SUBJECT FROM DATE)])')
            if status != 'OK' or not hdata_list:
                return stats

            txn_subject_keywords = {
                'debit', 'credit', 'upi', 'transaction', 'transferred',
                'credited', 'debited', 'spent', 'received', 'sent to',
                'payment successful', 'txn alert', 'purchase alert', 'spend of'
            }
            bank_senders = {'bank', 'alert', 'notify', 'hdfc', 'sbi', 'icici', 'axis', 'paytm', 'phonepe', 'gpay', 'cred', 'reliance', 'amazon'}

            for item in hdata_list:
                if not isinstance(item, tuple) or len(item) < 2:
                    continue

                raw_header = item[1]
                hmsg = email.message_from_bytes(raw_header)
                subject = self._decode_header_str(hmsg.get('Subject', '')).strip()
                sender = self._decode_header_str(hmsg.get('From', '')).strip()
                subject_lower = subject.lower()
                sender_lower = sender.lower()

                # Ignore non-transactional newsletters & promotional emails
                if any(bad in subject_lower for bad in ['security alert', 'terms of use', 'news', 'podcast', 'recording', 'gpt', 'fewer credits', 'now use']):
                    continue

                is_financial_subj = any(kw in subject_lower for kw in txn_subject_keywords)
                is_bank_sender = any(bs in sender_lower for bs in bank_senders)

                if is_financial_subj or is_bank_sender:
                    # Extract UID from response tuple e.g. b'2122 (UID 2122 BODY...'
                    item_info = item[0].decode(errors='ignore') if isinstance(item[0], bytes) else str(item[0])
                    uid_match = re.search(r'UID\s+(\d+)', item_info)
                    if not uid_match:
                        continue
                    uid_str = uid_match.group(1)

                    status, data = mail.uid('FETCH', uid_str.encode(), '(RFC822)')
                    if status != 'OK' or not data or not data[0] or not isinstance(data[0], tuple):
                        continue

                    raw_email = data[0][1]
                    msg = email.message_from_bytes(raw_email)
                    body = self._extract_body_text(msg)
                    full_text = f"{subject}\n{body}"

                    # Extract email date from headers
                    email_date = None
                    date_header = msg.get('Date')
                    if date_header:
                        try:
                            email_date = email.utils.parsedate_to_datetime(date_header)
                            if email_date and email_date.tzinfo:
                                email_date = email_date.replace(tzinfo=None)
                        except Exception:
                            email_date = None

                    parsed = UPITransactionParser.parse_message(full_text, source='Email', fallback_date=email_date)

                    if parsed['amount'] and parsed['amount'] > 0:
                        saved, msg_txt = self.db_manager.save_transaction(
                            amount=parsed['amount'],
                            merchant=parsed['merchant'],
                            category=parsed['category'],
                            transaction_type=parsed['transaction_type'],
                            source='Email',
                            transaction_date=parsed['transaction_date'],
                            reference_id=parsed['reference_id'],
                            account=parsed['account'],
                            raw_hash=parsed['raw_hash']
                        )
                        stats['fetched'] += 1
                        if saved:
                            stats['saved'] += 1
                        else:
                            stats['duplicates'] += 1

            return stats

        except Exception as e:
            logger.error(f"Email fetch failed: {e}")
            stats['success'] = False
            stats['error'] = str(e)
            return stats

        finally:
            if mail:
                try:
                    mail.close()
                except Exception:
                    pass
                try:
                    mail.logout()
                except Exception:
                    pass
