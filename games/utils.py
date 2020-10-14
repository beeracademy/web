def get_milliseconds(td):
    return td.seconds * 1000 + td.microseconds // 1000


def add_thousand_seperators(value):
    return f"{value:,}"


def format_sips(value):
    BASE = 14
    res = []
    while value > 0:
        v = value % 14
        if v < 10:
            res.append(str(v))
        else:
            res.append(chr(ord("A") + (v - 10)))
        value //= BASE

    return "".join(res[::-1])


def format_chug_duration(ms):
    td = datetime.timedelta(milliseconds=ms)
    s = str(td)
    if not "." in s:
        s += "."

    a, b = s.split(".")
    return a.split(":", 1)[1] + "." + b.rstrip("0").ljust(3, "0")


def format_total_time(s):
    td = datetime.timedelta(seconds=s)
    return str(td).split(".")[0]
