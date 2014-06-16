# -*- coding: utf-8 -*-
from unicodedata import normalize
import fnmatch
import logging
import os
import re
import string

import helpers
from operator import itemgetter


log = logging.getLogger("fileops")


class FileOps(object):

    def __init__(self, casemode=0, countpos=0, dirsonly=False, exclude="",
                 filesonly=False, hidden=False, ignorecase=False,
                 interactive=False, keepext=False, mediamode=False,
                 noclobber=False, recursive=False, regex=False, remdups=False,
                 remext=False, remnonwords=False, remsymbols=False,
                 simulate=False, spacemode=0, quiet=False, verbosity=1,
                 matchpattern="", replacepattern="", recursivedepth=0):
        # Universal options:
        try:
            self._casemode = int(casemode)  # 0=lc, 1=uc, 2=flfw, 3=flew
        except TypeError:
            self._casemode = 0
        try:
            self._countpos = int(countpos)  # Adds numerical index at position.
        except TypeError:
            self._countpos = 0
        try:
            self._spacemode = int(spacemode)  # 0=su, 1=sh, 2=sd, 3=ds, 4=hs, 5=us
        except TypeError:
            self.spacemode = 0
        self._dirsonly = dirsonly  # Only edit directory names.
        self._filesonly = False if dirsonly else filesonly  # Only file names.
        self._hidden = hidden  # Look at hidden files and directories, too.
        self._ignorecase = ignorecase  # Case sensitivity.
        self._interactive = interactive  # Confirm before overwriting.
        self._keepext = keepext  # Don't modify remext.
        self._mediamode = mediamode  # Mode to sanitize NTFS-filenames/dirnames.
        self._noclobber = noclobber  # Don't overwrite anything.
        self._recursive = recursive  # Look for files recursively
        self._regex = regex  # Use regular expressions instead of glob/fnmatch.
        self._remdups = remdups  # Remove remdups.
        self._remext = remext  # Remove all remext.
        self._remnonwords = remnonwords  # Only allow wordchars (\w)
        self._remsymbols = remsymbols  # Normalize remsymbols (ñé becomes ne).
        self._simulate = simulate  # Simulate renaming and dump result to stdout.
        # Initialize GUI options.
        self._recursivedepth = recursivedepth
        self._excludeedit = "" if not exclude else exclude
        self._matchedit = "" if not matchpattern else matchpattern
        self._replaceedit = "" if not replacepattern else replacepattern
        self._autostop = False  # Automatically stop execution on rename error.
        self._countbase = 1  # Base to start counting from.
        self._countfill = True  # 9->10: 9 becomes 09. 99->100: 99 becomes 099.
        self._countpreedit = ""  # String that is prepended to the counter.
        self._countstep = 1  # Increment per count iteration.
        self._countsufedit = ""  # String that is appended to the counter.
        self._deletecheck = False  # Whether to delete a specified range.
        self._deleteend = 1  # End index of deletion sequence.
        self._deletestart = 0  # Start index of deletion sequence.
        self._filteredit = ""
        self._insertcheck = False  # Whether to apply an insertion.
        self._insertedit = ""  # The inserted text/string.
        self._insertpos = 0  # Position/Index to insert at.
        self._manualmirror = False  # Mirror manual rename to all targets.
        self._matchcheck = True  # Whether to apply source/target patterns.
        self._matchexcludecheck = False
        self._matchfiltercheck = False
        self._matchreplacecheck = True
        self._casecheck = True if isinstance(casemode, str) else False
        self._countcheck = True if isinstance(countpos, str) else False
        removelist = [remdups, remext, remnonwords, remsymbols]
        self._removecheck = True if any(removelist) else False
        self._spacecheck = True if isinstance(spacemode, str) else False
        self.stopupdate = False
        self.stopcommit = False
        self.includes = set()
        self.excludes = set()
        self.recursiveincludes = set()
        self.recursiveexcludes = set()
        self.configdir = helpers.get_configdir()
        # Create the logger.
        helpers.configure_logger(verbosity, quiet, self.configdir)
        self.history = []  # History of commited operations, used to undo them.
        # Match everything inside one set of braces:
        self.bracerx = re.compile("(?<=\{)(.*?)(?=\})")

    def match_filter(self, target):
        """Match a file/directory name against a glob/regex pattern."""
        if not self.filteredit:
            return True
        if "/" in self.filteredit:
            patterns = self.filteredit.split("/")
        else:
            patterns = [self.filteredit]
        if self.regex:
            for pattern in patterns:
                try:
                    if re.search(pattern, target, flags=self.ignorecase):
                        return True
                except:
                    pass
        else:
            for pattern in patterns:
                if fnmatch.fnmatch(target, pattern):
                    return True
        return False

    def match_exclude(self, target):
        """Match a file/directory name against a glob/regex pattern."""
        if not self.excludeedit:
            return
        if "/" in self.excludeedit:
            patterns = self.excludeedit.split("/")
        else:
            patterns = [self.excludeedit]
        if self.regex:
            for pattern in patterns:
                try:
                    if re.search(pattern, target, flags=self.ignorecase):
                        return False
                except:
                    pass
        else:
            for pattern in patterns:
                if fnmatch.fnmatch(target, pattern):
                    return False

    def match(self, target):
        """Searches target for pattern and returns a bool."""
        if not self.hidden and target.startswith(".") and target not in self.includes:
            return False
        if self.matchexcludecheck:
            if self.match_exclude(target) is False:
                return False
        if self.excludes and target in self.excludes:
            return False
        if self.includes and target in self.includes:
            return True
        if self.matchfiltercheck:
            if self.match_filter(target) is False:
                return False
        return True

    def get_dirs(self, root, dirs):
        """Match and decode (from utf-8 to unicode) a list of dirs."""
        return [(root, d, "") for d in dirs if self.match(d)]
