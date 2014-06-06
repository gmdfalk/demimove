import ConfigParser
import codecs
import logging
import os
import re
import sys


log = logging.getLogger("helpers")


def configure_logger(loglevel=2, quiet=False, logdir=None):
    "Creates the logger instance and adds handlers plus formatting."
    logger = logging.getLogger()

    # Set the loglevel.
    if loglevel > 3:
        loglevel = 3  # Cap at 3 to avoid index errors.
    levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    logger.setLevel(levels[loglevel])

    logformat = "%(asctime)-14s %(levelname)-8s %(name)-8s %(message)s"

    formatter = logging.Formatter(logformat, "%Y-%m-%d %H:%M:%S")

    if not quiet:
        console_handler = logging.StreamHandler(sys.stdout)
        console_handler.setFormatter(formatter)
        logger.addHandler(console_handler)
        logger.debug("Added logging console handler.")
        logger.info("Loglevel is {}.".format(levels[loglevel]))
    if logdir:
        try:
            logfile = os.path.join(logdir, "demimove.log")
            file_handler = logging.FileHandler(logfile)
            file_handler.setFormatter(formatter)
            logger.addHandler(file_handler)
            logger.debug("Added logging file handler: {}.".format(logfile))
        except IOError:
            logger.error("Could not attach file handler.")


def translate(pat):
    """Adjusted copy of fnmatch.translate. Translate a shell glob into regex."""

    i, n = 0, len(pat)
    res = ""
    while i < n:
        c = pat[i]
        i = i + 1
        if c == "*":
            res = res + ".*"
        elif c == "?":
            res = res + "."
        elif c == "[":
            j = i
            if j < n and pat[j] == "!":
                j = j + 1
            if j < n and pat[j] == "]":
                j = j + 1
            while j < n and pat[j] != "]":
                j = j + 1
            if j >= n:
                res = res + "\\["
            else:
                stuff = pat[i:j].replace("\\", "\\\\")
                i = j + 1
                if stuff[0] == "!":
                    stuff = "^" + stuff[1:]
                elif stuff[0] == "^":
                    stuff = "\\" + stuff
                res = "%s[%s]" % (res, stuff)
        else:
            res = res + re.escape(c)
    return res


def walklevels(path, levels=1):
    """Wrap os.walk to allow setting recursion depth."""
    path = path.rstrip(os.path.sep)
    assert os.path.isdir(path)
    num_sep = path.count(os.path.sep)
    for root, dirs, files in os.walk(path):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + levels <= num_sep_this:
            del dirs[:]


splitrx = re.compile("(^(?:\w\:)?\/.*\/)(.*?)(\..*)?$")

def splitpath(path):
    try:
        match = splitrx.match(path).groups()
        if match[-1] is None:
            match = match[:-1] + ("",)
        return match
    except AttributeError:
        pass


def splitpath_os(path):
    root = os.path.dirname(path) + "/"
    if os.path.isdir(path):
        return (root, os.path.basename(path), "")
    return ((root,) + os.path.splitext(os.path.basename(path)))


def get_configdir():
    "Determine if an XDG_CONFIG_DIR for demimove exists and if so, use it."
    configdir = os.path.join(os.path.expanduser("~"), ".config/demimove")

    if not os.path.isdir(configdir):
        log.info("Creating config directory.")
        os.makedirs(configdir)

    return configdir


def load_configfile(configdir, configfile=None):
    config = ConfigParser.ConfigParser()
    if configfile:
        filepath = os.path.abspath(configfile)
    else:
        filepath = os.path.join(configdir, "demimove.ini")
    config.read(filepath)
    defaultoptions = {"edits":  {"insertedit": "",
                                 "countpreedit": "",
                                 "countsufedit": "",
                                 "replaceedit": "",
                                 "filteredit": "",
                                 "excludeedit": "",
                                 "matchedit": ""},
                      "combos": {"casebox": 0, "spacebox": 0},
                      "checks": {"countcheck": False,
                                 "switchviewcheck": False,
                                 "keepextensionscheck": True,
                                 "deletecheck": False,
                                 "spacecheck": True,
                                 "matchexcludecheck": False,
                                 "autopreviewcheck": True,
                                 "matchreplacecheck": True,
                                 "hiddencheck": False,
                                 "casecheck": True,
                                 "insertcheck": False,
                                 "matchfiltercheck": False,
                                 "recursivecheck": False,
                                 "matchignorecase": False,
                                 "removeduplicatescheck": False,
                                 "removesymbolscheck": False,
                                 "removeextensionscheck": False,
                                 "autostopcheck": False,
                                 "manualmirrorcheck": False,
                                 "matchcheck": True,
                                 "removenonwordscheck": False,
                                 "removecheck": False,
                                 "countfillcheck": True},
                      "radios": {"dirsradio": False,
                                 "globradio": True,
                                 "filesradio": False,
                                 "regexradio": False,
                                 "bothradio": True},
                      "spins":  {"deleteend": 1,
                                 "countpos": 0,
                                 "countbase": 1,
                                 "countstep": 1,
                                 "deletestart": 0,
                                 "insertpos": 0,
                                 "recursivedepth": 0}
                        }
    options = {}
    try:
        excluded = ["mediamodecheck", "dualmodecheck"]
        options["checks"] = {k:config.getboolean("checks", k) for k, _\
                             in config.items("checks") if k not in excluded}
        options["combos"] = {k:config.getint("combos", k)\
                             for k, _ in config.items("combos")}
        options["edits"] = {k:config.get("edits", k)
                            for k, _ in config.items("edits")}
        options["radios"] = {k:config.getboolean("radios", k)\
                             for k, _ in config.items("radios")}
        options["spins"] = {k:config.getint("spins", k)\
                            for k, _ in config.items("spins")}
    except Exception as e:
        log.error("Could not completely read config file: {}.".format(e))
        log.info("Using configuration template.")
    else:
        log.info("Configuration file loaded from {}.".format(configdir))

    return options, defaultoptions


def save_configfile(configdir, options):
    configfile = os.path.join(configdir, "demimove.ini")
    config = ConfigParser.ConfigParser()
    for section, sectiondict in options.items():
        config.add_section(section)
        for key, value in sectiondict.items():
            config.set(section, key, value)

    with codecs.open(configfile, "w", encoding="utf-8") as f:
        config.write(f)

    log.info("Configuration file written to {}.".format(configfile))
