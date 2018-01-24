import suzie
from homelib import aemet


class Notes(suzie.Plugin):
    TRIGGERS = [
        r'^anota$',
        r'^anota (?P<item>.+)$'
    ]
    STATE_SLOTS = [
        'item'
    ]

    def main(self, item):
        msg = 'Got your note: {item}'.format(item=item)
        return suzie.ClosingMessage(msg)

    def extract(self, msg):
        if msg:
            return {'item': msg}


class Weather(suzie.Plugin):
    NAME = 'weather'
    TRIGGERS = [
        r"^lloverá$",
        r"^lloverá (?P<when>.+)\??$"
    ]
    STATE_SLOTS = ['when']
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
