# -*- coding: utf-8 -*-
# TODO: Exclude option.
# TODO: Fix count step and count base plus large listings (~i).
# TODO: Reconcile keepext and not matchreplace.
from copy import deepcopy
from unicodedata import normalize, category
import fnmatch
import logging
import os
import re
import sys


log = logging.getLogger("fileops")


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
        log.info("Quiet mode: logging disabled.")
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


class FileOps(object):

    def __init__(self, quiet=False, verbosity=1,
                 dirsonly=False, filesonly=False, recursive=False,
                 hidden=False, simulate=False, interactive=False, prompt=False,
                 noclobber=False, keepext=False, regex=False, exclude=None,
                 mediamode=False, accents=False, lower=False, upper=False,
                 remdups=False, remext=False, remnonwords=False,
                 ignorecase=False, countpos=0):
        # List of available options.
        self.opts = ("quiet", "verbosity",
                     "dirsonly", "filesonly", "recursive", "hidden",
                     "simulate", "interactive", "prompt", "noclobber",
                     "keepext", "regex", "exclude", "media", "accents",
                     "lower", "upper", "remdups", "remext", "remnonwords",
                     "ignorecase", "countpos",
                     "autostop", "mirror", "spacecheck", "spacemode",
                     "capitalizecheck", "capitalizemode",
                     "insertcheck", "insertpos", "insertedit",
                     "countcheck", "countfill", "countbase", "countpreedit",
                     "countsufedit", "varcheck",
                     "deletecheck", "deletestart", "deleteend",
                     "matchcheck")
        # Universal options:
        self._dirsonly = dirsonly  # Only edit directory names.
        self._filesonly = False if dirsonly else filesonly  # Only file names.
        self._recursive = recursive  # Look for files recursively
        self._hidden = hidden  # Look at hidden files and directories, too.
        self._simulate = simulate  # Simulate renaming and dump result to stdout.
        self._interactive = interactive  # Confirm before overwriting.
        self._prompt = prompt  # Confirm all rename actions.
        self._noclobber = noclobber  # Don't overwrite anything.
        self._keepext = keepext  # Don't modify remext.
        self._countpos = countpos  # Adds numerical index at position.
        self._regex = regex  # Use regular expressions instead of glob/fnmatch.
        self._exclude = exclude  # List of strings to exclude from targets.
        self._accents = accents  # Normalize accents (ñé becomes ne).
        self._lower = lower  # Convert target to lowercase.
        self._upper = upper  # Convert target to uppercase.
        self._ignorecase = ignorecase  # Case sensitivity.
        self._mediamode = mediamode  # Mode to sanitize NTFS-filenames/dirnames.
        self._remdups = remdups  # Remove remdups.
        self._remnonwords = remnonwords  # Only allow wordchars (\w)
        self._remext = remext  # Remove all remext.
        # Initialize GUI options.
        self._autostop = False  # Automatically stop execution on rename error.
        self._mirror = False  # Mirror manual rename to all targets.
        self._capitalizecheck = False  # Whether to apply the capitalizemode.
        self._capitalizemode = 0  # 0=lc, 1=uc, 2=flfw, 3=flew
        self._spacecheck = False  # Whether to apply the spacemode.
        self._spacemode = 0  # 0=su, 1=sh, 2=sd, 3=ds, 4=hs, 5=us
        self._countcheck = False  # Whether to add a counter to the targets.
        self._countbase = 1  # Base to start counting from.
        self._countstep = 1
        self._countfill = True  # 9->10: 9 becomes 09. 99->100: 99 becomes 099.
        self._countpreedit = ""  # String that is prepended to the counter.
        self._countsufedit = ""  # String that is appended to the counter.
        self._insertcheck = False  # Whether to apply an insertion.
        self._insertpos = 0  # Position/Index to insert at.
        self._insertedit = ""  # The inserted text/string.
        self._deletecheck = False  # Whether to delete a specified range.
        self._deletestart = 0  # Start index of deletion sequence.
        self._deleteend = 1  # End index of deletion sequence.
        self._matchcheck = True  # Whether to apply source/target patterns.
        self._matchreplace = True
        self._removecheck = False
        self._varcheck = False  # Whether to apply various options (accents).
        self._recursivedepth = 1

        # Create the logger.
        configure_logger(verbosity, quiet)
        self.history = []  # History of commited operations, useful to undo.
        self.defaultopts = {i:getattr(self, "_" + i, None) for i in self.opts}

    def get_options(self, *args):
        if args:
            return {i: getattr(self, i, None) for i in args}
        return {i: getattr(self, i, None) for i in self.opts}

    def set_options(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)

    def restore_options(self):
        self.set_options(**self.defaultopts)

    def get_targets(self, path=None):
        """Return a list of files and/or dirs in path."""
        if not path:
            path = os.getcwd()

        targets = []

        # Determine recursion depth.
        levels = 0
        if self.recursive:
            levels = self.recursivedepth
        for root, dirs, files in walklevels(path, levels):
            # To unicode.
            root = root.decode("utf-8") + "/"
            dirs = [d.decode("utf-8") for d in dirs]
            files = [f.decode("utf-8") for f in files]
            # Exclude targets, if necessary.
            if not self.hidden:
                dirs = [i for i in dirs if not i.startswith(".")]
                files = [i for i in files if not i.startswith(".")]
            if self.exclude:
                dirs = [i for i in dirs if i not in self.exclude]
                files = [i for i in files if i not in self.exclude]

            dirs.sort()
            files.sort()
            dirs = [[root, i] for i in dirs]

            newfiles = []
            for i in files:
                fname, ext = os.path.splitext(i)
                newfiles.append([root, fname, ext])

            if self.dirsonly:
                target = dirs
            elif self.filesonly:
                target = newfiles
            else:
                target = dirs + newfiles
            targets.extend(target)

        return targets

    def get_previews(self, targets, matchpat=None, replacepat=None):
        """Simulate rename operation on targets and return results as list."""
        if not matchpat:
            matchpat = "*"
            if self.regex:
                matchpat = ".*"
        if replacepat is None:
            replacepat = "*"
            if self.regex:
                replacepat = ".*"
        if self.mediamode:
            self.set_mediaoptions()

        return self.modify_previews(deepcopy(targets), matchpat, replacepat)

    def set_mediaoptions(self):
        self.capitalizecheck = True
        self.spacecheck = True
        self.removecheck = True
        self.varcheck = True
        self.capitalizemode = 0
        self.spacemode = 6
        self.remdups = True
        self.keepext = True
        self.accents = True

    def commit(self, previews):
        if self.simulate:
            for p in previews:
                print "{} to {}".format(p[1], p[2])
        # clean up self.exclude

    def undo(self, action=None):
        if action is None:
            action = self.history.pop()

    def match(self, matchpat, target):
        """Searches target for pattern and returns a bool."""
        if self.regex:
            if re.search(matchpat, target):
                return True
        else:
            if fnmatch.fnmatch(target, matchpat):
                return True
        return False

    def modify_previews(self, previews, matchpat, replacepat):
        if self.countcheck:
            lenp, base, step = len(previews), self.countbase, self.countstep
            countlen = len(str(lenp))
            countrange = range(base, lenp * step + 1, step)
            if self.countfill:
                count = (str(i).rjust(countlen, "0") for i in countrange)
            else:
                count = (str(i) for i in countrange)

        modified = []
        for preview in previews:
            name = preview[1]
            if not self.remext and not self.keepext:
                try:
                    name += preview[2]
                except IndexError:
                    pass
