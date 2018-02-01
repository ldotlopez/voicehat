import sys


import suzie
import suzie.plugins


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    ui = suzie.CommandLineInterface()

    r = suzie.Router(ui)
    r.register(suzie.plugins.Notes())
    r.register(suzie.plugins.Addition())
    r.register(suzie.plugins.Pizza())
    r.register(suzie.plugins.Downloader())
    r.main()


if __name__ == '__main__':
    main(sys.argv[1:])
