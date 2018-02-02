import abc
import asyncio
import collections
import re
import logging

from . import exc


ACTIVE_SLOT = 'slots.active-slot'
SLOTS_PREFIX = 'slots.slot-'


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


class Plugin:
    WEIGHT = 0
    TRIGGERS = []
    SLOTS = []

    def __init__(self, bridge, logger=None):
        if not self.TRIGGERS:
            errmsg = "No triggers defined"
            raise TypeError(errmsg)

        self.triggers = [
            re.compile(trigger, re.IGNORECASE)
            for trigger in self.__class__.TRIGGERS]

        me = self.__class__.__name__.split('.')[-1]

        self.bridge = bridge
        self.logger = None or logging.getLogger(me)

    def matches(self, text):
        for trigger in self.triggers:
            m = trigger.search(text)
            if not m:
                continue

            return m.groupdict()

        raise exc.MessageNotMatched(text)

    def setup(self, memory, **params):
        pass

    def handle(self, memory, message):
        raise NotImplementedError()

    @abc.abstractmethod
    def main(self, memory, **kwargs):
        raise NotImplementedError()


class SlottedPlugin(Plugin):
    SLOTS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.SLOTS:
            errmsg = "No slots defined"
            raise TypeError(errmsg)

    def setup(self, memory, **params):
        for (slot, value) in params.items():
            try:
                self.fill_slot(memory, slot, value)
            except exc.SlotFilingError:
                pass

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

    def fill_slot(self, memory, slot, message):
        value = self.extract_slot(slot, str(message))
        if not value:
            raise exc.SlotFilingError(slot, message)

        try:
            value = self.validate_slot(slot, value)
        except ValueError as e:
            errmsg = "Invalid value '{value}' for slot '{slot}'"
            errmsg = errmsg.format(value=value, slot=slot)
            raise exc.SlotFilingError(slot, message, errmsg) from e

        memory[SLOTS_PREFIX + slot] = value

    def handle(self, memory, message):
        def _get_slots():
            n = len(SLOTS_PREFIX)
            return {
                k[n:]: v for (k, v)
                in memory.items()
                if k.startswith(SLOTS_PREFIX)}

        slot = memory.get(ACTIVE_SLOT)
        if slot is not None:
            try:
                self.fill_slot(memory, slot, message)
            except exc.SlotFilingError:
                pass

        missing = set(self.SLOTS) - set(_get_slots().keys())
        if not missing:
            return ClosingMessage(self.main(**_get_slots()))

        else:
            memory[ACTIVE_SLOT] = missing.pop()
            msg = "Give " + memory[ACTIVE_SLOT]
            return Message(msg)

    @abc.abstractmethod
    def main(self, **kwargs):
        raise NotImplementedError()


class Conversation:
    def __init__(self, plugin, **init_params):
        self.plugin = plugin
        self.log = []
        self.memory = {}

        # FIXME: For now we use Plugin.setup but in the future we have
        # to instantiate the Plugin on demand, so init_params will be
        # passed to Plugin.__init__
        plugin.setup(self.memory, **init_params)

    def handle(self, message, is_trigger=False):
        if not isinstance(message, str):
            raise TypeError(message)

        if self.closed:
            raise TypeError('closed conversation')

        self.log.append(message)
        if not is_trigger:
            resp = self.plugin.handle(self.memory, message)

        self.log.append(resp)
        return resp

    @property
    def closed(self):
        return self.log and isinstance(self.log[-1], ClosingMessage)


class BridgeAPI:
    def __init__(self, push_queue, loop=None):
        self._loop = loop or asyncio.get_event_loop()
        self._push_queue = push_queue

    def create_task(self, coro):
        return self._loop.create_task(coro)

    def push_message(self, message):
        self._push_queue.put_nowait(message)


class Router:
    def __init__(self, ui, plugins=None):

        plugins = plugins or []
        self.registry = set(plugins)
        self.ui = ui
        self.conversation = None
        self.loop = asyncio.get_event_loop()
        self.queue = asyncio.Queue()

        self.bridge = BridgeAPI(push_queue=self.queue, loop=self.loop)

    def load(self, plugin_cls):
        self.register(plugin_cls(self.bridge))

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

    def main(self):

        async def _queue_handler():
            while True:
                msg = await self.queue.get()
                print("Got msg from queue:", msg)

        async def _main():
            while True:
                msg = await self.ui.recv()

                if self.conversation is None and msg in ['bye', 'q']:
                    self.loop.stop()
                    break

                try:
                    resp = self.handle(msg)
                except exc.MessageNotMatched:
                    resp = "[?] I don't how to handle that"
                    await self.ui.send(resp)
                    continue

                self.ui.set_conversation(self.conversation)
                await self.ui.send(resp)

        self.loop.create_task(_queue_handler())
        self.loop.create_task(_main())
        self.loop.run_forever()


class UserInterface:
    @abc.abstractmethod
    async def recv(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def send(self, message):
        raise NotImplementedError()

    @abc.abstractmethod
    def set_conversation(self, conversation):
        raise NotImplementedError


class CommandLineInterface(UserInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = '> '

    async def recv(self):
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, input, self.prompt)
        text = re.sub(r'\s+', ' ', text.strip())
        return text

    async def send(self, message):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, print, message)

    def set_conversation(self, conversation):
        if conversation is not None:
            prompt = '[{plugin}] '
            plugin_cls = conversation.plugin.__class__
            humanized_cls = plugin_cls.__name__.split('.')[-1].lower()
            prompt = prompt.format(plugin=humanized_cls)
            self.prompt = prompt
        else:
            self.prompt = '> '
