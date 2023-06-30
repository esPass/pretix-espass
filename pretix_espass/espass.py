import json
import os
import tempfile
from collections import OrderedDict
from typing import Tuple
from zipfile import ZipFile

import pytz
from django import forms
from django.core.files.storage import default_storage
from django.utils.translation import gettext, gettext_lazy as _  # NOQA
from pretix.base.models import Order
from pretix.base.ticketoutput import BaseTicketOutput
from pretix.multidomain.urlreverse import build_absolute_uri

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
        tz = pytz.timezone(order.event.settings.timezone)

        ticket = str(order_position.item)
        if order_position.variation:
            ticket += ' - ' + str(order_position.variation)

        pass_id = '%s-%s' % (order.event.slug, order.code)

        data = {'app': 'pretix',
                'type': 'EVENT',
                'description': str(order.event.name),
                'id': pass_id,
                'accentColor': order.event.settings.primary_color,
                'calendarTimespan': {
                    "from": order.event.date_from.isoformat(),
                },
                'locations': [
                    # intentionally empty - will be populated later
                ],
                'barCode': {
                    "format": "QR_CODE",
                    "message": order_position.secret,
                    "alternativeText": order_position.secret
                },
                'fields': [
                    {
                        "hide": False,
                        "label": gettext('Product'),
                        "value": ticket
                    },
                    {
                        "hide": True,
                        "label": gettext('Ordered by'),
                        "value": order.email
                    },
                    {
                        "hide": True,
                        "label": gettext('Order code'),
                        "value": order.code
                    },
                    {
                        "hide": True,
                        "label": gettext('Organizer'),
                        "value": str(order.event.organizer)
                    },
                    {
                        "hide": False,
                        "label": gettext('From'),
                        "value": order.event.get_date_from_display(tz)
                    },
                    {
                        "hide": True,
                        "label": gettext('Website'),
                        "value": build_absolute_uri(order.event, 'presale:event.index')
                    },
                ]
                }

        if order.event.date_to:
            data["calendarTimespan"]["to"] = order.event.date_to.isoformat()
            data["fields"].append({
                "label": gettext('To'),
                "value": order.event.get_date_to_display(tz),
                "hide": False
            })

        if order.event.seating_plan_id is not None:
            if order_position.seat:
                if order_position.seat.zone_name:
                    data["fields"].append({
                        "label": gettext('Zone'),
                        "value": order_position.seat.zone_name,
                        "hide": False
                    })
                if order_position.seat.row_name:
                    data["fields"].append({
                        "label": gettext('Row'),
                        "value": order_position.seat.row_name,
                        "hide": False
                    })
                if order_position.seat.seat_number:
                    data["fields"].append({
                        "label": gettext('Seat'),
                        "value": order_position.seat.seat_number,
                        "hide": False
                    })
            else:
                data["fields"].append({
                    "label": gettext('Seat'),
                    "value": gettext('General admission'),
                    "hide": False
                })

        if order_position.attendee_name:
            data["fields"].append({
                "label": gettext('Attendee name'),
                "value": order_position.attendee_name,
                "hide": False
            })

        if order.event.settings.contact_mail:
            data["fields"].append({
                "label": gettext('Organizer contact'),
                "value": order.event.settings.contact_mail,
                "hide": False
            })

        if self.event.settings.ticketoutput_espass_latitude and self.event.settings.ticketoutput_espass_longitude:
            data["locations"].append({
                "lat": self.event.settings.ticketoutput_espass_latitude,
                "lon": self.event.settings.ticketoutput_espass_longitude
            })
            if self.event.settings.ticketoutput_espass_location_name:
                data["locations"][-1]["name"] = self.event.settings.ticketoutput_espass_location_name

        with tempfile.TemporaryDirectory() as tmp_dir:
            with ZipFile(os.path.join(tmp_dir, 'tmp.zip'), 'w') as zipf:
                icon_file = self.event.settings.get('ticketoutput_espass_icon')
                zipf.writestr('icon.png', default_storage.open(icon_file.name, 'rb').read())

                logo_file = self.event.settings.get('ticketoutput_espass_logo')
                zipf.writestr('logo.png', default_storage.open(logo_file.name, 'rb').read())

                zipf.writestr('main.json', json.dumps(data, indent=4, separators=(',', ':')))

            with open(os.path.join(tmp_dir, 'tmp.zip'), 'rb') as zipf:
                filename = 'pass_{}-{}.espass'.format(order.event.slug, order.code)
                return filename, 'application/vnd.espass-espass+zip', zipf.read()
