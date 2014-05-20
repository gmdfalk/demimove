from ConfigParser import ConfigParser, NoOptionError
import logging
import os
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


def walklevels(path, levels=1):
    """Replacement for os.walk."""
    path = path.rstrip(os.path.sep)
    assert os.path.isdir(path)
    num_sep = path.count(os.path.sep)
    for root, dirs, files in os.walk(path):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + levels <= num_sep_this:
            del dirs[:]


def get_configdir():
    "Determine if an XDG_CONFIG_DIR for demimove exists and if so, use it."
    configdir = os.path.join(os.path.expanduser("~"), ".config/demimove")
    if os.path.isdir(configdir):
        log.debug("Config file found.")
        return configdir


def load_configfile(configdir):
    config = ConfigParser()
    config.read(os.path.join(configdir, "demimove.ini"))
    defaultoptions = {"edits":  {"insertedit": u"",
                                 "countpreedit": u"",
                                 "countsufedit": u"",
                                 "replaceedit": u"",
                                 "filteredit": u"",
                                 "excludeedit": u"",
                                 "matchedit": u""},
                      "combos": {"casebox": 0, "spacebox": 0},
                      "checks": {"countcheck": False,
                                 "switchviewcheck": False,
                                 "keepextensionscheck": False,
                                 "deletecheck": False,
                                 "spacecheck": False,
                                 "matchexcludecheck": False,
                                 "autopreviewcheck": True,
                                 "matchreplacecheck": False,
                                 "hiddencheck": False,
                                 "casecheck": False,
                                 "insertcheck": False,
                                 "matchfiltercheck": False,
                                 "recursivecheck": False,
                                 "matchignorecase": False,
                                 "removeduplicatescheck": False,
                                 "removesymbolscheck": False,
                                 "removeextensionscheck": False,
                                 "autostopcheck": False,
                                 "manualmirrorcheck": False,
                                 "matchcheck": False,
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
                                 "recursivedepth": 1}
                        }
    options = {}
    try:
        excluded = ["mediamodecheck", "dualmodecheck"]
        options["checks"] = {k:config.getboolean("checks", k) for k, _\
                             in config.items("checks") if k not in excluded}
        options["combos"] = {k:config.getint("combos", k)\
                             for k, _ in config.items("combos")}
        options["edits"] = {k:config.get("edits", k).decode("utf-8")\
                            for k, _ in config.items("edits")}
        options["radios"] = {k:config.getboolean("radios", k)\
                             for k, _ in config.items("radios")}
        options["spins"] = {k:config.getint("spins", k)\
                            for k, _ in config.items("spins")}
    except NoOptionError as e:
        log.debug("Could not completely read config file: {}.".format(e))
        log.debug("Using default (empty) configuration file.")
    else:
        log.debug("Configuration file loaded from {}.".format(configdir))

    return options, defaultoptions


def save_configfile(configdir, options):
    configfile = os.path.join(configdir, "demimove.ini")
    config = ConfigParser()
    for section, sectiondict in options.items():
        config.add_section(section)
        for key, value in sectiondict.items():
            config.set(section, key, value)

    with open(configfile, "w") as f:
        config.write(f)

    log.info("Configuration file written to {}.".format(configfile))
