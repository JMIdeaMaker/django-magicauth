import math

from django.contrib.auth import get_user_model
from django.contrib.sites.shortcuts import get_current_site
from django.core.mail import send_mail
from django.template import loader

from magicauth import settings as magicauth_settings
from django.conf import settings as django_settings
from magicauth.models import MagicToken

import sendgrid
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

sg = sendgrid.SendGridAPIClient(django_settings.SENDGRID_API_KEY)


class SendTokenMixin(object):
    """
    Helper for sending an email containing a link containing the MagicToken.
    """

    def create_token(self, user):
        token = MagicToken.objects.create(user=user)
        return token

    def get_user_from_email(self, user_email):
        """
        Query the DB for the user corresponding to the email.
         - We use get_user_model() instead of User (in case the Django app has customised the User
        class)
         - We use magicauth_settings.EMAIL_FIELD, which is the name of the field in the user
        model. By default "username" but not always.
        """
        user_class = get_user_model()
        email_field = magicauth_settings.EMAIL_FIELD
        field_lookup = {f"{email_field}__iexact": user_email}
        user = user_class.objects.get(**field_lookup)
        return user

    def send_email(self, user, user_email, token, extra_context=None):
        email_subject = magicauth_settings.EMAIL_SUBJECT
        html_template = magicauth_settings.EMAIL_HTML_TEMPLATE
        text_template = magicauth_settings.EMAIL_TEXT_TEMPLATE
        from_email = magicauth_settings.FROM_EMAIL
        context = {
            "token": token,
            "user": user,
            "site": get_current_site(self.request),
            "TOKEN_DURATION_MINUTES": math.floor(magicauth_settings.TOKEN_DURATION_SECONDS / 60),
            "TOKEN_DURATION_SECONDS": magicauth_settings.TOKEN_DURATION_SECONDS,
        }
        if extra_context:
            context.update(extra_context)
        text_message = loader.render_to_string(text_template, context)
        html_message = loader.render_to_string(html_template, context)

        mail = Mail(
            from_email=(
                django_settings.MAGICAUTH_FROM_EMAIL, 
                django_settings.MAGICAUTH_SENDER
            ),
            to_emails=[user_email],
            subject=email_subject,
            html_content=html_message
        )

        sg.send(mail)

    def send_token(self, user_email, extra_context=None):
        user = self.get_user_from_email(user_email)
        token = self.create_token(user)
        self.send_email(user, user_email, token, extra_context)
