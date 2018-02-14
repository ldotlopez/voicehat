import abc
import asyncio
import re


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


class CommandLine(UserInterface):
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
