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

    def reply(self, conv, item=None):
        if item:
            conv.reply_and_close('Got your note: ' + conv.last)
            return

        stage = conv.data.get('stage', self.Stage.NONE)

        if stage == self.Stage.NONE:
            conv.reply('ok, tellme what')
            conv.data['stage'] = self.Stage.ANNOTATING

        elif stage == self.Stage.ANNOTATING:
            conv.reply_and_close('Got your note: ' + conv.last)


class Weather(Plugin):
    NAME = 'weather'
    TRIGGERS = [
        r'^tiempo en (.+)$',
        r'^tiempo$'
    ]

    def reply(self, conversation, *args, **kwargs):
        conversation.reply_and_close('To be done :-)')
