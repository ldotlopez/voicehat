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


PluginMatch = collections.namedtuple('PluginMatch', ['plugin', 'match'])

# class Response:
#     def __init__(self, text):
#         self.text = text

#     def __str__(self):
#         return self.text


# class SimpleResponse(Response):
#     pass


# class Conversation(Response):
#     pass


# class EndConversation(Response):
#     pass

class Response(str):
    def is_final(self):
        return True


class FinalResponse(Response):
    pass


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
            if m:
                return m

        return None

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
            m = plugin.matches(text)
            if not m:
                continue

            yield PluginMatch(plugin, m)

    def get_handler(self, text):
        g = self.get_handlers(text)
        try:
            return next(g)
        except StopIteration:
            raise TextNotMatched(text)

    def handle(self, text):
        text = re.subn(r'\s+', ' ', text.strip())[0]

        handler = self.get_handler(text)

        args = ()
        kwargs = handler.match.groupdict()
        if not kwargs:
            args = handler.match.groups()

        return handler.plugin.handle(*args, **kwargs)


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
