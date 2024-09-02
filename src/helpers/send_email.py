import os
from dotenv import load_dotenv

from datetime import datetime

import smtplib, ssl
from email.mime.text import MIMEText

load_dotenv(override=True)

context = ssl.create_default_context()

EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS']
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD']
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = os.environ['EMAIL_PORT']
PERSONAL_EMAIL = os.environ['PERSONAL_EMAIL']
EMAIL_SMS = os.environ['EMAIL_SMS']

def send_email(messages, subject):
    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as server:
        if len(messages) > 0:
            try:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

                body = '\n\n'.join(messages)
                email_msg = MIMEText(body)
                email_msg['Subject'] = subject
                email_msg['From'] = EMAIL_ADDRESS
                recipients = [PERSONAL_EMAIL, EMAIL_SMS]
                email_msg['To'] = ', '.join(recipients)

                # server.sendmail(EMAIL_ADDRESS, PERSONAL_EMAIL, email_msg.as_string()) # send email
                server.sendmail(EMAIL_ADDRESS, recipients, email_msg.as_string()) # send text message

                print(f'{datetime.now()} - Sent email notification')
            except Exception as e:
                print(e)
                