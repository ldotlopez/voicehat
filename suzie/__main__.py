import sys


import suzie
import suzie.plugins


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    r = suzie.Router()
    r.load(suzie.plugins.Alarm)
    r.load(suzie.plugins.Notes)
    r.load(suzie.plugins.Addition)
    r.load(suzie.plugins.Pizza)
    r.load(suzie.plugins.Downloader)
    r.add_ui(suzie.CommandLineInterface())
    r.main()

    # ui = suzie.CommandLineInterface()

    # while True:
    #     msg = ui.recv()

    #     if r.conversation is None and msg in ['bye', 'q']:
    #         break

    #     try:
    #         resp = r.handle(msg)
    #     except suzie.exc.MessageNotMatched:
    #         resp = "[?] I don't how to handle that"
    #         ui.send(resp)
    #         continue

    #     ui.set_conversation(r.conversation)
    #     ui.send(resp)


if __name__ == '__main__':
    main(sys.argv[1:])
