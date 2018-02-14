import sys


import suzie
import suzie.plugins
import suzie.ui


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    r = suzie.Router()
    r.load(suzie.plugins.Alarm)
    r.load(suzie.plugins.Ping)
    r.load(suzie.plugins.Notes)
    r.load(suzie.plugins.Addition)
    r.load(suzie.plugins.Pizza)
    r.load(suzie.plugins.Downloader)
    r.add_ui(suzie.ui.CommandLine())
    r.main()


if __name__ == '__main__':
    main(sys.argv[1:])
