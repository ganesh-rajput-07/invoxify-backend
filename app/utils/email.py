import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from app.config.settings import settings

def get_html_template(title: str, content: str):
    """Wraps content in a professional Invox branded HTML template."""
    return f"""
    <html>
    <head>
        <style>
            .container {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; max-width: 600px; margin: 0 auto; border: 1px solid #e2e8f0; border-radius: 12px; overflow: hidden; }}
            .header {{ background: linear-gradient(135deg, #1F3A5F 0%, #0F172A 100%); padding: 30px; text-align: center; color: white; }}
            .content {{ padding: 40px; line-height: 1.6; color: #334155; background: #ffffff; }}
            .footer {{ background: #f8fafc; padding: 20px; text-align: center; font-size: 12px; color: #64748b; border-top: 1px solid #e2e8f0; }}
            .button {{ display: inline-block; padding: 12px 24px; background: #1F3A5F; color: white !important; text-decoration: none; border-radius: 8px; font-weight: bold; margin-top: 20px; }}
            .highlight {{ color: #1F3A5F; font-weight: bold; }}
            .ticket-badge {{ background: #f1f5f9; padding: 4px 8px; border-radius: 4px; font-family: monospace; font-weight: bold; border: 1px solid #cbd5e1; }}
        </style>
    </head>
    <body>
        <div class="container">
            <div class="header">
                <h1 style="margin:0; font-size: 24px; letter-spacing: 1px;">INVOX ECOSYSTEM</h1>
                <p style="margin:5px 0 0 0; opacity: 0.8; font-size: 14px;">Secure Intellectual Property Ledger</p>
            </div>
            <div class="content">
                <h2 style="color: #0F172A; margin-top: 0;">{title}</h2>
                {content}
                <p style="margin-top: 30px;">Best Regards,<br><span class="highlight">Invox Operations Team</span></p>
            </div>
            <div class="footer">
                &copy; 2026 Invox Global Ledger Services. All rights reserved.<br>
                This is an automated notification. Please do not reply directly to this email.
            </div>
        </div>
    </body>
    </html>
    """

