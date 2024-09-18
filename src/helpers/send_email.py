from logging import Logger
import os
from dotenv import load_dotenv

from datetime import datetime
import smtplib, ssl
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.mime.base import MIMEBase
from email import encoders

load_dotenv(override=True)

context = ssl.create_default_context()

EMAIL_ADDRESS = os.environ['EMAIL_ADDRESS']
EMAIL_PASSWORD = os.environ['EMAIL_PASSWORD']
EMAIL_HOST = os.environ['EMAIL_HOST']
EMAIL_PORT = os.environ['EMAIL_PORT']
PERSONAL_EMAIL = os.environ['PERSONAL_EMAIL']
EMAIL_SMS = os.environ['EMAIL_SMS']

def send_email(messages, subject, logger: Logger, attachments=None):
    with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as server:
        if len(messages) > 0:
            try:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

                # Create a multipart message
                email_msg = MIMEMultipart()
                email_msg['Subject'] = subject
                email_msg['From'] = EMAIL_ADDRESS
                recipients = [PERSONAL_EMAIL]
                email_msg['To'] = ', '.join(recipients)

                # Add the message body to the email
                body = '\n\n'.join(messages)
                email_msg.attach(MIMEText(body, 'plain'))

                # Attach files if provided
                if attachments:
                    for file_path in attachments:
                        part = MIMEBase('application', 'octet-stream')
                        with open(file_path, 'rb') as file:
                            part.set_payload(file.read())
                        encoders.encode_base64(part)
                        part.add_header('Content-Disposition', f'attachment; filename={os.path.basename(file_path)}')
                        email_msg.attach(part)

                # Send the email
                server.sendmail(EMAIL_ADDRESS, recipients, email_msg.as_string())

                logger.info(f'Sent email notification')
            except Exception as e:
                logger.error(e)
