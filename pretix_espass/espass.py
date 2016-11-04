import tempfile
from collections import OrderedDict
from zipfile import ZipFile

from typing import Tuple
import os
import json
from django import forms
from django.utils.translation import ugettext, ugettext_lazy as _
from django.core.files.storage import default_storage
from pretix.base.models import Order
from pretix.base.ticketoutput import BaseTicketOutput

from .forms import PNGImageField


class EspassOutput(BaseTicketOutput):
    identifier = 'espass'
    verbose_name = 'esPass Tickets'
    download_button_icon = 'fa-mobile'
    download_button_text = 'esPass'

    @property
    def settings_form_fields(self) -> dict:
        return OrderedDict(
            list(super().settings_form_fields.items()) + [
                ('icon',
                 PNGImageField(
                     label=_('Event icon'),
                     help_text=_('We suggest an upload size of 96x96 pixels - the display size is 48dp'),
                     required=True,
                 )),
                ('logo',
                 PNGImageField(
                     label=_('Event logo'),
                     help_text=_('Upload a nice big image - size depends on the device - example size 800x600'),
                     required=True,
                 )),
                ('location_name',
                 forms.CharField(
                     label=_('Event location name'),
                     required=False
                 )),
                ('latitude',
                 forms.FloatField(
                     label=_('Event location latitude'),
                     required=False
                 )),
                ('longitude',
                 forms.FloatField(
                     label=_('Event location longitude'),
                     required=False
                 )),
            ]
        )

    def generate(self, order_position: Order) -> Tuple[str, str, str]:
        order = order_position.order

        ticket = str(order_position.item)
        if order_position.variation:
            ticket += ' - ' + str(order_position.variation)

        pass_id = '%s-%s' % (order.event.slug, order.code)

        data = {'type': 'EVENT',
                'description': str(order.event.name),
                'id': pass_id,
                'wtf': "1",
                'locations': [

                ],
                'fields': [
                    {
                        "hide": False,
                        "label": ugettext('Product'),
                        "value": ticket
                    },
                    {
                        "hide": True,
                        "label": ugettext('Ordered by'),
                        "value": order.email
                    },
                    {
                        "hide": True,
                        "label": ugettext('Order code'),
                        "value": order.code
                    },
                    {
                        "hide": True,
                        "label": ugettext('Organizer'),
                        "value": str(order.event.organizer)
                    },
                ]
                }

        if order_position.attendee_name:
            data["fields"].append({
                "label": ugettext('Attendee name'),
                "value": order_position.attendee_name,
                "hide": False
            })

        if order.event.settings.contact_mail:
            data["fields"].append({
                "label": ugettext('Organizer contact'),
                "value": order.event.settings.contact_mail,
                "hide": False
            })

        if self.event.settings.ticketoutput_espass_latitude and self.event.settings.ticketoutput_espass_longitude:
            data["locations"].append({
                "name": self.event.settings.ticketoutput_espass_location_name,
                "lat": self.event.settings.ticketoutput_espass_latitude,
                "lon": self.event.settings.ticketoutput_espass_longitude
            })

        with tempfile.TemporaryDirectory() as tmp_dir:
            with ZipFile(os.path.join(tmp_dir, 'tmp.zip'), 'w') as zipf:

                icon_file = self.event.settings.get('ticketoutput_espass_icon')
                zipf.writestr('icon.png', default_storage.open(icon_file.name, 'rb').read())

                logo_file = self.event.settings.get('ticketoutput_espass_logo')
                zipf.writestr('logo.png', default_storage.open(logo_file.name, 'rb').read())

                zipf.writestr('main.json', json.dumps(data, indent=4, separators=(',', ':')))

            with open(os.path.join(tmp_dir, 'tmp.zip'), 'rb') as zipf:
                filename = 'foo_{}-{}.espass'.format(order.event.slug, order.code)
                return filename, 'application/vnd.espass-espass+zip', zipf.read()
