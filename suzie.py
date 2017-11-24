#!/usr/bin/env python3
# -*- encoding: utf-8 -*-

import argparse
import re
import sys


class TextNotMatched(Exception):
    pass


class InternalError(Exception):
    pass


class Plugin:
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

    def handle(self, text):
        return text


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

    def handle(self, text):
        text = re.subn(r'\s+', ' ', text)[0]

        plugins = sorted(self.registry, key=lambda x: x.WEIGHT)
        for plugin in plugins:
            m = plugin.matches(text)
            if not m:
                continue

            args = ()
            kwargs = m.groupdict()
            if not kwargs:
                args = m.groups()

            try:
                return plugin.handle(*args, **kwargs)
            except SyntaxError:
                raise
            except Exception as e:
                raise InternalError(e) from e

        raise TextNotMatched(text)


def main():
    r = Router()
    r.register(Notes())
    r.register(Weather())

    argparser = argparse.ArgumentParser()
    argparser.add_argument(dest='text', nargs='+')
    args = argparser.parse_args(sys.argv[1:])

    try:
        resp = r.handle(' '.join(args.text))
        print(resp)

    except TextNotMatched:
        print("[?]", "I don't how to handle that")

    except InternalError as e:
        print("[!] Internal error: {e!r}".format(e=e.args[0]))


if __name__ == '__main__':
    main()