def send_invox_email(to_email: str, subject: str, body: str, is_html: bool = False):
    """Base function to send automated platform emails."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        print(f"\n[EMAIL MOCK] To: {to_email}")
        print(f"[EMAIL MOCK] Subject: {subject}")
        print(f"[EMAIL MOCK] Body: {body[:150]}...\n")
        return True

    msg = MIMEMultipart()
    try:
        msg['From'] = f"Invox Ecosystem <{settings.MAIL_FROM}>"
        msg['To'] = to_email
        msg['Subject'] = subject
        
        if is_html:
            msg.attach(MIMEText(body, 'html'))
        else:
            msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT)
        server.starttls()
        server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False

def send_password_reset_email(to_email: str, token: str, origin: str):
    title = "Password Reset Request"
    reset_link = f"{origin}/reset-password/{token}"
    content = f"""
    <p>We received a request to reset the password for your Invox account.</p>
    <p>Please click the button below to establish new credentials. This link is valid for <span class="highlight">60 minutes</span>.</p>
    <div style="text-align: center;">
        <a href="{reset_link}" class="button">Reset Password</a>
    </div>
    <p style="font-size: 12px; color: #94a3b8; margin-top: 20px;">If you did not request this, you can safely ignore this email. Your account remains secure.</p>
    """
    return send_invox_email(to_email, "Security: Password Reset Request", get_html_template(title, content), is_html=True)

# --- Specific Notifications ---

def notify_query_submitted(email: str, ticket_id: str, subject: str, message: str):
    title = "Support Ticket Created"
    content = f"""
    <p>Your technical query has been successfully broadcasted to the Invox admin nodes.</p>
    <p><span class="highlight">Ticket ID:</span> <span class="ticket-badge">#{ticket_id[:8].upper()}</span></p>
    <div style="background: #f8fafc; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #e2e8f0;">
        <p style="margin:0; font-weight:bold;">{subject}</p>
        <p style="margin:10px 0 0 0; color: #64748b; font-size: 14px;">{message}</p>
    </div>
    <p>Our core developers are currently analyzing your request. You will receive a notification as soon as the issue is resolved on the ledger.</p>
    """
    return send_invox_email(email, f"Support Ticket [#{ticket_id[:8].upper()}]", get_html_template(title, content), is_html=True)

def notify_query_resolved(email: str, ticket_id: str, admin_note: str = ""):
    title = "Issue Resolved"
    content = f"""
    <p>Your technical query for Ticket <span class="ticket-badge">#{ticket_id[:8].upper()}</span> has been marked as <b>RESOLVED</b> by our team.</p>
    <div style="background: #f0fdf4; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid #bbf7d0; color: #166534;">
        <p style="margin:0; font-weight:bold;">Admin Resolution Note:</p>
        <p style="margin:10px 0 0 0; font-size: 14px;">{admin_note if admin_note else "The reported anomaly has been verified and cleared on the chain."}</p>
    </div>
    <p>If you continue to experience difficulties, please open a secondary ticket from your command center.</p>
    """
    return send_invox_email(email, "Update: Support Ticket Resolved", get_html_template(title, content), is_html=True)

def notify_withdrawal_requested(email: str, amount: float, method: str):
    title = "Withdrawal Initiation"
    content = f"""
    <p>A new withdrawal request has been registered on the Invox Ledger.</p>
    <ul style="list-style: none; padding: 0;">
        <li><span class="highlight">Amount:</span> Ʉ {amount:.2f}</li>
        <li><span class="highlight">Target Method:</span> {method}</li>
        <li><span class="highlight">Status:</span> Pending Verification</li>
    </ul>
    <p style="background: #fff7ed; padding: 15px; border-radius: 8px; color: #9a3412; font-size: 14px;">
        <strong>Note:</strong> These tokens are now <b>LOCKED</b> and removed from your active circulation until the request is finalized.
    </p>
    """
    return send_invox_email(email, "Wallet: Withdrawal Request Registered", get_html_template(title, content), is_html=True)

def notify_withdrawal_processed(email: str, amount: float, status: str, note: str = ""):
    is_approved = status.lower() == "approved"
    title = "Withdrawal Finalized" if is_approved else "Withdrawal Declined"
    color = "#166534" if is_approved else "#991b1b"
    bg = "#f0fdf4" if is_approved else "#fef2f2"
    border = "#bbf7d0" if is_approved else "#fecaca"

    content = f"""
    <p>The processing session for your withdrawal of <span class="highlight">Ʉ {amount:.2f}</span> is complete.</p>
    <div style="background: {bg}; padding: 20px; border-radius: 8px; margin: 20px 0; border: 1px solid {border}; color: {color};">
        <p style="margin:0; font-weight:bold;">Final Status: {status.upper()}</p>
        <p style="margin:10px 0 0 0; font-size: 14px;"><b>Note:</b> {note if note else "Standard ledger verification complete."}</p>
    </div>
    <p>{ "Please allow 1-3 business days for the funds to reflect in your target account." if is_approved else "The locked tokens have been immediately returned to your available wallet balance." }</p>
    """
    return send_invox_email(email, f"Wallet Update: {status.capitalize()}", get_html_template(title, content), is_html=True)

def notify_token_purchase(email: str, amount: float, item_name: str):
    title = "Purchase Confirmed"
    content = f"""
    <p>Transaction successful. You have successfully committed tokens to the network for a content acquisition.</p>
    <ul style="list-style: none; padding: 0;">
        <li><span class="highlight">Asset:</span> {item_name}</li>
        <li><span class="highlight">Cost:</span> Ʉ {amount:.2f}</li>
        <li><span class="highlight">Status:</span> Committed to Chain</li>
    </ul>
    <p>The asset ownership has been transferred to your digital vault.</p>
    """
    return send_invox_email(email, "Ledger: Purchase Successful", get_html_template(title, content), is_html=True)

def notify_system_fee(email: str, amount: float, purpose: str):
    title = "System Fee Deduction"
    content = f"""
    <p>An automated platform fee has been deducted from your account as part of a network operation.</p>
    <ul style="list-style: none; padding: 0;">
        <li><span class="highlight">Operation:</span> {purpose}</li>
        <li><span class="highlight">Fee Amount:</span> Ʉ {amount:.2f}</li>
        <li><span class="highlight">Status:</span> Burned / System Reward</li>
    </ul>
    <p style="font-size: 12px; color: #94a3b8;">This transaction is immutable and recorded on the Invox public ledger.</p>
    """
    return send_invox_email(email, "System: Fee Deduction Registered", get_html_template(title, content), is_html=True)

