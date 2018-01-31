import abc
import collections
import re
import logging

from . import exc


Undefined = object()


class Message(collections.UserString):
    def __init__(self, text):
        text = re.sub(r'\s+', ' ', text).strip()
        super().__init__(text)


class RequestMessage(Message):
    def __init__(self, text, what):
        super().__init__(text)
        self.what = what


class ClosingMessage(Message):
    def __init__(self, text='Done!'):
        super().__init__(text)


Undefined = object()


class Slots(collections.abc.MutableMapping):
    def __init__(self, fields, *args, **kwargs):
        self._fields = fields
        self._m = {f: Undefined for f in self._fields}

        initial = {}

        if args:
            if not isinstance(args[0], dict):
                raise TypeError(args[0])
            initial = args[0]

        initial.update(kwargs)
        for (k, v) in initial.items():
            self.set(k, v)

    @classmethod
    def for_plugin(cls, plugin, *args, **kwargs):
        return cls(plugin.SLOTS, *args, **kwargs)

    def _check_key(self, key):
        key = str(key)
        if key not in self._fields:
            raise KeyError(key)

    def __getitem__(self, key):
        self._check_key(key)
        return self._m[key]
    get = __getitem__

    def __setitem__(self, key, value):
        self._check_key(key)
        self._m[key] = value
    set = __setitem__

    def __delitem__(self, key):
        self._check_key(key)
        del(self._m[key])
        self._m[key] = Undefined
    delete = __delitem__

    def __iter__(self):
        yield from self._fields.__iter__()

    def __len__(self):
        return len(self._m)

    @property
    def ready(self):
        return all([self.defined(x) for x in self])

    def defined(self, key):
        return self.get(key) != Undefined

    @property
    def missing(self):
        return [key for key in self if self.get(key) == Undefined]

    def __eq__(self, other):
        return dict(self) == dict(other)

    def __repr__(self):
        items = ''.join(["{}={!r}".format(k, v) for (k, v) in self.items()])
        repr = '<{cls} object at 0x{id} {{{items}}}>'.format(
            cls=self.__class__.__name__,
            id=id(self),
            items=items)
        return repr


class Plugin:
    WEIGHT = 0
    TRIGGERS = []
    SLOTS = []

    def __init__(self, logger=None):
        if not self.TRIGGERS:
            errmsg = "No triggers defined"
            raise TypeError(errmsg)

        self.triggers = [
            re.compile(trigger, re.IGNORECASE)
            for trigger in self.__class__.TRIGGERS]

        me = self.__class__.__name__.split('.')[-1]
        self.logger = None or logging.getLogger(me)

    def matches(self, text):
        for trigger in self.triggers:
            m = trigger.search(text)
            if not m:
                continue

            return m.groupdict()

        raise exc.MessageNotMatched(text)

    def setup(self, **params):
        pass

    @abc.abstractmethod
    def extract(self, text):
        raise NotImplementedError()

    @abc.abstractmethod
    def extract_slot(self, slot, text):
        raise NotImplementedError()

    def handle(self, message, state, active_slot=None):
        raise NotImplementedError()

        try:
            res = self.extract_slot(active_slot, str(message))
        except NotImplementedError:
            pass
        except exc.MessageNotMatched:
            return
        else:
            state.set(active_slot, res)
            return

        res = self.extract(str(message))
        if not isinstance(res, dict):
            raise TypeError(res)

        state.update(res)

    @abc.abstractmethod
    def main(self, **kwargs):
        raise NotImplementedError()


class SlottedPlugin(Plugin):
    SLOTS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.SLOTS:
            errmsg = "No slots defined"
            raise TypeError(errmsg)

        self._active_slot = None
        self._slots = {}

    def matches(self, text):
        for trigger in self.triggers:
            m = trigger.search(text)
            if not m:
                continue

            return m.groupdict()

        raise exc.MessageNotMatched(text)

    @abc.abstractmethod
    def validate_slot(self, slot, value):
        raise NotImplementedError()

    @abc.abstractmethod
    def extract_slot(self, slot, text):
        raise NotImplementedError()

    def handle(self, message):
        if self._active_slot:
            value = self.extract_slot(self._active_slot, str(message))
            value = self.validate_slot(self._active_slot, value)
            self._slots[self._active_slot] = value

        missing = set(self.SLOTS) - set(self._slots.keys())
        if not missing:
            return ClosingMessage(self.main(**self._slots))

        else:
            self._active_slot = missing.pop()
            msg = "Give " + self._active_slot
            return Message(msg)

    @abc.abstractmethod
    def main(self, **kwargs):
        raise NotImplementedError()


