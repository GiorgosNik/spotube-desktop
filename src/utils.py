import datetime


def convert_sec_to_clock(seconds):
    return str(datetime.timedelta(seconds=max(int(seconds), 0)))
