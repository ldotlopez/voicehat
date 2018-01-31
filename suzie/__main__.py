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

    ui = suzie.CommandLineInterface()

    while True:
        msg = ui.recv()

        if not r.in_conversation and msg in ['bye', 'q']:
            break

        try:
            resp = r.handle(msg)
        except suzie.exc.MessageNotMatched:
            resp = "[?] I don't how to handle that"
            ui.send(resp)
            continue

        ui.set_conversation(r.conversation)
        ui.send(resp)


if __name__ == '__main__':
    main(sys.argv[1:])
