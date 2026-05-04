from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse


def send_team_invitation_email(invitation, request=None):
    """
    Envoie un email d'invitation à rejoindre une équipe
    """
    # Construire les URLs d'acceptation et de refus
    base_url = settings.BACKEND_URL
    
    accept_url = f"{base_url}/api/invitations/accept/{invitation.token}"
    decline_url = f"{base_url}/api/invitations/decline/{invitation.token}"
    
    # Contexte pour le template
    context = {
        'invitee_name': invitation.invitee.get_full_name() or invitation.invitee.username,
        'inviter_name': invitation.inviter.get_full_name() or invitation.inviter.username,
        'team_name': invitation.team.nom,
        'contest_name': invitation.team.contest.title,
        'contest_start': invitation.team.contest.date_debut,
        'accept_url': accept_url,
        'decline_url': decline_url,
        'expires_at': invitation.expires_at,
    }
    
    # Sujet de l'email
    subject = f"Invitation à rejoindre l'équipe {invitation.team.nom}"
    
    # Message HTML
    html_message = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <style>
            body {{
                font-family: Arial, sans-serif;
                line-height: 1.6;
                color: #333;
                max-width: 600px;
                margin: 0 auto;
                padding: 20px;
            }}
            .header {{
                background-color: #4CAF50;
                color: white;
                padding: 20px;
                text-align: center;
                border-radius: 5px 5px 0 0;
            }}
            .content {{
                background-color: #f9f9f9;
                padding: 30px;
                border: 1px solid #ddd;
            }}
            .button-container {{
                text-align: center;
                margin: 30px 0;
            }}
            .button {{
                display: inline-block;
                padding: 12px 30px;
                margin: 0 10px;
                text-decoration: none;
                border-radius: 5px;
                font-weight: bold;
                font-size: 16px;
            }}
            .accept-button {{
                background-color: #4CAF50;
                color: white;
            }}
            .decline-button {{
                background-color: #f44336;
                color: white;
            }}
            .info-box {{
                background-color: #e3f2fd;
                border-left: 4px solid #2196F3;
                padding: 15px;
                margin: 20px 0;
            }}
            .footer {{
                text-align: center;
                color: #777;
                font-size: 12px;
                margin-top: 20px;
            }}
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🎯 Invitation à rejoindre une équipe</h1>
        </div>
        
        <div class="content">
            <p>Bonjour <strong>{context['invitee_name']}</strong>,</p>
            
            <p><strong>{context['inviter_name']}</strong> vous invite à rejoindre l'équipe 
            <strong>{context['team_name']}</strong> pour participer au contest :</p>
            
            <div class="info-box">
                <h3 style="margin-top: 0;">📋 {context['contest_name']}</h3>
                <p><strong>Début :</strong> {context['contest_start'].strftime('%d/%m/%Y à %H:%M')}</p>
            </div>
            
            <p>Souhaitez-vous accepter cette invitation ?</p>
            
            <div class="button-container">
                <a href="{context['accept_url']}" class="button accept-button">
                    ✓ Accepter l'invitation
                </a>
                <a href="{context['decline_url']}" class="button decline-button">
                    ✗ Refuser l'invitation
                </a>
            </div>
            
            <p style="color: #777; font-size: 14px;">
                ⏰ Cette invitation expire le {context['expires_at'].strftime('%d/%m/%Y à %H:%M')}
            </p>
        </div>
        
        <div class="footer">
            <p>Cet email a été envoyé automatiquement, merci de ne pas y répondre.</p>
        </div>
    </body>
    </html>
    """
    
    # Message texte brut (fallback)
    text_message = f"""
Bonjour {context['invitee_name']},

{context['inviter_name']} vous invite à rejoindre l'équipe {context['team_name']} 
pour participer au contest "{context['contest_name']}".

Début du contest : {context['contest_start'].strftime('%d/%m/%Y à %H:%M')}

Pour accepter l'invitation : {context['accept_url']}
Pour refuser l'invitation : {context['decline_url']}

Cette invitation expire le {context['expires_at'].strftime('%d/%m/%Y à %H:%M')}

Cet email a été envoyé automatiquement, merci de ne pas y répondre.
    """
    
    # Envoi de l'email
    try:
        send_mail(
            subject=subject,
            message=text_message,
            from_email=settings.EMAIL_HOST_USER,
            recipient_list=[invitation.invitee.email],
            html_message=html_message,
            fail_silently=False,
        )
        return True
    except Exception as e:
        print(f"Erreur lors de l'envoi de l'email : {e}")
        return False