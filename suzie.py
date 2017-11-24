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

    def handle(self, item=''):
        return 'apuntado: {}'.format(item)


class Weather(Plugin):
    TRIGGERS = [
        r'^tiempo en (.+)$',
        r'^lloverá$'
    ]


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


def main():
    r = Router()
    r.register(Notes())
    r.register(Weather())

    argparser = argparse.ArgumentParser()
    argparser.add_argument(dest='text', nargs='*')
    args = argparser.parse_args(sys.argv[1:])

    text = ' '.join(args.text)
    if not text:
        text = input('> ')

    while True:
        try:
            resp = r.handle(text)

        except TextNotMatched:
            print("[?]", "I don't how to handle that")
            break

        except InternalError as e:
            print("[!] Internal error: {e!r}".format(e=e.args[0]))
            break

        if resp.is_final:
            print(resp)
            break

        else:
            raise NotImplementedError()


if __name__ == '__main__':
    main()
