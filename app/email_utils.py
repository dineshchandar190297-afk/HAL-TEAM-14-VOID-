"""
Email Notification Utility for HAL 4.0
Sends login alerts and failed-password warnings via Gmail SMTP.
"""

import smtplib
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime

# ===== GMAIL SMTP CONFIGURATION =====
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  # Using SSL port for more reliability
SMTP_USER = "dinesh190297@gmail.com"
SMTP_PASS = "uawg emko pkjg sgnw"
SENDER_EMAIL = "dinesh190297@gmail.com"
RECEIVER_EMAIL = "visshaalramachandran18@gmail.com"
SENDER_NAME = "HAL 4.0 Security"


def _send_email_sync(to_email: str, subject: str, html_body: str):
    """Direct synchronous send to ensure we catch any errors immediately in logs."""
    print(f"[EMAIL] Attempting to send to {to_email}...")
    try:
        msg = MIMEMultipart("alternative")
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(html_body, "html"))

        print(f"[EMAIL] Connecting to {SMTP_HOST}:{SMTP_PORT} (SSL)...")
        with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT) as server:
            print("[EMAIL] Logging in...")
            server.login(SMTP_USER, SMTP_PASS)
            print(f"[EMAIL] Sending mail...")
            server.sendmail(SENDER_EMAIL, to_email, msg.as_string())
        print(f"[EMAIL] ✅ SUCCESS! Message sent to {to_email}")
    except Exception as e:
        print(f"[EMAIL ERROR] ❌ CRITICAL FAILURE: {e}")
        if hasattr(e, 'smtp_code'):
            print(f"[EMAIL ERROR] Code: {e.smtp_code}, Msg: {e.smtp_error.decode() if isinstance(e.smtp_error, bytes) else e.smtp_error}")



def send_login_success_email(to_email: str, username: str):
    """Send a notification when a user successfully logs in."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = "🔐 HAL 4.0 — Login Notification"
    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #04091e; border-radius: 16px; overflow: hidden; border: 1px solid rgba(157,80,187,0.3);">
        <div style="background: linear-gradient(135deg, #9d50bb, #6e48aa); padding: 30px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 24px;">🛡️ HAL 4.0</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">Secure Search Intelligence Platform</p>
        </div>
        <div style="padding: 30px; color: #e2e8f0;">
            <div style="background: rgba(0,210,255,0.1); border: 1px solid rgba(0,210,255,0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: #00d2ff; margin: 0 0 8px; font-size: 18px;">✅ Successful Login Detected</h2>
                <p style="color: #94a3b8; margin: 0;">Your account was accessed successfully.</p>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Username</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{username}</td></tr>
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Time</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{now}</td></tr>
            </table>
            <p style="color: #94a3b8; font-size: 13px; margin-top: 20px;">If this wasn't you, please change your password immediately and enable 2FA.</p>
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 15px 30px; text-align: center; border-top: 1px solid rgba(255,255,255,0.08);">
            <p style="color: #64748b; font-size: 12px; margin: 0;">HAL 4.0 — AES-256 + HMAC-SHA256 + JWT + TOTP</p>
        </div>
    </div>
    """
    _send_email_sync(RECEIVER_EMAIL, subject, html)


def send_failed_login_email(to_email: str, username: str, attempt_count: int):
    """Send an alert when someone enters wrong password multiple times."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    severity = "⚠️ WARNING" if attempt_count < 5 else "🚨 CRITICAL"
    color = "#f59e0b" if attempt_count < 5 else "#ef4444"
    subject = f"{severity} — Failed Login Alert | HAL 4.0"
    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #04091e; border-radius: 16px; overflow: hidden; border: 1px solid {color}40;">
        <div style="background: linear-gradient(135deg, {color}, {color}cc); padding: 30px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 24px;">🛡️ HAL 4.0</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">Security Alert</p>
        </div>
        <div style="padding: 30px; color: #e2e8f0;">
            <div style="background: {color}15; border: 1px solid {color}30; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: {color}; margin: 0 0 8px; font-size: 18px;">{severity} — Failed Login Attempt</h2>
                <p style="color: #94a3b8; margin: 0;">Someone tried to access your account with an incorrect password.</p>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Username</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{username}</td></tr>
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Failed Attempts</td><td style="padding: 10px 0; color: {color}; font-weight: 700; font-size: 18px;">{attempt_count}</td></tr>
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Time</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{now}</td></tr>
            </table>
            <div style="background: rgba(239,68,68,0.1); border-radius: 8px; padding: 15px; margin-top: 20px;">
                <p style="color: #fca5a5; font-size: 13px; margin: 0;">
                    <strong>🔒 Security Recommendation:</strong> If you did not attempt this login, 
                    please change your password immediately and enable Two-Factor Authentication (2FA).
                </p>
            </div>
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 15px 30px; text-align: center; border-top: 1px solid rgba(255,255,255,0.08);">
            <p style="color: #64748b; font-size: 12px; margin: 0;">HAL 4.0 — Automated Security Alert System</p>
        </div>
    </div>
    """
    _send_email_sync(RECEIVER_EMAIL, subject, html)
