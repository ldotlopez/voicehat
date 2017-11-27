import abc
import enum
import re


import suzie
import homelib


class Plugin:
    TRIGGERS = []
    WEIGHT = 0
    MESSAGES = []

    def __init__(self):
        self.triggers = [
            re.compile(trigger, re.IGNORECASE)
            for trigger in self.__class__.TRIGGERS]

    def t(self, id, **kwargs):
        try:
            return self.MESSAGES[id].format(**kwargs)
        except KeyError:
            return "{id} ({kwargs!r})".format(id=id, kwargs=kwargs)

    def matches(self, text):
        for trigger in self.triggers:
            m = trigger.search(text)
            if not m:
                continue

            args = ()
            kwargs = m.groupdict()
            if not kwargs:
                args = m.groups()

            return args, kwargs

        raise suzie.TextNotMatched(text)

    @abc.abstractmethod
    def reply(self, conversation):
        raise NotImplementedError()


class Notes(Plugin):
    class Stage:
        NONE = 0
        ANNOTATING = 1

    NAME = 'notes'
    TRIGGERS = [
        r'^anota$',
        r'^anota (?P<note>.+)$'
    ]

    MESSAGES = {
        'REQUEST_NOTE': r'What is the message?',
        'OK': r'OK. Got your note: {note}'
    }

    def reply(self, msg, data, note=None):
        if note:
            msg = self.t('OK', note=note)
            return suzie.FinalMessage(msg)

        stage = data.get('stage', self.Stage.NONE)

        if stage == self.Stage.NONE:
            data.set('stage', self.Stage.ANNOTATING)

            msg = self.t('REQUEST_NOTE')
            return suzie.AgentMessage(msg)

        elif stage == self.Stage.ANNOTATING:
            self.save(msg)
            msg = self.t('OK', note=msg)
            return suzie.FinalMessage(msg)

    def save(self, note):
        pass


class Weather(Plugin):
    NAME = 'weather'
    TRIGGERS = [
        r"^lloverá$",
        r"^lloverá (?P<when>.+)$"
    ]
    MESSAGES = {
        'INVALID_WHEN': 'Solo hoy o mañana',
        'REQUEST_WHEN': 'Cuando, ¿hoy o mañana?',
        homelib.Aemet.Probability.YES: 'Si',
        homelib.Aemet.Probability.LIKELY: 'Posiblemente',
        homelib.Aemet.Probability.MAYBE: 'Puede',
        homelib.Aemet.Probability.UNLIKELY: 'No creo',
        homelib.Aemet.Probability.NO: 'No'
    }

    class Stage(enum.Enum):
        NONE = 0
        REQUEST_WHEN = 1

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.aemet = homelib.Aemet()

    def reply(self, msg, data, when=None):
        when_table = {
            'hoy': homelib.Aemet.When.TODAY,
            'mañana': homelib.Aemet.When.TOMORROW,
        }

        when = when or str(msg)
        if not when:
            return suzie.FinalMessage('not')

        try:
            when = when_table[when]
        except KeyError:
            return suzie.FinalMessage('Invalid when')

        res = self.aemet.info(when=when)
        msg = self.t(res)
        return suzie.FinalMessage(msg)
