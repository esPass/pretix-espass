from collections import OrderedDict

from django import forms
from django.dispatch import receiver
from django.utils.translation import ugettext_lazy as _
from pretix.base.signals import (
    register_global_settings, register_ticket_outputs,
)


@receiver(register_ticket_outputs, dispatch_uid='output_espass')
def register_ticket_output(sender, **kwargs):
    from .espass import EspassOutput
    return EspassOutput


@receiver(register_global_settings, dispatch_uid='espass_settings')
def register_global_settings(sender, **kwargs):
    return OrderedDict([

        ('esPass_organizer_name', forms.CharField(
            label='esPass organizer name',
            required=False,
        ))
    ])
