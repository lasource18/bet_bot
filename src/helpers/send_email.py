import os
import sys

from logging import Logger
from dotenv import load_dotenv

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
    try:
        with smtplib.SMTP_SSL(EMAIL_HOST, EMAIL_PORT, context=context) as server:
            if len(messages) > 0:
                server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)

                # Create a multipart message
                email_msg = MIMEMultipart()
                email_msg['Subject'] = subject
                email_msg['From'] = EMAIL_ADDRESS

                if not attachments:
                    recipients = [PERSONAL_EMAIL, EMAIL_SMS]
                    # recipients = [PERSONAL_EMAIL]
                else:
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
        e_type, e_object, e_traceback = sys.exc_info()
        e_filename = os.path.split(
            e_traceback.tb_frame.f_code.co_filename
        )[1]
        e_line_number = e_traceback.tb_lineno
        logger.error(f'{e}, type: {e_type}, filename: {e_filename}, line: {e_line_number}')