#             print name
            if self.matchcheck:
                name = self.apply_match(name, matchpat, replacepat)
            if self.capitalizecheck:
                name = self.apply_capitalize(name)
            if self.spacecheck:
                name = self.apply_space(name)
            if self.deletecheck:
                name = self.apply_delete(name)
            if self.removecheck:
                name = self.apply_remove(name)
            if self.insertcheck:
                name = self.apply_insert(name)
            if self.countcheck:
                try:
                    name = self.apply_count(name, count.next())
                except StopIteration:
                    pass

            if self.keepext:
                try:
                    name += preview[2]
                except IndexError:
                    pass

            modified.append(name)

        previews = [[i[0], i[1] + i[2]] if len(i) > 2 else i for i in previews]

        return zip(previews, modified)

    def apply_space(self, s):
        if not self.spacecheck:
            return s

        if self.spacemode == 0:
            s = s.replace(" ", "_")
        elif self.spacemode == 1:
            s = s.replace(" ", "-")
        elif self.spacemode == 2:
            s = s.replace(" ", ".")
        elif self.spacemode == 3:
            s = s.replace(".", " ")
        elif self.spacemode == 4:
            s = s.replace("-", " ")
        elif self.spacemode == 5:
            s = s.replace("_", " ")
        elif self.spacemode == 6:
            s = re.sub("[.\s]", "_", s)

        return s

    def apply_capitalize(self, s):
        if not self.capitalizecheck:
            return s

        if self.capitalizemode == 0:
            s = s.lower()
        elif self.capitalizemode == 1:
            s = s.upper()
        elif self.capitalizemode == 2:
            s = s.capitalize()
        elif self.capitalizemode == 3:
            s = " ".join([c.capitalize() for c in s.split()])

        return s

    def apply_insert(self, s):
        if not self.insertcheck or not self.insertedit:
            return s
        s = list(s)
        s.insert(self.insertpos, self.insertedit)
        return "".join(s)

    def apply_count(self, s, count):
        if not self.countcheck:
            return s
        s = list(s)

        if self.countpreedit:
            count = self.countpreedit + count
        if self.countsufedit:
            count += self.countsufedit
        s.insert(self.countpos, count)

        return "".join(s)

    def apply_delete(self, s):
        if not self.deletecheck:
            return s
        return s[:self.deletestart] + s[self.deleteend:]

    def apply_remove(self, s):
        if not self.removecheck:
            return s
        if self.remdups:
            s = re.sub(r"([-_ .])\1+", r"\1", s)
        if self.remnonwords:
            s = re.sub("\W", "", s)
        return s

    def apply_match(self, s, matchpat, replacepat):
        return s
        # TODO: Handle case sensitivity (re.IGNORECASE)
        if not self.matchcheck:
            return s
        # Translate glob to regular expression.
        if not self.regex:
            matchpat = fnmatch.translate(matchpat)
            replacepat = fnmatch.translate(replacepat)
        match = re.search(matchpat, s)
