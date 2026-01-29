"""
Custom Mail class that supports SSL for Flask-Mail
Flask-Mail doesn't natively support MAIL_USE_SSL, so we need to extend it
"""
import smtplib
from contextlib import contextmanager
from flask_mail import Mail, email_dispatched
from flask import current_app


class Connection:
    """Simple wrapper for SMTP connection"""
    def __init__(self, host):
        self.host = host

    def send(self, message):
        """Send a message"""
        self.host.sendmail(message.sender, message.send_to, message.as_string())

    def quit(self):
        """Close the connection"""
        if self.host:
            try:
                self.host.quit()
            except:
                pass


class SSLMail(Mail):
    """
    Custom Mail class that supports both TLS and SSL connections
    """

    @contextmanager
    def connect(self):
        """Override connect to support SSL connection"""
        host = current_app.config.get('MAIL_SERVER', 'smtp.gmail.com')
        port = current_app.config.get('MAIL_PORT', 587)
        use_tls = current_app.config.get('MAIL_USE_TLS', True)
        use_ssl = current_app.config.get('MAIL_USE_SSL', False)
        username = current_app.config.get('MAIL_USERNAME')
        password = current_app.config.get('MAIL_PASSWORD')
        timeout = current_app.config.get('MAIL_TIMEOUT', 30)

        conn = None
        try:
            if use_ssl:
                conn = smtplib.SMTP_SSL(host, port, timeout=timeout)
            else:
                conn = smtplib.SMTP(host, port, timeout=timeout)

            if use_tls and not use_ssl:
                conn.starttls()

            if username and password:
                conn.login(username, password)

            yield Connection(conn)

        except Exception:
            if conn:
                try:
                    conn.quit()
                except:
                    pass
            raise

        finally:
            if conn:
                try:
                    conn.quit()
                except:
                    pass
