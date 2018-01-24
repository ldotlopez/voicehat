import collections
import enum
import re
import types


class MessageNotMatched(Exception):
    pass


class Message(collections.UserString):
    def __init__(self, text):
        text = re.sub(r'\s+', ' ', text).strip()
        super().__init__(text)


class InformationRequiredMessage(Message):
    def __init__(self, text, what):
        super().__init__(text)
        self.what = what


class ClosingMessage(Message):
    def __init__(self, text='Done!'):
        super().__init__(text)


class Plugin:
    WEIGHT = 0
    TRIGGERS = []
    STATE_SLOTS = []

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

        raise MessageNotMatched(text)

    def missing_slots(self, state):
        return set(self.STATE_SLOTS) - set(state.keys())

    def get_request(self, state):
        missing_slots = self.missing_slots(state)
        slot = missing_slots.pop()
        msg = "I need information for {slot}"
        msg = msg.format(slot=slot)
        return InformationRequiredMessage(msg, slot)

    def handle(self, text, state):
        r = self.extract(text)

        if isinstance(r, types.GeneratorType):
            while True:
                try:
                    k, v = next(r)
                except StopIteration:
                    break

                state[k] = v

        elif isinstance(r, dict):
            state.update(r)

        elif isinstance(r, tuple):
            k, v = r
            state[k] = v

        missing_slots = self.missing_slots(state)
        if not missing_slots:
            return self.main(**state)
        else:
            return self.get_request(state)

    def main(self, **kwargs):
        raise NotImplementedError()


class Turn(enum.Enum):
    USER = 0
    AGENT = 1


class Conversation:
    def __init__(self, plugin, message=None, state=None):
        if not isinstance(plugin, Plugin):
            raise TypeError(plugin)

        self.plugin = plugin
        self.turn = Turn.USER  # Conversations are always initiated by user
        self.state = state or {}
        self.log = []
        if message:
            self.handle(message)

    def handle(self, message):
        def _swap_turn():
            self.turn = Turn.USER if self.turn == Turn.AGENT else Turn.AGENT

        if not isinstance(message, (Message, str)):
            raise TypeError(message)

        if self.turn != Turn.USER:
            raise TypeError(self.turn)

        if self.closed:
            raise TypeError('closed conversation')

        # Add conversation to log and change turn
        self.log.append(message)
        _swap_turn()

        if len(self.log) == 1:
            if not self.plugin.missing_slots(self.state):
                resp = self.plugin.main(**self.state)
            elif not self.state:
                resp = self.plugin.get_request(self.state)
            else:
                resp = self.plugin.handle(message, self.state)
        else:
            resp = self.plugin.handle(message, self.state)

        self.log.append(resp)
        _swap_turn()

        return resp

    @property
    def last(self):
        try:
            return self.log[-1]
        except IndexError:
            return None

    @property
    def closed(self):
        return self.last is not None and isinstance(self.last, ClosingMessage)


class Router:
    def __init__(self, plugins=None):
        plugins = plugins or []
        self.registry = set(plugins)
        self.conversation = None

    @property
    def prompt(self):
        if self.conversation is None:
            return '> '
        else:
            return '[' + self.conversation.plugin.__class__.__name__ + '] '

    @property
    def in_conversation(self):
        return self.conversation and not self.conversation.closed

    def register(self, plugin):
        self.registry.add(plugin)

    def get_handlers(self, text):
        plugins = sorted(self.registry, key=lambda x: x.WEIGHT)

        for plugin in plugins:
            try:
                args, kwargs = plugin.matches(text)
            except MessageNotMatched:
                continue

            yield plugin, args, kwargs

    def get_handler(self, text):
        try:
            return next(self.get_handlers(text))
        except StopIteration:
            raise MessageNotMatched(text)

    def handle(self, text):
        # Sanitize text
        text = re.subn(r'\s+', ' ', text.strip())[0]

        if self.conversation is None:
            # Open a new conversation
            plugin, args, kwargs = self.get_handler(text)
            self.conversation = Conversation(plugin, state=kwargs)

        response = self.conversation.handle(text)

        if self.conversation.closed:
            self.conversation = None

        return response
