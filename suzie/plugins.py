import suzie


import asyncio
import re
from homelib import aemet


class Ping(suzie.Plugin):
    TRIGGERS = [
        r'^ping$',
        r'^echo (.+)$'
    ]

    def handle(self, context, message):
        if message == 'ping':
            return suzie.ClosingMessage('pong')

        else:
            usertxt = message[5:]
            return suzie.ClosingMessage(usertxt)


class Alarm(suzie.SlottedPlugin):
    TRIGGERS = [
        '^beep in (?P<secs>\d+)$'
    ]
    SLOTS = [
        'secs'
    ]

    def extract_slot(self, slot, text):
        return text

    def validate_slot(self, slot, text):
        return int(text)

    async def _timer(self, ctx, secs):
        await asyncio.sleep(secs)
        ctx.push_message('Wakeup after ' + str(secs))

    def main(self, ctx, secs):
        ctx.create_task(self._timer(ctx, secs))
        return 'OK. I will beep in {}'.format(secs)


class Downloader(suzie.SlottedPlugin):
    TRIGGERS = [
        'download (?P<url>.+)',
        'download'
    ]
    SLOTS = [
        'url'
    ]

    def validate_slot(self, slot, text):
        return text

    def extract_slot(self, slot, text):
        return text

    def main(self, ctx, url):
        msg = 'Downloading {url}'
        msg = msg.format(url=url)
        return msg


class Pizza(suzie.SlottedPlugin):
    TRIGGERS = [
        'pizza'
    ]
    SLOTS = [
        'size',
        'when',
        'ingredients'
    ]

    def validate_slot(self, slot, text):
        return text

    def extract_slot(self, slot, text):
        if slot == 'size':
            m = re.search(r'\b(grande|mediana|familiar|pequeña|normal)\b',
                          text)
            if m:
                return m.group(1)

        elif slot == 'when':
            m = re.search(r'\b(asap|esta noche|ahora|en (.+) horas?)\b', text)
            if m:
                return m.group(1)

        elif slot == 'ingredients':
            return [x.strip() for x in text.split(',')]

    def main(self, ctx, size, when, ingredients):
        return ("pizza pasta, pasta pizza !1!. "
                "(size={}, when={}, ingredients={}".format(
                    size, when, ingredients))


class Events(suzie.Plugin):
    TRIGGERS = [
        'añade cita'
    ]
    SLOTS = [
        'about',
        'where',
        'when'
    ]

    def main(self, ctx, about, where, when):
        msg = "OK. Your appointment: {when} at {where}. Subject: {about}"
        msg = msg.format(when=when, where=where, about=about)
        return suzie.ClosingMessage(msg)


class Notes(suzie.SlottedPlugin):
    TRIGGERS = [
        r'^anota (?P<item>.+)$',
        r'^anota$',
    ]
    SLOTS = [
        'item'
    ]

    def validate_slot(self, slot, text):
        return text

    def extract_slot(self, slot, text):
        return text

    def main(self, ctx, item):
        msg = 'Got your note: {item}'.format(item=item)
        return msg


class Addition(suzie.SlottedPlugin):
    TRIGGERS = [
        r'^(?P<x>\d+)\s*(and|\+)\s*(?P<y>\d+)$',
        r'^add$'
    ]
    SLOTS = ['x', 'y']

    def validate_slot(self, slot, value):
        try:
            return int(value)
        except (ValueError, TypeError) as e:
            raise ValueError(value) from e

    def extract_slot(self, slot, text):
        return text

    def main(self, ctx, x, y):
        msg = "{x} + {y} = {z}"
        msg = msg.format(x=x, y=y, z=x+y)
        return msg


class Weather(suzie.Plugin):
    NAME = 'weather'
    TRIGGERS = [
        r"^lloverá$",
        r"^lloverá (?P<when>.+)\??$"
    ]
    SLOTS = ['when']
    MESSAGES = {
        'INVALID_WHEN': 'Solo hoy o mañana',
        'REQUEST_WHEN': 'Cuando, ¿hoy o mañana?',
        aemet.Probability.YES: 'Si',
        aemet.Probability.LIKELY: 'Posiblemente',
        aemet.Probability.MAYBE: 'Puede',
        aemet.Probability.UNLIKELY: 'No creo',
        aemet.Probability.NO: 'No'
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aemet = aemet.Aemet()

    def main(self, ctx, when):
        when_table = {
            'hoy': aemet.When.TODAY,
            'mañana': aemet.When.TOMORROW,
        }

        res = self.aemet.info(when=when)

        try:
            when = when_table[when]
        except KeyError:
            return suzie.ClosingMessage('Invalid when')

        res = self.aemet.info(when=when)
        msg = self.t(res)
        return suzie.ClosingMessage(msg)


# TRIGGERS = [
#     'lloverá', [
#         Regexp('(hoy|mañana)'),
#     ],
#     'va ha llover', [
#         Regexp('(hoy|mañana)'),
#     ],
#     'tiempo', [
#         Regexp('para (hoy|mañana)'),
#     ]
# ]

# class Weather(Plugin):
#     NAME = 'weather'
#     TRIGGERS = [
#         r'^tiempo en (.+)$',
#         r'^tiempo$'
#     ]

#     def reply(self, conversation, *args, **kwargs):
#         conversation.reply('To be done :-)')
