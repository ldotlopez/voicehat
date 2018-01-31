import sys


import suzie
import suzie.plugins


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    r = suzie.Router()
    r.register(suzie.plugins.Notes())
    r.register(suzie.plugins.Pizza())
    r.register(suzie.plugins.Downloader())

    user = suzie.StdIO()

    while True:
        msg = user.recv()

        if not r.in_conversation and msg in ['bye', 'q']:
            break

        try:
            import ipdb; ipdb.set_trace(); pass
            resp = r.handle(msg)
        except suzie.MessageNotMatched:
            resp = "[?] I don't how to handle that"

        user.send(resp)


if __name__ == '__main__':
    main(sys.argv[1:])
