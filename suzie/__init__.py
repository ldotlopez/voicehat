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

    def __init__(self, logger=None):
        if not self.TRIGGERS:
            errmsg = "No triggers defined"
            raise TypeError(errmsg)

        self.triggers = [
            re.compile(trigger, re.IGNORECASE)
            for trigger in self.__class__.TRIGGERS]

        self.logger = None or logging.getLogger(self.NAME)

    @property
    def NAME(self):
        return self.__class__.__name__.split('.')[-1]

    def matches(self, text):
        for trigger in self.triggers:
            m = trigger.search(text)
            if not m:
                continue

            return m.groupdict()

        raise exc.MessageNotMatched(text)

    def setup(self, context, **params):
        pass

    def handle(self, context, message):
        raise NotImplementedError()

    @abc.abstractmethod
    def main(self, context, **kwargs):
        raise NotImplementedError()


class SlottedPlugin(Plugin):
    SLOTS = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        if not self.SLOTS:
            errmsg = "No slots defined"
            raise TypeError(errmsg)

    def setup(self, context, **params):
        for (slot, value) in params.items():
            try:
                self.fill_slot(context.memory, slot, value)
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

    def handle(self, context, message):
        # Try to fill active slot
        active_slot = context.memory.get(ACTIVE_SLOT)
        if active_slot is not None:
            try:
                self.fill_slot(context.memory, active_slot, message)
            except exc.SlotFilingError:
                pass

        # Extract slots from Context.memory
        prefix_len = len(SLOTS_PREFIX)
        slots = {
            k[prefix_len:]: v for (k, v)
            in context.memory.items()
            if k.startswith(SLOTS_PREFIX)
        }

        # Check for missing slots and ask for one or run Plugin.main
        missing = set(self.SLOTS) - set(slots.keys())
        if missing:
            context.memory[ACTIVE_SLOT] = missing.pop()
            msg = "Give " + context.memory[ACTIVE_SLOT]
            return Message(msg)

        else:
            msg = self.main(context, **slots)
            return ClosingMessage(msg)

    @abc.abstractmethod
    def main(self, context, **kwargs):
        raise NotImplementedError()


class Context:
    def __init__(self, plugin_name, ui, push_queue, loop=None):
        self.plugin_name = plugin_name
        self.ui = ui
        self.memory = {}
        self.loop = loop or asyncio.get_event_loop()
        self.push_queue = push_queue

    def create_task(self, coro):
        return self.loop.create_task(coro)

    def push_message(self, message):
        self.push_queue.put_nowait(message)


class Router:
    def __init__(self, plugins=None):
        plugins = plugins or []
        self._ui_tasks = {}
        self.registry = set(plugins)
        self.loop = asyncio.get_event_loop()

    def load(self, plugin_cls):
        self.register(plugin_cls())

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

    async def _handle_ui(self, ui):
        async def _queue_handler():
            while True:
                msg = await push_queue.get()
                await ui.send(msg)

        context = None
        push_queue = asyncio.Queue()
        push_task = self.loop.create_task(_queue_handler())

        while True:
            try:
                msg = await ui.recv()
            except EOFError:
                break

            text = str(msg)

            if context is None:
                try:
                    plugin, init_params = self.get_handler(text)
                except exc.MessageNotMatched:
                    response = "[?] I don't how to handle that"
                    await ui.send(response)
                    continue

                context = Context(plugin_name=plugin.NAME, ui=ui,
                                  push_queue=push_queue)
                plugin.setup(context, **init_params)

            response = plugin.handle(context, text)
            if isinstance(response, ClosingMessage):
                context = None

            await ui.send(response)
            ui.set_context(context)

        push_task.cancel()
        self.remove_ui(ui)

    def add_ui(self, ui):
        task = self.loop.create_task(self._handle_ui(ui))
        self._ui_tasks[ui] = task

    def remove_ui(self, ui):
        del(self._ui_tasks[ui])
        if not self._ui_tasks:
            self.loop.stop()

    def main(self):
        self.loop.run_forever()


class UserInterface:
    @abc.abstractmethod
    async def recv(self):
        raise NotImplementedError()

    @abc.abstractmethod
    async def send(self, message):
        raise NotImplementedError()

    @abc.abstractmethod
    def set_context(self, context):
        raise NotImplementedError


class CommandLineInterface(UserInterface):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.prompt = '> '

    async def recv(self):
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(None, input, self.prompt)
        text = re.sub(r'\s+', ' ', text.strip())
        if text in ['q', 'bye']:
            raise EOFError()

        return text

    async def send(self, message):
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, print, message)

    def set_context(self, context):
        if context is not None:
            prompt = '[{plugin}] '
            prompt = prompt.format(plugin=context.plugin_name)
            self.prompt = prompt
        else:
            self.prompt = '> '
