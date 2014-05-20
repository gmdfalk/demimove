from ConfigParser import ConfigParser
import logging
import os
import sys


def configure_logger(loglevel=2, quiet=False):
    "Creates the logger instance and adds handlers and formatting."
    logger = logging.getLogger()

    # Set the loglevel.
    if loglevel > 3:
        loglevel = 3  # Cap at 3 to avoid index errors.
    levels = [logging.ERROR, logging.WARN, logging.INFO, logging.DEBUG]
    logger.setLevel(levels[loglevel])

    logformat = "%(asctime)-14s %(levelname)-8s %(name)-8s %(message)s"

    formatter = logging.Formatter(logformat, "%Y-%m-%d %H:%M:%S")

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    if quiet:
        logger.info("Quiet mode: logging disabled.")
        logging.disable(logging.ERROR)


def walklevels(path, levels=1):
    path = path.rstrip(os.path.sep)
    assert os.path.isdir(path)
    num_sep = path.count(os.path.sep)
    for root, dirs, files in os.walk(path):
        yield root, dirs, files
        num_sep_this = root.count(os.path.sep)
        if num_sep + levels <= num_sep_this:
            del dirs[:]


def get_configdir():
    "Determine the directory we read the configuration file from."
    xdgdir = os.path.join(os.path.expanduser("~"), ".config/demimove")
    if os.path.isdir(xdgdir):
        configdir = xdgdir
    else:
        configdir = os.path.dirname(os.path.realpath(__file__))

    return configdir


def parse_configfile(configdir):
    config = ConfigParser()
    configfile = "demimove.ini"
    if not configdir.startswith("/home"):
        configfile = "data/" + configfile
    config.read(os.path.join(configdir, configfile))
    options = {}
    for s in config.sections():
        options[s] = {k:v for k, v in config.items(s)}

    return options


def get_opt(option, optiontype=str):
    "Parse an option from config.ini"
    config, account = None, None
    section = account
    if optiontype == int:
        return config.getint(section, option)
    elif optiontype == float:
        return config.getfloat(section, option)
    elif optiontype == bool:
        return config.getboolean(section, option)
    elif optiontype == str:
        return config.get(section, option)