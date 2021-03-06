import json
import datetime as dt

from django import forms
from django.conf import settings
from django.utils.safestring import mark_safe
from zenpy import Zenpy
from zenpy.lib.api_objects import Ticket, CustomField, Comment, User

from govuk_forms.forms import GOVUKForm
from govuk_forms import widgets, fields
import requests

from .fields import AVFileField


class ChangeRequestForm(GOVUKForm):
    name = forms.CharField(
        label='Your full name',
        max_length=255,
        widget=widgets.TextInput()
    )

    email = forms.EmailField(
        label='Your email address',
        widget=widgets.TextInput()
    )

    description = forms.CharField(
        label='What\'s your feedback?',
        widget=widgets.Textarea(),
        help_text=mark_safe(
            'If you\'re reporting a bug, please include'
            '<ol>'
            '<li>1. Enough step by step instructions for us to experience the bug: so we know what to fix.</li>'
            '<li>2. What you\'ve already tried.</li>'
            '<li>3. Your aim: the platform may have an alternative.</li>'
            '</ol>'
        )
    )

    attachment1 = AVFileField(
        label='Please attach screenshots or small data files. Do not submit sensitive data.',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        required=False
    )

    attachment2 = AVFileField(
        label='',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='',
        required=False
    )

    attachment3 = AVFileField(
        label='',
        max_length=255,
        widget=widgets.ClearableFileInput(),
        help_text='',
        required=False
    )

    def create_zendesk_ticket(self):
        zenpy_client = Zenpy(
            subdomain=settings.ZENDESK_SUBDOMAIN,
            email=settings.ZENDESK_EMAIL,
            token=settings.ZENDESK_TOKEN,
        )

        custom_fields = [
            CustomField(id=31281329, value='JupyterHub'),                         # service
            CustomField(id=45522485, value=self.cleaned_data['email']),                 # email         # Phone number
        ]

        formatted_text = (
            'Name: {name}\n'
            'Email: {email}\n'
            'Description: {description}'.format(**self.cleaned_data)
        )

        ticket_audit = zenpy_client.tickets.create(Ticket(
            subject='JupyterHub feedback',
            description=formatted_text,
            custom_fields=custom_fields,
            tags=['jupyterhub'],
            requester=User(
                name=self.cleaned_data['name'],
                email=self.cleaned_data['email'],
            ),
        ))

        attachments = [value for field, value in self.cleaned_data.items() if field.startswith('attachment') and value]

        if attachments:
            uploads = []
            for attachment in attachments:
                upload_instance = zenpy_client.attachments.upload(attachment.temporary_file_path())
                uploads.append(upload_instance.token)

            ticket_audit.ticket.comment = Comment(body=str(attachment), uploads=uploads)

            zenpy_client.tickets.update(ticket_audit.ticket)

        return ticket_audit.ticket.id
