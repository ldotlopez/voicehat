import suzie


import re
from homelib import aemet


class Downloader(suzie.Plugin):
    TRIGGERS = [
        'download (?P<url>.+)',
        'download'
    ]
    SLOTS = [
        'url'
    ]

    def extract_slot(self, slot, text):
        return text

    def main(self, url):
        msg = 'Downloading {url}'
        msg = msg.format(url=url)
        return msg


class Pizza(suzie.Plugin):
    TRIGGERS = [
        'pizza'
    ]
    SLOTS = [
        'size',
        'when',
        'ingredients'
    ]

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

        raise suzie.MessageNotMatched(slot)

    def main(self, size, when, ingredients):
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

    def main(self, about, where, when):
        msg = "OK. Your appointment: {when} at {where}. Subject: {about}"
        msg = msg.format(when=when, where=where, about=about)
        return suzie.ClosingMessage(msg)


class Notes(suzie.Plugin):
    TRIGGERS = [
        r'^anota$',
        r'^anota (?P<item>.+)$'
    ]
    SLOTS = [
        'item'
    ]

    def main(self, item):
        msg = 'Got your note: {item}'.format(item=item)
        return msg

    def extract(self, msg):
        if msg:
            return {'item': msg}


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

    def main(self, when):
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
