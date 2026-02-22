"""
Email Notification Utility for HAL 4.0
Sends login alerts and failed-password warnings via Gmail SMTP.
"""

import smtplib
import os
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
import base64
from datetime import datetime

# ===== GMAIL SMTP CONFIGURATION =====
# ===== GMAIL SMTP CONFIGURATION (Environment Variables recommended for Production) =====
SMTP_HOST = "smtp.gmail.com"
SMTP_PORT = 465  
SMTP_USER = os.getenv("EMAIL_USER", "dinesh190297@gmail.com")
SMTP_PASS = os.getenv("EMAIL_PASS", "uawg emko pkjg sgnw")
SENDER_EMAIL = os.getenv("EMAIL_USER", "dinesh190297@gmail.com")
RECEIVER_EMAIL = os.getenv("RECEIVER_EMAIL", "visshaalramachandran18@gmail.com")
SENDER_NAME = "HAL 4.0 Security"


def _send_email_sync(to_email: str, subject: str, html_body: str, image_data: str = None):
    """Direct synchronous send to ensure we catch any errors immediately in logs."""
    print(f"[EMAIL] Attempting to send to {to_email}...")
    try:
        msg = MIMEMultipart("related")
        msg["From"] = f"{SENDER_NAME} <{SENDER_EMAIL}>"
        msg["To"] = to_email
        msg["Subject"] = subject
        
        msg_alternative = MIMEMultipart("alternative")
        msg.attach(msg_alternative)
        msg_alternative.attach(MIMEText(html_body, "html"))

        if image_data:
            try:
                # Handle base64 image if provided
                if "," in image_data:
                    header, encoded = image_data.split(",", 1)
                else:
                    encoded = image_data
                image_bytes = base64.b64decode(encoded)
                img = MIMEImage(image_bytes)
                img.add_header('Content-ID', '<security_photo>')
                img.add_header('Content-Disposition', 'inline', filename="incident_capture.jpg")
                msg.attach(img)
            except Exception as e:
                print(f"[EMAIL ERROR] Failed to attach image: {e}")

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



def send_login_success_email(to_email: str, username: str, method: str = "Standard Password"):
    """Send a notification when a user successfully logs in."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    subject = f"🔐 HAL 4.0 — Login Notification ({method})"
    method_color = "#00d2ff" if "Face" not in method else "#9d50bb"
    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #04091e; border-radius: 16px; overflow: hidden; border: 1px solid rgba(157,80,187,0.3);">
        <div style="background: linear-gradient(135deg, #9d50bb, #6e48aa); padding: 30px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 24px;">🛡️ HAL 4.0</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">Secure Search Intelligence Platform</p>
        </div>
        <div style="padding: 30px; color: #e2e8f0;">
            <div style="background: rgba(0,210,255,0.1); border: 1px solid rgba(0,210,255,0.2); border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: {method_color}; margin: 0 0 8px; font-size: 18px;">✅ Successful Login Detected</h2>
                <p style="color: #94a3b8; margin: 0;">Your account was accessed successfully via <strong>{method}</strong>.</p>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Username</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{username}</td></tr>
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Auth Method</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{method}</td></tr>
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


def send_failed_login_email(to_email: str, username: str, attempt_count: int, image_data: str = None):
    """Send an alert when someone enters wrong password multiple times, with optional photo."""
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    severity = "🚨 CRITICAL" if attempt_count >= 5 or image_data else "⚠️ WARNING"
    color = "#ef4444" if attempt_count >= 5 or image_data else "#f59e0b"
    subject = f"{severity} — Security Breach Attempt | HAL 4.0"
    
    image_html = ""
    if image_data:
        image_html = """
        <div style="margin-top: 20px; text-align: center;">
            <p style="color: #fca5a5; font-size: 14px; margin-bottom: 10px;">📸 <strong>INCIDENT CAPTURE:</strong> The person below attempted to access the system.</p>
            <div style="border: 4px solid #ef4444; border-radius: 12px; display: inline-block; overflow: hidden; box-shadow: 0 0 20px rgba(239,68,68,0.4);">
                <img src="cid:security_photo" style="max-width: 100%; width: 400px; display: block;" alt="Incident Photo">
            </div>
        </div>
        """

    html = f"""
    <div style="font-family: 'Segoe UI', Arial, sans-serif; max-width: 600px; margin: 0 auto; background: #04091e; border-radius: 16px; overflow: hidden; border: 1px solid {color}40;">
        <div style="background: linear-gradient(135deg, {color}, {color}cc); padding: 30px; text-align: center;">
            <h1 style="color: #fff; margin: 0; font-size: 24px;">🛡️ HAL 4.0</h1>
            <p style="color: rgba(255,255,255,0.8); margin: 8px 0 0;">Security Alert</p>
        </div>
        <div style="padding: 30px; color: #e2e8f0;">
            <div style="background: {color}15; border: 1px solid {color}30; border-radius: 12px; padding: 20px; margin-bottom: 20px;">
                <h2 style="color: {color}; margin: 0 0 8px; font-size: 18px;">{severity} — Unauthorized Attempt</h2>
                <p style="color: #94a3b8; margin: 0;">An unauthorized person was detected trying to bypass security protocols.</p>
            </div>
            <table style="width: 100%; border-collapse: collapse;">
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Identified as</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{username}</td></tr>
                <tr><td style="padding: 10px 0; color: #94a3b8; font-size: 14px;">Time</td><td style="padding: 10px 0; color: #fff; font-weight: 600;">{now}</td></tr>
            </table>
            {image_html}
        </div>
        <div style="background: rgba(255,255,255,0.03); padding: 15px 30px; text-align: center; border-top: 1px solid rgba(255,255,255,0.08);">
            <p style="color: #64748b; font-size: 12px; margin: 0;">HAL 4.0 — Automated Security Alert System</p>
        </div>
    </div>
    """
    _send_email_sync(RECEIVER_EMAIL, subject, html, image_data=image_data)
