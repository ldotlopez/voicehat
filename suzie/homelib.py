import datetime
import io
from urllib import request
from xml.etree import ElementTree


class Aemet:
    BASE_URL = 'http://www.aemet.es/xml/municipios/localidad_{loc}.xml'

    class When:
        TODAY = 'today'
        TOMORROW = 'tomorrow'

    class Probability:
        YES = 0
        LIKELY = 1
        MAYBE = 2
        UNLIKELY = 3
        NO = 4

    def __init__(self):
        self.location = 12040
        self._xml = None

    @property
    def url(self):
        return self.BASE_URL.format(loc=self.location)

    def get_xml(self):
        if self._xml is None:
            with request.urlopen(self.url) as fh:
                self._xml = fh.read().decode('iso-8859-15')

        return self._xml

    def info(self, when=When.TODAY):
        now = datetime.datetime.now()
        if when == self.When.TODAY:
            pass
        elif when == self.When.TOMORROW:
            now += datetime.timedelta(days=1)
        else:
            raise ValueError(when)

        fh = io.StringIO(self.get_xml())
        xml = ElementTree.parse(fh).getroot()

        value = '{}-{}-{}'.format(now.year, now.month, now.day)
        expr = 'prediccion/dia[@fecha="{value}"]/{param}'.format(
            value=value,
            param='prob_precipitacion')
        elements = xml.findall(expr)

        probabilities = []

        for e in elements:
            if not e.text:
                continue

            start, end = e.get('periodo').split('-', 1)
            start = int(start)
            end = int(end)

            if when == self.When.TODAY and now.hour > end:
                continue

            probabilities.append((start, end, int(e.text)))

        return self.humanize(probabilities)

    def humanize(self, probs):
        v = sum([value for (_, _, value) in probs]) / len(probs)

        if v > 80:
            return self.Probability.YES
        elif v > 70:
            return self.Probability.LIKELY
        elif v > 30:
            return self.Probability.MAYBE
        elif v > 10:
            return self.Probability.UNLIKELY
        else:
            return self.Probability.NO
