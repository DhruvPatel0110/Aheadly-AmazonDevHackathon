"""
Email parser for raw .eml files or pasted standard email headers.
Uses Python's standard email module and HTML sanitization without external paid dependencies.
"""
import email
from email import policy
from html.parser import HTMLParser
import io
import re
from typing import Dict, Any
from app.parsers.text_parser import hash_content


class HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.text_parts = []

    def handle_data(self, data):
        cleaned = data.strip()
        if cleaned:
            self.text_parts.append(cleaned)

    def get_text(self) -> str:
        return "\n".join(self.text_parts)


def strip_html(html_content: str) -> str:
    """Safely extract plain text from HTML content."""
    parser = HTMLTextExtractor()
    parser.feed(html_content)
    return parser.get_text()


def parse_email_input(email_bytes_or_text: bytes | str, default_title: str = "Email Notice") -> Dict[str, Any]:
    """
    Parse email from raw bytes (.eml) or text format.
    Extracts Subject, From, Date, and plain text content.
    """
    is_str = isinstance(email_bytes_or_text, str)
    if is_str:
        msg = email.message_from_string(email_bytes_or_text, policy=policy.default)
    else:
        msg = email.message_from_bytes(email_bytes_or_text, policy=policy.default)

    subject = msg.get("Subject", "").strip() or default_title
    sender = msg.get("From", "").strip()
    date_header = msg.get("Date", "").strip()

    body_text = ""
    # Extract body
    if msg.is_multipart():
        for part in msg.walk():
            content_type = part.get_content_type()
            content_disposition = str(part.get("Content-Disposition", ""))
            if "attachment" in content_disposition:
                continue

            if content_type == "text/plain":
                if is_str:
                    text_part = part.get_payload(decode=False)
                    if text_part:
                        body_text += str(text_part) + "\n"
                else:
                    payload = part.get_payload(decode=True)
                    if payload:
                        body_text += payload.decode(part.get_content_charset() or "utf-8", errors="replace") + "\n"
            elif content_type == "text/html" and not body_text:
                if is_str:
                    html_part = part.get_payload(decode=False)
                    if html_part:
                        body_text += strip_html(str(html_part)) + "\n"
                else:
                    payload = part.get_payload(decode=True)
                    if payload:
                        html_str = payload.decode(part.get_content_charset() or "utf-8", errors="replace")
                        body_text += strip_html(html_str) + "\n"
    else:
        content_type = msg.get_content_type()
        if is_str:
            payload = msg.get_payload(decode=False)
            if payload:
                body_text = strip_html(str(payload)) if content_type == "text/html" else str(payload)
            else:
                body_text = ""
        else:
            payload = msg.get_payload(decode=True)
            if payload:
                text = payload.decode(msg.get_content_charset() or "utf-8", errors="replace")
                body_text = strip_html(text) if content_type == "text/html" else text
            else:
                body_text = msg.get_payload() or ""

    if not body_text.strip():
        # Fallback to string representation if parsing had no payload
        body_text = str(email_bytes_or_text)

    # Prefix headers if available for complete evidence context
    header_summary = []
    if sender:
        header_summary.append(f"From: {sender}")
    if subject:
        header_summary.append(f"Subject: {subject}")
    if date_header:
        header_summary.append(f"Date: {date_header}")

    full_text = "\n".join(header_summary) + "\n\n" + body_text.strip() if header_summary else body_text.strip()

    return {
        "title": subject,
        "clean_text": full_text,
        "raw_text": full_text,
        "sender": sender,
        "subject": subject,
        "file_hash": hash_content(full_text),
        "source_type": "email"
    }
