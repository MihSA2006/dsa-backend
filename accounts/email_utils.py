# accounts/email_utils.py
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, Email, To, Content
from django.conf import settings
import logging

logger = logging.getLogger(__name__)

def send_email_sendgrid(to_email, subject, html_content):
    """
    Envoie un email via l'API SendGrid
    
    Args:
        to_email (str): Email du destinataire
        subject (str): Sujet de l'email
        html_content (str): Contenu HTML de l'email
    
    Returns:
        bool: True si envoyé, False sinon
    """
    try:
        message = Mail(
            from_email=Email(settings.DEFAULT_FROM_EMAIL),
            to_emails=To(to_email),
            subject=subject,
            html_content=Content("text/html", html_content)
        )
        
        sg = SendGridAPIClient(settings.SENDGRID_API_KEY)
        response = sg.send(message)
        
        logger.info(f"✅ Email envoyé à {to_email} - Status: {response.status_code}")
        return True
        
    except Exception as e:
        logger.error(f"❌ Erreur SendGrid pour {to_email}: {str(e)}")
        return False