#         if match:
#             log.debug("found src: {}.".format(match.group()))
        if not match:
            return s
        if not self.matchreplace:
            result = match.group()
        else:
            replace = re.search(replacepat, s)
            if replace:
                log.debug("found dest: {}.".format(replace.group()))
            log.debug("{}, {}, {}, {}".format(matchpat, replacepat,
                                          match, replace))
            result = replace.group()

        # TODO: Two functions: one to convert a glob into a pattern
        # and another to convert one into a replacement.
        return result

    def apply_various(self, s):
        if not self.varcheck:
            return
        if self.accents:
            s = "".join(c for c in normalize("NFD", s) if category(c) != "Mn")
        return s

    @property
    def dirsonly(self):
        return self._dirsonly

    @dirsonly.setter
    def dirsonly(self, boolean):
        log.debug("dirsonly: {}".format(boolean))
        self._dirsonly = boolean
        if boolean:
            self.filesonly = False

    @property
    def filesonly(self):
        return self._filesonly

    @filesonly.setter
    def filesonly(self, boolean):
        log.debug("filesonly: {}".format(boolean))
        self._filesonly = boolean
        if boolean:
            self.dirsonly = False

    @property
    def recursive(self):
        return self._recursive

    @recursive.setter
    def recursive(self, boolean):
        log.debug("recursive: {}".format(boolean))
        self._recursive = boolean

    @property
    def recursivedepth(self):
        return self._recursivedepth

    @recursivedepth.setter
    def recursivedepth(self, num):
        log.debug("recursivedepth: {}".format(num))
        self._recursivedepth = num

    @property
    def hidden(self):
        return self._hidden

    @hidden.setter
    def hidden(self, boolean):
        log.debug("hidden: {}".format(boolean))
        self._hidden = boolean

    @property
    def simulate(self):
        return self._simulate

    @simulate.setter
    def simulate(self, boolean):
        log.debug("simulate: {}".format(boolean))
        self._simulate = boolean

    @property
    def interactive(self):
        return self._interactive

    @interactive.setter
    def interactive(self, boolean):
        log.debug("interactive: {}".format(boolean))
        self._interactive = boolean

    @property
    def prompt(self):
        return self._prompt

    @prompt.setter
    def prompt(self, boolean):
        log.debug("simulate: {}".format(boolean))
        self._prompt = boolean

    @property
    def noclobber(self):
        return self._noclobber

    @noclobber.setter
    def noclobber(self, boolean):
        log.debug("noclobber: {}".format(boolean))
        self._noclobber = boolean

    @property
    def keepext(self):
        return self._keepext

    @keepext.setter
    def keepext(self, boolean):
        log.debug("keepext: {}.".format(boolean))
        self._keepext = boolean

    @property
    def regex(self):
        return self._regex

    @regex.setter
    def regex(self, boolean):
        log.debug("regex: {}.".format(boolean))
        self._regex = boolean

    @property
    def varcheck(self):
        return self._varcheck

    @varcheck.setter
    def varcheck(self, boolean):
        log.debug("varcheck: {}".format(boolean))
        self._varcheck = boolean

    @property
    def replacematch(self):
        return self._replacematch

    @replacematch.setter
    def replacematch(self, boolean):
        log.debug("replacematch: {}".format(boolean))
        self._replacematch = boolean

    @property
    def accents(self):
        return self._accents

    @accents.setter
    def accents(self, boolean):
        log.debug("accents: {}".format(boolean))
        self._accents = boolean

    @property
    def exclude(self):
        return self._exclude

    @exclude.setter
    def exclude(self, names):
        log.debug("Excluding {}.".format(names))
        self._exclude = names

    @property
    def autostop(self):
        return self._autostop

    @autostop.setter
    def autostop(self, boolean):
        log.debug("autostop: {}".format(boolean))
        self._autostop = boolean

    @property
    def mirror(self):
        return self._mirror

    @mirror.setter
    def mirror(self, boolean):
        log.debug("mirror: {}".format(boolean))
        self._mirror = boolean

    @property
    def removecheck(self):
        return self._removecheck

    @removecheck.setter
    def removecheck(self, boolean):
        log.debug("removecheck: {}".format(boolean))
        self._removecheck = boolean

    @property
    def remnonwords(self):
        return self._remnonwords

    @remnonwords.setter
    def remnonwords(self, boolean):
        log.debug("remnonwords: {}".format(boolean))
        self._remnonwords = boolean

    @property
    def remext(self):
        return self._remext

    @remext.setter
    def remext(self, boolean):
        log.debug("remext: {}".format(boolean))
        self._remext = boolean

    @property
    def remdups(self):
        return self._remdups

    @remdups.setter
    def remdups(self, boolean):
        log.debug("remdups: {}".format(boolean))
        self._remdups = boolean

    @property
    def lower(self):
        return self._lower

    @lower.setter
    def lower(self, boolean):
        log.debug("lower: {}".format(boolean))
        self._lower = boolean

    @property
    def upper(self):
        return self._upper

    @upper.setter
    def upper(self, boolean):
        log.debug("upper: {}".format(boolean))
        self._upper = boolean

    @property
    def ignorecase(self):
        return self._ignorecase

    @ignorecase.setter
    def ignorecase(self, boolean):
        log.debug("ignorecase: {}".format(boolean))
        self._ignorecase = boolean

    @property
    def nowords(self):
        return self._nowords

    @nowords.setter
    def nowords(self, boolean):
        log.debug("nowords: {}".format(boolean))
        self._nowords = boolean

    @property
    def mediamode(self):
        return self._mediamode

    @mediamode.setter
    def mediamode(self, boolean):
        log.debug("mediamode: {}".format(boolean))
        self._mediamode = boolean

    @property
    def countcheck(self):
        return self._countcheck

    @countcheck.setter
    def countcheck(self, boolean):
        log.debug("countcheck: {}".format(boolean))
        self._countcheck = boolean

    @property
    def countfill(self):
        return self._countfill

    @countfill.setter
    def countfill(self, boolean):
        log.debug("countfill: {}".format(boolean))
        self._countfill = boolean

    @property
    def countpos(self):
        return self._countpos

    @countpos.setter
    def countpos(self, index):
        log.debug("countpos: {}".format(index))
        self._countpos = index

    @property
    def countbase(self):
        return self._countbase

    @countbase.setter
    def countbase(self, num):
        log.debug("countbase: {}".format(num))
        self._countbase = num

    @property
    def countstep(self):
        return self._countstep

    @countstep.setter
    def countstep(self, num):
        log.debug("countstep: {}".format(num))
        self._countstep = num

    @property
    def countpreedit(self):
        return self._countpreedit

    @countpreedit.setter
    def countpreedit(self, text):
        log.debug("countpreedit: {}".format(text))
        self._countpreedit = text.decode("utf-8")

    @property
    def countsufedit(self):
        return self._countsufedit

    @countsufedit.setter
    def countsufedit(self, text):
        log.debug("countsufedit: {}".format(text))
        self._countsufedit = text.decode("utf-8")

    @property
    def insertcheck(self):
        return self._insertcheck

    @insertcheck.setter
    def insertcheck(self, boolean):
        log.debug("insertcheck: {}".format(boolean))
        self._insertcheck = boolean

    @property
    def insertpos(self):
        return self._insertpos

    @insertpos.setter
    def insertpos(self, index):
        log.debug("insertpos: {}".format(index))
        self._insertpos = index

    @property
    def insertedit(self):
        return self._insertedit

    @insertedit.setter
    def insertedit(self, text):
        log.debug("insertedit: {}.".format(text))
        self._insertedit = text.decode("utf-8")

    @property
    def deletecheck(self):
        return self._deletecheck

    @deletecheck.setter
    def deletecheck(self, boolean):
        log.debug("deletecheck: {}".format(boolean))
        self._deletecheck = boolean

    @property
    def deletestart(self):
        return self._deletestart

    @deletestart.setter
    def deletestart(self, index):
        log.debug("deletestart: {}".format(index))
        self._deletestart = index

    @property
    def deleteend(self):
        return self._deleteend

    @deleteend.setter
    def deleteend(self, index):
        log.debug("deleteend: {}".format(index))
        self._deleteend = index

    @property
    def matchcheck(self):
        return self._matchcheck

    @matchcheck.setter
    def matchcheck(self, boolean):
        log.debug("matchcheck: {}".format(boolean))
        self._matchcheck = boolean

    @property
    def matchreplace(self):
        return self._matchreplace

    @matchreplace.setter
    def matchreplace(self, boolean):
        log.debug("matchreplace: {}".format(boolean))
        self._matchreplace = boolean

    @property
    def capitalizecheck(self):
        return self._capitalizecheck

    @capitalizecheck.setter
    def capitalizecheck(self, boolean):
        log.debug("capitalizecheck: {}".format(boolean))
        self._capitalizecheck = boolean

    @property
    def capitalizemode(self):
        return self._capitalizemode

    @capitalizemode.setter
    def capitalizemode(self, num):
        log.debug("capitalizemode: {}".format(num))
        self._capitalizemode = num

    @property
    def spacecheck(self):
        return self._spacecheck

    @spacecheck.setter
    def spacecheck(self, boolean):
        log.debug("spacecheck: {}".format(boolean))
        self._spacecheck = boolean

    @property
    def spacemode(self):
        return self._spacemode

    @spacemode.setter
    def spacemode(self, num):
        log.debug("spacemode: {}".format(num))
        self._spacemode = num


if __name__ == "__main__":
    fileops = FileOps(hidden=True, recursive=False, keepext=False, regex=False)
    targets = fileops.get_targets()
    fileops.get_previews(targets, "*", "asdf")

