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


def parse_config(configdir):
    config = ConfigParser()
    config.read(os.path.join(configdir, "data/demimove.ini"))
    networks = {}
    for s in config.sections():
        print {k:v for k, v in config.items(s)}

    # Correct a couple of values.
#     for n in networks:
#         networks[n]["port"] = int(config.get(n, "port", 6667))
#         for i in ["urltitles_enabled", "ssl"]:
#             try:
#                 networks[n][i] = config.getboolean(n, i)
#             except NoOptionError:
#                 print "ConfigError: Could not parse option {}.".format(i)
#         for i in ["minperms", "lost_delay", "failed_delay", "rejoin_delay"]:
#             try:
#                 networks[n][i] = config.getint(n, i)
#             except NoOptionError:
#                 print "ConfigError: Could not parse option {}.".format(i)
#         for k, v in networks[n].items():
#             if k == "superadmins":
#                 networks[n]["superadmins"] = set(v.replace(" ", "").split(","))
#             elif k == "admins":
#                 networks[n]["admins"] = set(v.replace(" ", "").split(","))
#             elif k == "channels":
#                 networks[n]["channels"] = {i if i.startswith("#") else "#" + i\
#                                            for i in v.replace(" ", "").split(",")}

    return networks