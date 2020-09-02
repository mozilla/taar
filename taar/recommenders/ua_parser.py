import re

RE_PLATFORM = re.compile("(linux|windows|macintosh|android|fxios).*firefox")

LINUX = 1
WINDOWS = 2
MACINTOSH = 3
ANDROID = 4
FXIOS = 5

OSNAME_TO_ID = {
    "linux": LINUX,
    "windows": WINDOWS,
    "macintosh": MACINTOSH,
    "android": ANDROID,
    "fxios": FXIOS,
}


def parse_ua(user_agent):
    """
    Return one of the constants for platform selection, otherwise
    return None if the platform cannot be determined.  Any non-firefox
    agent us automatically short circuited to be None.
    """
    ua = user_agent.lower()
    matches = RE_PLATFORM.findall(ua)
    if len(matches) != 1:
        return None
    return OSNAME_TO_ID[matches[0]]
