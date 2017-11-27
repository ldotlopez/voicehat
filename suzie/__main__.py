import argparse
import sys


import suzie
from suzie import plugins


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    r = suzie.Router()
    r.register(plugins.Notes())
    r.register(plugins.Weather())

    argparser = argparse.ArgumentParser()
    argparser.add_argument(dest='text', nargs='*')
    args = argparser.parse_args(args)

    text = ' '.join(args.text)
    if not text:
        text = input(r.prompt)

    running = True
    while running:
        if not r.in_conversation and text == 'bye':
            running = False
            continue

        try:
            resp = r.handle(text)
            print(resp)

        except suzie.TextNotMatched:
            print("[?] I don't how to handle that")
            continue

        except suzie.InternalError as e:
            print("[!] Internal error: {e!r}".format(e=e.args[0]))
            continue

        finally:
            text = input(r.prompt)


if __name__ == '__main__':
    main(sys.argv[1:])
