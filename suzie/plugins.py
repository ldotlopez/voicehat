import abc
import re


import suzie


class Plugin:
    TRIGGERS = []
    WEIGHT = 0

    def __init__(self):
        self.triggers = [
            re.compile(trigger, re.IGNORECASE)
            for trigger in self.__class__.TRIGGERS]

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
        r'^anota (?P<item>.+)$'
    ]

    def reply(self, msg, data, item=None):
        if item:
            msg = 'Got your note: ' + item
            return suzie.FinalMessage(msg)

        stage = data.get('stage', self.Stage.NONE)

        if stage == self.Stage.NONE:
            data.set('stage', self.Stage.ANNOTATING)
            return suzie.AgentMessage('ok, tellme what')

        elif stage == self.Stage.ANNOTATING:
            msg = 'Got your note: ' + msg
            return suzie.FinalMessage(msg)


class Weather(Plugin):
    NAME = 'weather'
    TRIGGERS = [
        r'^tiempo en (?P<where>.+)$',
        r'^tiempo$'
    ]

    def reply(self, msg, data, where=None):
        msg = 'To be done :-)'
        return suzie.FinalMessage(msg)