class Conversation:
    def __init__(self, plugin, **init_params):
        self.plugin = plugin
        self.log = []

        # FIXME: For now we use Plugin.setup but in the future we have
        # to instantiate the Plugin on demand, so init_params will be
        # passed to Plugin.__init__
        plugin.setup(**init_params)

    def handle(self, message, is_trigger=False):
        if not isinstance(message, str):
            raise TypeError(message)

        if self.closed:
            raise TypeError('closed conversation')

        self.log.append(message)
        if not is_trigger:
            resp = self.plugin.handle(message)

        self.log.append(resp)
        return resp

    @property
    def closed(self):
        return self.log and isinstance(self.log[-1], ClosingMessage)


class Conversation__Does_Too_Much:
    def __init__(self, plugin, slots_data=None):
        self.plugin = plugin
        self.log = []
        self.slots = Slots.for_plugin(self.plugin, slots_data or {})

    def get_reply(self):
        if self.slots.ready:
            return ClosingMessage(self.plugin.main(**self.slots))
        else:
            slot = self.slots.missing[0]
            respmsg = "I need '{what}'"
            respmsg = respmsg.format(what=slot)
            return RequestMessage(respmsg, what=self.slots.missing[0])

    def handle(self, message, is_trigger=False):
        if not isinstance(message, str):
            raise TypeError(message)

        if self.closed:
            raise TypeError('closed conversation')

        self.log.append(message)
        if not is_trigger:
            try:
                active_slot = self.log[-2].what
            except IndexError:
                active_slot = None

            self.plugin.handle(message, self.slots, active_slot=active_slot)

        resp = self.get_reply()
        self.log.append(resp)

        return resp

    @property
    def closed(self):
        return self.log and isinstance(self.log[-1], ClosingMessage)


class Router:
    def __init__(self, plugins=None):
        plugins = plugins or []
        self.registry = set(plugins)
        self.conversation = None

    def register(self, plugin):
        self.registry.add(plugin)

    def get_handlers(self, text):
        plugins = sorted(self.registry, key=lambda x: x.WEIGHT)

        for plugin in plugins:
            try:
                init_params = plugin.matches(text)
            except exc.MessageNotMatched:
                continue

            yield plugin, init_params

    def get_handler(self, text):
        try:
            return next(self.get_handlers(text))
        except StopIteration:
            raise exc.MessageNotMatched(text)

    def handle(self, text):
        # Sanitize text
        text = re.subn(r'\s+', ' ', text.strip())[0]

        is_trigger = False

        if self.conversation is None:
            plugin, init_params = self.get_handler(text)
            self.conversation = Conversation(plugin, **init_params)

        response = self.conversation.handle(text, is_trigger=is_trigger)
        if self.conversation.closed:
            self.conversation = None

        return response


class UserInterface:
    @abc.abstractmethod
    def recv(self):
        raise NotImplementedError()

    @abc.abstractmethod
    def send(self, message):
        raise NotImplementedError()

    @abc.abstractmethod
    def set_conversation(self, conversation):
        raise NotImplementedError


class CommandLineInterface(UserInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = '> '

    def recv(self):
        text = input(self.prompt)
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    def send(self, message):
        print(message)

    def set_conversation(self, conversation):
        if conversation is not None:
            prompt = '[{plugin}] '
            plugin_cls = conversation.plugin.__class__
            humanized_cls = plugin_cls.__name__.split('.')[-1].lower()
            prompt = prompt.format(plugin=humanized_cls)
            self.prompt = prompt
        else:
            self.prompt = '> '