#         return sorted((root, d, "") for d in dirs if self.match(d))

    def get_files(self, root, files):
        """Match and decode (from utf-8 to unicode) a list of files."""
        return [(root,) + os.path.splitext(f) for f in files if self.match(f)]
#         return sorted((root,) + os.path.splitext(f) for f in files if self.match(f))

    def get_targets(self, path=None):
        """Return a list of files and/or dirs in path."""
        if not path:
            path = os.getcwd()

        # Determine recursion depth.
        levels = 0
        if self.recursive:
            levels = self.recursivedepth

        targets = []
        for root, dirs, files in helpers.walklevels(path, levels):
            root += "/"
            if self.dirsonly:
                target = self.get_dirs(root, dirs)
            elif self.filesonly:
                target = self.get_files(root, files)
            else:
                target = self.get_dirs(root, dirs) + self.get_files(root, files)

            targets.extend(target)

            # Exit out of get_targets when "Stop" is pressed in the GUI.
            if self.stopupdate:
                return targets

        if self.countcheck:
            return sorted(targets, key=lambda i: i[1] + i[2])
        else:
            return targets

    def get_previews(self, targets, matchpat=None, replacepat=None):
        """Simulate rename operation on targets and return results as list."""
        if matchpat is not None:
            self.matchedit = matchpat
        if replacepat is not None:
            self.replaceedit = replacepat
        if self.mediamode:
            self.set_mediaoptions()

        return self.modify_previews(targets)
