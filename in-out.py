import asyncio
import random
import itertools
import sys
import abc


class Message(str):
    pass


class UserMessage(Message):
    pass


class AgentMessage(Message):
    pass


class Context:
    def __init__(self, user_channel, handler):
        self.user_channel = user_channel
        self.handler = handler
        self.log = []
        self.busy = False


class UserChannel:
    @abc.abstractmethod
    def send(self, msg):
        raise NotImplementedError()

    @abc.abstractmethod
    async def arecv(self, msg):
        raise NotImplementedError


class Plugin:
    NAME = ''
    WEIGHT = 0


class PushMixin:
    async def main(self, loop):
        raise NotImplementedError()


class ExecutorMixin:
    def execute(self):
        raise NotImplementedError()


class SlotFillingMixin:
    SLOTS = []

    def handle(self, msg):
        raise NotImplementedError()


class RandomPush(Plugin, PushMixin, ExecutorMixin):
    NAME = 'push'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.msg_tpl = "Event #{i}"

    async def main(self, loop):
        for i in itertools.count():
            t = random.randint(0, 10) / 10
            await asyncio.sleep(t)

            msg = self.msg_tpl.format(i=i)
            yield AgentMessage(msg)

    def execute(self):
        return AgentMessage('Hello!')


class Stdin(Plugin, PushMixin):
    NAME = 'stdin'

    async def main(self, loop):
        while True:
            line = await loop.run_in_executor(None, sys.stdin.readline)
            line = line.strip()
            yield UserMessage(line)


class App:
    def __init__(self, plugins):
        self.loop = asyncio.get_event_loop()
        self.plugins = []
        for p in plugins:
            self.add_plugin(p)

    def add_plugin(self, plugin):
        if isinstance(plugin, PushMixin):
            self.loop.create_task(self._handle_push(plugin))

        self.plugins.append(plugin)

    async def _handle_push(self, inst):
        async for msg in inst.main(loop=self.loop):
            if isinstance(msg, UserMessage):
                self._handle_user(msg, sender=inst)

            elif isinstance(msg, AgentMessage):
                self._handle_agent(msg, sender=inst)

            else:
                raise TypeError()

    def _handle_user(self, msg, sender):
        for inst in self.plugins:
            if inst == sender:
                continue

            if msg != inst.NAME:
                continue

            print('<=', inst.execute())
            break

    def _handle_agent(self, message, sender):
        msg = '[{sender}] {msg}'
        msg = msg.format(sender=sender.NAME, msg=message)
        print(msg)

    def main(self):
        try:
            self.loop.run_forever()
        except KeyboardInterrupt:
            self.loop.stop()


app = App(plugins=[
    Stdin(),
    RandomPush(),
])
app.main()
