import asyncio
import asyncio.streams
import sys


import suzie
import suzie.plugins
import suzie.ui


class TCPServer:
    def __init__(self, addr, port, router, loop=None):
        self.addr = addr
        self.port = port
        self.router = router
        self.loop = loop or asyncio.get_event_loop()

    def start(self):
        self.loop.create_task(asyncio.streams.start_server(
            self._accept_client,
            self.addr, self.port,
            loop=self.loop))

    def _accept_client(self, reader, writer):
        ui = suzie.ui.TCP(reader, writer)
        self.router.add_ui(ui)


def main(args=None):
    if args is None:
        args = sys.argv[:1]

    loop = asyncio.get_event_loop()

    r = suzie.Router(loop=loop)
    r.load(suzie.plugins.Alarm)
    r.load(suzie.plugins.Ping)
    r.load(suzie.plugins.Notes)
    r.load(suzie.plugins.Addition)
    r.load(suzie.plugins.Pizza)
    r.load(suzie.plugins.Downloader)
    r.add_ui(suzie.ui.CommandLine())

    tcp_server = TCPServer('127.0.0.1', 5000, router=r, loop=loop)
    tcp_server.start()

    loop.run_forever()


if __name__ == '__main__':
    main(sys.argv[1:])
