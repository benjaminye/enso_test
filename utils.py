import dateutil.parser as dt


def parse_timestr(timestr):
    """returns milliseconds timestamp given datetime str"""
    return int(dt.parse(timestr).timestamp()) * 1000
