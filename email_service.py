import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

# ─── CONFIGURATION (Unga details-ai inga kudunga) ───
SMTP_SERVER = "smtp.gmail.com"  # Gmail-ku ithan, vera provider-na mathikonga
SMTP_PORT = 587                 # TLS port
EMAIL_USER = "kausikskausikarun@gmail.com"  # Unga email id
EMAIL_PASS = "yvhnkbsmgvcxzdst"     # Unga Gmail App Password (Normal password work aagadhu)

def send_email(to_email, subject, html_body):
    msg = MIMEMultipart()
    msg["From"] = EMAIL_USER
    
    # ─── TESTING KAGA UNGA MAIL ID-AH DIRECT-AH PODUNGA ───
    msg["To"] = "kausikskausikarun@gmail.com"  # <-- Unga testing mail id
    
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html"))

    try:
        # SMTP Server connectivity
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()  # Secure connection start pannuthu
        server.login(EMAIL_USER, EMAIL_PASS)
        
        # Email send pannuthu
        server.send_message(msg)
        server.quit()
        
        print(f"✅ Email successfully sent to {msg['To']}")

    except Exception as e:
        print("❌ Email error:", e)