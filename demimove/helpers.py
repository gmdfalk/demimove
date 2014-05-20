from ConfigParser import ConfigParser
import logging
import os
import sys


def configure_logger(loglevel=2, quiet=False, logdir=None):
    "Creates the logger instance and adds handlers and formatting."
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
            logfile = os.path.abspath(logdir)
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
        return configdir


def load_configfile(configdir):
    config = ConfigParser()
    config.read(os.path.join(configdir, "demimove.ini"))
    print config, type(config)
    options = {}
    options["checks"] = {k:config.getboolean("checks", k)\
                         for k, v in config.items("checks")}
    options["combos"] = {k:config.getint("combos", k)\
                         for k, v in config.items("combos")}
    options["edits"] = {k:config.get("edits", k).decode("utf-8")\
                        for k, v in config.items("edits")}
    options["radios"] = {k:config.getboolean("radios", k)\
                         for k, v in config.items("radios")}
    options["spins"] = {k:config.getint("spins", k)\
                        for k, v in config.items("spins")}

    return options

def save_configfile(configdir, options):
    configfile = os.path.join(configdir, "demimove.ini")
    config = ConfigParser()
    for k, v in options.items():
        config.add_section(k)
        for kk, vv in v.items():
            config.set(k, kk, vv)

    with open('example.ini', 'w') as f:
        config.write(f)

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
