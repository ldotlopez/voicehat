import abc
import re


import suzie


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
        r'^tiempo en (?P<where>.+)$',
        r'^tiempo$'
    ]
    MESSAGES = {
        'TO_BE_DONE': 'To be done :-)'
    }

    def reply(self, msg, data, where=None):
        msg = self.t('TO_BE_DONE')
        return suzie.FinalMessage(msg)
