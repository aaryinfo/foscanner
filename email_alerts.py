import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import datetime
from dotenv import load_dotenv

load_dotenv()

SMTP_SERVER = os.getenv("SMTP_SERVER", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", 587))
SMTP_USER = os.getenv("SMTP_USER")
SMTP_PASS = os.getenv("SMTP_PASS")
DEST_EMAIL = "aaryinfo@gmail.com"

def send_email_alert(subject: str, body: str, is_html: bool = False):
    """
    Sends an email alert.
    Requires SMTP_USER and SMTP_PASS environment variables to be set.
    """
    if not SMTP_USER or not SMTP_PASS:
        print("SMTP_USER or SMTP_PASS not set. Skipping email alert.")
        return False
        
    msg = MIMEMultipart()
    msg['From'] = SMTP_USER
    msg['To'] = DEST_EMAIL
    msg['Subject'] = f"[{datetime.date.today()}] {subject}"
    
    if is_html:
        msg.attach(MIMEText(body, 'html'))
    else:
        msg.attach(MIMEText(body, 'plain'))
        
    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASS)
        text = msg.as_string()
        server.sendmail(SMTP_USER, DEST_EMAIL, text)
        server.quit()
        print(f"Email alert sent successfully to {DEST_EMAIL}.")
        return True
    except Exception as e:
        print(f"Failed to send email alert: {e}")
        return False

if __name__ == "__main__":
    send_email_alert("Test AstroMarket Pro Alert", "This is a test alert.")
