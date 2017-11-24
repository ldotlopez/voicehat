#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import abc
import argparse
import collections
import re
import sys


class TextNotMatched(Exception):
    pass


class InternalError(Exception):
    pass


Handler = collections.namedtuple('Handler', [
    'plugin', 'args', 'kwargs'
])


class Response(str):
    pass


class Conversation:
    def __init__(self, text):
        self.log = [text]
        self.opened = True

    def add(self, text):
        self.log.append(text)

    @property
    def reply(self):
        return self.log[-1]


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

        raise TextNotMatched(text)

    @abc.abstractmethod
    def handle(self, *args, **kwargs):
        raise NotImplementedError()


class Notes(Plugin):
    TRIGGERS = [
        r'^anota$',
        r'^apunta (?P<item>.+)$'
    ]

    def reply(self, conversation):
        pass

    def handle(self, item=''):
        if not item:
            return Conversation('ok')

        return Response('apuntado: {}'.format(item))


class Weather(Plugin):
    TRIGGERS = [
        r'^tiempo en (.+)$',
        r'^lloverá$'
    ]

    def handle(self, *args, **kwargs):
        return Response('Ni idea')


class Router:
    def __init__(self):
        self.registry = []

    def register(self, plugin):
        self.conversation = None
        self.registry.append(plugin)

    def get_handlers(self, text):
        plugins = sorted(self.registry, key=lambda x: x.WEIGHT)

        for plugin in plugins:
            try:
                args, kwargs = plugin.matches(text)
            except TextNotMatched:
                continue

            yield Handler(plugin, args, kwargs)

    def get_handler(self, text):
        try:
            return next(self.get_handlers(text))
        except StopIteration:
            raise TextNotMatched(text)

    def handle(self, text):
        # Sanitize text
        text = re.subn(r'\s+', ' ', text.strip())[0]

        # Get handler for this text
        handler = self.get_handler(text)
        return handler.plugin.handle(*handler.args, **handler.kwargs)


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    r = Router()
    r.register(Notes())
    r.register(Weather())

    argparser = argparse.ArgumentParser()
    argparser.add_argument(dest='text', nargs='*')
    args = argparser.parse_args(args)

    text, interactive = ' '.join(args.text), False
    if not text:
        text, interactive = input('> '), True

    running = True
    while running:
        running = False
        if not interactive:
            running = False

        if text == 'bye':
            running = False
            continue

        try:
            resp = r.handle(text)

        except TextNotMatched:
            print("[?] I don't how to handle that")
            continue

        except InternalError as e:
            print("[!] Internal error: {e!r}".format(e=e.args[0]))
            continue

        if isinstance(resp, Response):
            print(resp)

        elif isinstance(resp, Conversation):
            print(resp.reply)

        else:
            print("[!] Can't handle respose")
            continue


if __name__ == '__main__':
    main(sys.argv[1:])