#         return sorted(self.modify_previews(targets), key=lambda i: i[0][1])

    def set_mediaoptions(self):
        self.casecheck = True
        self.spacecheck = True
        self.removecheck = True
        self.casemode = 0
        self.spacemode = 6
        self.remdups = True
        self.keepext = True
        self.remsymbols = True

    def commit(self, previews):
        # Reverse sort the paths (by counting the amount of slashs in the path)
        # so that the longest paths are renamed first.
        # This should minimize rename errors for recursive operations, for now.
        actions = sorted((("".join(i[0]), i[0][0] + i[1]) for i in previews),
                         key=lambda i: i[0].count("/"), reverse=True)

        for i in actions:
            log.debug("{} -> {}.".format(i[0], i[1]))
            # TODO: Implement a check for overwriting.
            if i[0] == i[1]:
                log.warn("File already exists. Skipping.")
                continue
            if self.simulate:
                continue
            if self.stopcommit:
                idx = actions.index(i)
                log.warn("Stopping commit after {} renames." .format(idx + 1))
                if idx:
                    log.warn("Use undo to revert the rename actions.")
                self.history.append(actions[:idx + 1])
                return
            try:
                os.rename(i[0], i[1])
            except Exception as e:
                log.debug("Rename Error: {} -> {} ({}).".format(i[0], i[1], e))
                if self.autostop:
                    break

        self.history.append(actions)
        log.info("Renaming complete.")

    def undo(self, actions=None):
        if actions is None:
            try:
                actions = self.history.pop()
            except IndexError:
                log.error("History list is empty.")
                return

        for i in actions:
            log.debug("{} -> {}.".format(i[1], i[0]))
            if self.simulate:
                continue
            try:
                os.rename(i[1], i[0])
            except Exception as e:
                log.error("Rename Error: {} -> {} ({}).".format(i[1], i[0], e))
                if self.autostop:
                    break

        log.info("Undo complete.")

    def modify_previews(self, previews):
        if self.countcheck:
            lenp, base, step = len(previews), self.countbase, self.countstep
            countlen = len(str(lenp))
            countrange = xrange(base, lenp * step + 1, step)
            if self.countfill:
                count = (str(i).rjust(countlen, "0") for i in countrange)
            else:
                count = (str(i) for i in countrange)

        modified = []
        for preview in previews:
            name = preview[1]
            if not self.remext and not self.keepext:
                name += preview[2]
            if self.casecheck:
                name = self.apply_case(name)
            if self.spacecheck:
                name = self.apply_space(name)
            if self.deletecheck:
                name = self.apply_delete(name)
            if self.removecheck:
                name = self.apply_remove(name)
            if self.insertcheck:
                name = self.apply_insert(name)
            if self.matchcheck:
                name = self.apply_replace(name)
            if self.countcheck:
                try:
                    name = self.apply_count(name, count.next())
                except StopIteration:
                    pass

            if self.keepext:
                name += preview[2]

            preview = ((preview[0], preview[1] + preview[2]), name)
            modified.append(preview)

        return modified

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

    def apply_case(self, s):
        if not self.casecheck:
            return s

        if self.casemode == 0:
            s = s.lower()
        elif self.casemode == 1:
            s = s.upper()
        elif self.casemode == 2:
            s = s.capitalize()
        elif self.casemode == 3:
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
        if self.remnonwords:
            s = re.sub("\W", "", s, flags=self.ignorecase)
        if self.remsymbols:
            allowed = string.ascii_letters + string.digits + " .-_+"  # []()
            for i in ["utf-8", "latin1"]:
                try:
                    # Convert bytestring to unicode and back.
                    s = "".join(c for c in normalize("NFKD", s.decode(i))
                                if c in allowed).encode("utf-8")
                    break
                except UnicodeDecodeError:
                    pass
            else:
                log.debug("Symbols: Could not decode {}.".format(s))
        if self.remdups:
            s = re.sub(r"([-_ .])\1+", r"\1", s, flags=self.ignorecase)
        return s

    def apply_replace(self, s):
        if not self.matchreplacecheck or not self.matchedit:
            return s

        if not self.regex:
            matchpat = fnmatch.translate(self.matchedit)
            replacepat = helpers.translate(self.replaceedit)
        else:
            matchpat = self.matchedit
            replacepat = self.replaceedit
        try:
            s = re.sub(matchpat, replacepat, s, flags=self.ignorecase)
        except:
            pass

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
    def matchcheck(self):
        return self._matchcheck

    @matchcheck.setter
    def matchcheck(self, boolean):
        log.debug("matchcheck: {}".format(boolean))
        self._matchcheck = boolean

    @property
    def matchexcludecheck(self):
        return self._matchexcludecheck

    @matchexcludecheck.setter
    def matchexcludecheck(self, boolean):
        log.debug("matchexcludecheck: {}".format(boolean))
        self._matchexcludecheck = boolean

    @property
    def matchfiltercheck(self):
        return self._matchfiltercheck

    @matchfiltercheck.setter
    def matchfiltercheck(self, boolean):
        log.debug("matchfiltercheck: {}".format(boolean))
        self._matchfiltercheck = boolean

    @property
    def matchreplacecheck(self):
        return self._matchreplacecheck

    @matchreplacecheck.setter
    def matchreplacecheck(self, boolean):
        log.debug("matchreplacecheck: {}".format(boolean))
        self._matchreplacecheck = boolean

    @property
    def countpreedit(self):
        return self._countpreedit

    @countpreedit.setter
    def countpreedit(self, text):
        log.debug("countpreedit: {}".format(text))
        self._countpreedit = text

    @property
    def countsufedit(self):
        return self._countsufedit

    @countsufedit.setter
    def countsufedit(self, text):
        log.debug("countsufedit: {}".format(text))
        self._countsufedit = text
    @property
    def insertedit(self):
        return self._insertedit

    @insertedit.setter
    def insertedit(self, text):
        log.debug("insertedit: {}.".format(text))
        self._insertedit = text

    @property
    def matchedit(self):
        return self._matchedit

    @matchedit.setter
    def matchedit(self, text):
        log.debug("matchedit: {}.".format(text))
        self._matchedit = text

    @property
    def replaceedit(self):
        return self._replaceedit

    @replaceedit.setter
    def replaceedit(self, text):
        log.debug("replaceedit: {}.".format(text))
        self._replaceedit = text

    @property
    def filteredit(self):
        return self._filteredit

    @filteredit.setter
    def filteredit(self, text):
        log.debug("filteredit: {}.".format(text))
        self._filteredit = text

    @property
    def excludeedit(self):
        return self._excludeedit

    @excludeedit.setter
    def excludeedit(self, text):
        log.debug("excludeedit: {}.".format(text))
        self._excludeedit = text

    @property
    def remsymbols(self):
        return self._remsymbols

    @remsymbols.setter
    def remsymbols(self, boolean):
        log.debug("remsymbols: {}".format(boolean))
        self._remsymbols = boolean

    @property
    def autostop(self):
        return self._autostop

    @autostop.setter
    def autostop(self, boolean):
        log.debug("autostop: {}".format(boolean))
        self._autostop = boolean

    @property
    def manualmirror(self):
        return self._manualmirror

    @manualmirror.setter
    def manualmirror(self, boolean):
        log.debug("manualmirror: {}".format(boolean))
        self._manualmirror = boolean

    @property
    def removecheck(self):
        return self._removecheck

    @removecheck.setter
    def removecheck(self, boolean):
        log.debug("removecheck: {}".format(boolean))
        self._removecheck = boolean

    @property
    def remdups(self):
        return self._remdups

    @remdups.setter
    def remdups(self, boolean):
        log.debug("remdups: {}".format(boolean))
        self._remdups = boolean

    @property
    def remext(self):
        return self._remext

    @remext.setter
    def remext(self, boolean):
        log.debug("remext: {}".format(boolean))
        self._remext = boolean

    @property
    def remnonwords(self):
        return self._remnonwords

    @remnonwords.setter
    def remnonwords(self, boolean):
        log.debug("remnonwords: {}".format(boolean))
        self._remnonwords = boolean

    @property
    def ignorecase(self):
        return self._ignorecase

    @ignorecase.setter
    def ignorecase(self, boolean):
        flag = 0
        if boolean:
            flag = re.I
        log.debug("ignorecase: {}".format(boolean))
        self._ignorecase = flag

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
    def casecheck(self):
        return self._casecheck

    @casecheck.setter
    def casecheck(self, boolean):
        log.debug("casecheck: {}".format(boolean))
        self._casecheck = boolean

    @property
    def casemode(self):
        return self._casemode

    @casemode.setter
    def casemode(self, num):
        log.debug("casemode: {}".format(num))
        self._casemode = num

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
    fileops = FileOps(hidden=True, recursive=True, casemode="1")
    fileops.get_previews(fileops.get_targets(), "*", "asdf")
