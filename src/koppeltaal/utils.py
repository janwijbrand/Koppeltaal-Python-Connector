import datetime


class UTC(datetime.tzinfo):

    def utcoffset(self, dt):
        return datetime.timedelta(0)

    def tzname(self, dt):
        return "UTC"

    def dst(self, dt):
        return datetime.timedelta(0)

utc = UTC()


def strip_history_from_link(link):
    return link.split('/_history/', 1)[0]


def json2links(data):
    links = {}
    for link in data.get('link', []):
        links[link['rel']] = link['href']
    return links


def now():
    return datetime.datetime.utcnow().replace(microsecond=0, tzinfo=utc)
