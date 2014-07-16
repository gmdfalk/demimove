# -*- coding: utf-8 -*-
"""demimove-ui

Usage:
    demimove-ui [<path>] [-c <file>] [-v|-vv|-vvv] [-q] [-h]

Options:
    -c, --config=<file>  Specify a config file to load.
    -v                   Logging verbosity level, up to -vvv.
    -q, --quiet          Do not print logging messages to console.
    -h,  --help          Show this help text and exit.
    --version            Show the current demimove-ui version.
"""
# GUI:
# TODO: Overwrite check.
# TODO: Accelerators (C+Q, Q+S).
# TODO: Add recursive include/exclude in contextmenu.
# TODO: Test QDirIterator vs os.path.walk. If positive, replace get_targets
#       functionality (though Qt has encoding issues for non-utf8 file names).
# TODO: History tab.
# TODO: Statustab with Errors/Warnings, Summaries etc.
# TODO: Metatags (Photos, Videos, Audio)
# TODO: Test demimove on windows?
# TODO: Write unittests for rename/undo with mock unicode input?
# Fileops:
# TODO: Fix count step and count base plus large listings (~i).
# TODO: Enable glob replacing like this: *.mp3 prefix*.mp3
#       (Adjust translate method to group wildcards).
# TODO: Fix filters on hiddencheck? Logic for on_refreshbutton?
# TODO: (more) fallback encodings?
# TODO: grey out undo button if history empty

import codecs
import logging
import os
import sys

from PyQt4 import Qt, QtGui, QtCore, uic

import fileops
import helpers
import history


log = logging.getLogger("gui")

try:
    from docopt import docopt
except ImportError:
    print("ImportError: You won't be able to use the CLI.")


class BoldDelegate(QtGui.QStyledItemDelegate):

    def paint(self, painter, option, index):
        if self.parent().cwdidx == index:
            option.font.setWeight(QtGui.QFont.Bold)
        super(BoldDelegate, self).paint(painter, option, index)


class DirModel(QtGui.QFileSystemModel):

    def __init__(self, parent=None):
        super(DirModel, self).__init__(parent)
        self.p = parent
        self.labels = ["Name", "Size", "Type", "Date Modified", "Preview"]

    def columnCount(self, parent=QtCore.QModelIndex()):
        return super(DirModel, self).columnCount() + 1

    def headerData(self, col, orientation, role=Qt.Qt.DisplayRole):
        if role == QtCore.Qt.DisplayRole and orientation == QtCore.Qt.Horizontal:
            return self.labels[col]
        return QtGui.QFileSystemModel.headerData(self, col, orientation, role)

    def data(self, index, role):

        if index.column() == self.columnCount() - 1:
            if role == QtCore.Qt.DisplayRole:
                if not self.p.autopreview:
                    return
                fileindex = self.index(index.row(), 0, index.parent())
                return self.match_preview(fileindex)

        return super(DirModel, self).data(index, role)

    def match_preview(self, index, *args):
        if not self.p.cwdidx:
            return
        if not self.p.fileops.recursive and index.parent() != self.p.cwdidx:
            return
        target = helpers.splitpath_os(self.p.get_path(index))
        if self.p.cwd in target[0] and target in self.p.targets:
            idx = self.p.targets.index(target)
            try:
                # If preview differs from its original name, show the preview.
                if target[1] + target[2] != self.p.previews[idx][1]:
                    for i in ["utf-8", "latin1"]:
                        try:
                            return self.p.previews[idx][1].decode(i)
                        except UnicodeDecodeError:
                            pass
                    return self.p.previews[idx][1]
                # Otherwise show "\1" to indicate that nothing changed.
                else:
                    return "\\1"
            except IndexError:
                return "err"


class UpdateThread(QtCore.QThread):

    def __init__(self, parent=None):
        super(UpdateThread, self).__init__(parent)
        self.p = parent
        self.mode = 1

    def run(self):
        if self.mode == 0:
            self.p.update_targets()
        elif self.mode == 1:
            self.p.update_previews()
        elif self.mode == 2:
            self.p.update_targets()
            self.p.update_previews()


class CommitThread(QtCore.QThread):

    def __init__(self, parent=None):
        super(CommitThread, self).__init__(parent)
        self.p = parent

    def run(self):
        self.p.fileops.commit(self.p.previews)


class DemiMoveGUI(QtGui.QMainWindow):

    def __init__(self, startdir, fileops, configfile, parent=None):

        super(DemiMoveGUI, self).__init__(parent)
        self.fileops = fileops
        # Current working directory.
        self.basedir = os.path.dirname(os.path.realpath(__file__))
        self._autopreview = True
        self._cwd = ""
        self._cwdidx = None
        self.switchview = False
        # Initialize empty containers for option states and targets.
        self.dualoptions1, self.dualoptions2 = {}, {}
        self.targets, self.joinedtargets = [], []
        self.previews = []

        self.initialize_ui(startdir, configfile)

    def initialize_ui(self, startdir, configfile):
        self.updatethread = UpdateThread(self)
        self.committhread = CommitThread(self)
        guifile = os.path.join(self.basedir, "data/gui.ui")
        iconfile = os.path.join(self.basedir, "data/icon.png")
        uic.loadUi(guifile, self)
        self.switchviewcheck.hide()
        self.setWindowIcon(QtGui.QIcon(iconfile))
        self.mainsplitter.setStretchFactor(0, 1)
        self.create_browser(startdir)
#         self.create_historytab()
        self.connect_elements()

        self.startoptions, self.defaultoptions = helpers.load_configfile(
                                                 self.fileops.configdir,
                                                 configfile)
        self.set_options(self.startoptions)
        self.mediachecks = [self.casecheck, self.keepextensionscheck,
                            self.removesymbolscheck, self.removecheck,
                            self.removeduplicatescheck, self.spacecheck]
        self.mediaboxes = [self.casebox, self.spacebox]

        self.dirview.setExpanded(self.get_index(), True)
        log.info("demimove-ui initialized.")
        self.statusbar.showMessage("Select a directory and press Enter.")

    def create_browser(self, startdir):
        # TODO: With readOnly disabled we can use setData for file operations?
        self.dirmodel = DirModel(self)
        self.dirmodel.setReadOnly(False)
        self.dirmodel.setRootPath("/")
        self.dirmodel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Files |
                                    QtCore.QDir.NoDotAndDotDot)

        self.menu = QtGui.QMenu(self)
        self.dirview.setModel(self.dirmodel)
        self.dirview.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.dirview.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.dirview.setColumnHidden(2, True)
        self.dirview.header().swapSections(4, 1)
        self.dirview.header().resizeSection(0, 300)
        self.dirview.header().resizeSection(4, 220)
        self.dirview.header().resizeSection(3, 124)
        self.dirview.setEditTriggers(QtGui.QAbstractItemView.EditKeyPressed)
        self.dirview.setItemDelegate(BoldDelegate(self))
        self.dirview.setCurrentIndex(self.dirmodel.index(startdir))

    def create_historytab(self):
        historyfile = os.path.join(self.fileops.configdir, "history.txt")

        try:
            with codecs.open(historyfile, encoding="utf-8") as f:
                data = f.read()
        except IOError:
            historyfile = os.path.join(self.basedir, "data/history.txt")
            with codecs.open(historyfile, encoding="utf-8") as f:
                data = f.read()

        self.historymodel = history.HistoryTreeModel(data, self)
        self.historytree.setModel(self.historymodel)

    def set_options(self, options=None, sanitize=False):
        if not options:
            options = self.defaultoptions

#         self.autopreview = False

        for k, v in options["checks"].items():
            # Handle autopreview attribute at the end.
            if k == "autopreviewcheck": continue
            if sanitize:
                v = False
            getattr(self, k).setChecked(v)
        for k, v in options["combos"].items():
            if sanitize:
                v = 0
            getattr(self, k).setCurrentIndex(v)
        for k, v in options["edits"].items():
            if sanitize:
                v = ""
            getattr(self, k).setText(v)
        for k, v in options["radios"].items():
            getattr(self, k).setChecked(v)
        for k, v in options["spins"].items():
            getattr(self, k).setValue(v)

        self.autopreviewcheck.setChecked(options["checks"]["autopreviewcheck"])

    def get_options(self):
        options = self.defaultoptions
        o = {}
        o["checks"] = {k:getattr(self, k).isChecked() for k in options["checks"].keys()}
        o["combos"] = {k:getattr(self, k).currentIndex() for k in options["combos"].keys()}
        o["edits"] = {k:str(getattr(self, k).text().toUtf8()) for k in options["edits"].keys()}
        o["radios"] = {k:getattr(self, k).isChecked() for k in options["radios"].keys()}
        o["spins"] = {k:getattr(self, k).value() for k in options["spins"].keys()}

        return o

    def get_path(self, index):
        return str(self.dirmodel.filePath(index).toUtf8())

    def get_index(self):
        return self.dirview.currentIndex()

    def set_cwd(self, index=None, force=False):
        "Set the current working directory for renaming actions."
        if not index:
            index = self.get_index()
        path = self.get_path(index)
        if force or path != self.cwd and os.path.isdir(path):
            self.cwd = path
            self.cwdidx = index
            self.dirview.setExpanded(self.cwdidx, True)
            self.update(2)
        elif self.cwd and path == self.cwd:
            self.fileops.stopupdate = True
            self.dirview.setExpanded(self.cwdidx, False)
            self.cwd = ""
            self.cwdidx = None
            self.update_indexview()

    def delete_index(self, indexes=None):
        if not indexes:
            indexes = self.get_selected_indexes()
        for index in indexes:
            path = self.get_path(index)
            name = os.path.basename(path)

            # TODO: Subclass MessageBox to center it on screen?
            m = QtGui.QMessageBox(self)
            reply = m.question(self, "Message", "Delete {}?".format(name),
                               m.Yes | m.No, m.Yes)

            if reply == QtGui.QMessageBox.Yes:
                self.dirmodel.remove(index)

    def on_popmenu(self, position):
        self.menu.clear()

        items = ["Toggle", "Include", "Exclude",
                 "Clear Includes", "Clear Excludes", "Clear Both",
                 "Set/Unset CWD", "Edit", "Delete"]
        for item in items:
            action = self.menu.addAction(item)
            action.triggered[()].connect(lambda i=item: self.menuhandler(i))
        self.menu.exec_(self.dirview.mapToGlobal(position))

    def get_selected_indexes(self):
        indexes = self.dirview.selectionModel().selectedIndexes()
        return indexes[:len(indexes) / 5]

    def toggle_selection(self, mode=0):
        indexes = self.get_selected_indexes()
        for idx in indexes:
            path = self.get_path(idx)
            target = helpers.splitpath_os(path)
            name = target[1] + target[2]
            if mode == 0:  # Toggle Include/Exclude
                if target in self.targets:
                    self.fileops.includes.discard(name)
                    self.fileops.excludes.add(name)
                else:
                    self.fileops.excludes.discard(name)
                    self.fileops.includes.add(name)
            elif mode == 1:  # Include
                self.fileops.excludes.discard(name)
                self.fileops.includes.add(name)
            elif mode == 2:  # Exclude
                self.fileops.includes.discard(name)
                self.fileops.excludes.add(name)
            elif mode == 3:  # Recursive Include
                pass
            elif mode == 4:  # Recursive Exclude
                pass
        log.debug("includes: {}".format(self.fileops.includes))
        log.debug("excludes: {}".format(self.fileops.excludes))
        self.update(2)
        log.debug(self.targets)

    def menuhandler(self, action):
        if action == "Toggle":
            self.toggle_selection(0)
        if action == "Include":
            self.toggle_selection(1)
        if action == "Exclude":
            self.toggle_selection(2)
        if action == "Recursive Include":
            self.toggle_selection(3)
        if action == "Recursive Exclude":
            self.toggle_selection(4)
        elif action == "Clear Includes":
            self.fileops.includes.clear()
        elif action == "Clear Excludes":
            self.fileops.excludes.clear()
        elif action == "Clear Both":
            self.fileops.includes.clear()
            self.fileops.excludes.clear()
            self.update(2)
        elif action == "Set/Unset CWD":
            self.set_cwd()
        elif action == "Edit":
            self.dirview.edit(self.get_index())
        elif action == "Delete":
            self.delete_index()

    def keyPressEvent(self, e):
        "Overloaded to connect return key to self.set_cwd()."
        # TODO: Move this to TreeView only.
        if e.key() == QtCore.Qt.Key_Return:
            self.set_cwd()
        if e.key() == QtCore.Qt.Key_Delete:
            self.delete_index()

    def update(self, mode=1):
        """Main update routine using threading to get targets and/or previews"""
        # Modes: 0 = targets, 1 = previews, 2 = both.
        self.fileops.stopupdate = False
        if not self.autopreview or not self.cwd:
            self.update_view()
            return
        self.updatethread.mode = mode
        self.updatethread.start()

    def on_updatethread_started(self):
        log.debug("Updatethread started.")
        self.statusbar.showMessage("Refreshing...")
        self.refreshbutton.setText("Stop")

    def on_updatethread_finished(self):
        log.debug("Updatethread finished.")
        self.refreshbutton.setText("Refresh")
        if self.cwd:
            lent = len(self.targets)
            lenp = sum(i[0][1] != i[1] for i in self.previews)
            self.statusbar.showMessage("Targets: {}, Staged: {} - {}"
                                   .format(lent, lenp, self.cwd))
        else:
            self.statusbar.showMessage("No working directory set.")
        self.update_view()

    def update_targets(self):
        if self.cwd:
            self.targets = self.fileops.get_targets(self.cwd)
        else:
            self.targets = []

    def update_previews(self):
        if self.cwd:
            self.previews = self.fileops.get_previews(self.targets)
        else:
            self.previews = []

    def update_view(self):
        m, v = self.dirmodel, self.dirview
        r = v.rect()
        m.dataChanged.emit(v.indexAt(r.topLeft()), v.indexAt(r.bottomRight()))

    def update_indexview(self, index=None):
        if index is None:
            index = self.get_index()
        m = self.dirmodel
        m.dataChanged.emit(index, m.index(index.row(), m.columnCount()))

    def on_committhread_started(self):
        log.debug("Committhread started.")
        self.statusbar.showMessage("Committing...")
        self.commitbutton.setText("Stop")

    def on_committhread_finished(self):
        log.debug("Committhread finished.")
        self.commitbutton.setText("Commit")
        self.update(2)

    def connect_elements(self):
        self.dirview.customContextMenuRequested.connect(self.on_popmenu)
        self.updatethread.finished.connect(self.on_updatethread_finished)
        self.updatethread.started.connect(self.on_updatethread_started)
        self.committhread.finished.connect(self.on_committhread_finished)
        self.committhread.started.connect(self.on_committhread_started)

        # Main buttons:
        self.commitbutton.clicked.connect(self.on_commitbutton)
        self.refreshbutton.clicked.connect(self.on_refreshbutton)
        self.undobutton.clicked.connect(self.on_undobutton)
        self.bothradio.toggled.connect(self.on_bothradio)
        self.dirsradio.toggled.connect(self.on_dirsradio)
        self.filesradio.toggled.connect(self.on_filesradio)
        self.switchviewcheck.toggled.connect(self.on_switchviewcheck)

        # Main options:
        self.autopreviewcheck.toggled.connect(self.on_autopreviewcheck)
        self.autostopcheck.toggled.connect(self.on_autostopcheck)
        self.keepextensionscheck.toggled.connect(self.on_keepextensioncheck)
        self.hiddencheck.toggled.connect(self.on_hiddencheck)
        self.manualmirrorcheck.toggled.connect(self.on_manualmirrorcheck)
        self.recursivecheck.toggled.connect(self.on_recursivecheck)
        self.recursivedepth.valueChanged.connect(self.on_recursivedepth)
        self.saveoptionsbutton.clicked.connect(self.on_saveoptionsbutton)
        self.restoreoptionsbutton.clicked.connect(self.on_restoreoptionsbutton)
        self.clearoptionsbutton.clicked.connect(self.on_clearoptionsbutton)

        # Match options:
        self.matchcheck.toggled.connect(self.on_matchcheck)
        self.matchignorecase.toggled.connect(self.on_matchignorecase)
        self.matchreplacecheck.toggled.connect(self.on_matchreplacecheck)
        self.matchexcludecheck.toggled.connect(self.on_matchexcludecheck)
        self.matchfiltercheck.toggled.connect(self.on_matchfiltercheck)
        self.globradio.toggled.connect(self.on_globradio)
        self.regexradio.toggled.connect(self.on_regexradio)
        self.matchedit.textChanged.connect(self.on_matchedit)
        self.replaceedit.textChanged.connect(self.on_replaceedit)
        self.excludeedit.textChanged.connect(self.on_excludeedit)
        self.filteredit.textChanged.connect(self.on_filteredit)

        # Insert options:
        self.insertcheck.toggled.connect(self.on_insertcheck)
        self.insertpos.valueChanged.connect(self.on_insertpos)
        self.insertedit.textChanged.connect(self.on_insertedit)

        # Delete options:
        self.deletecheck.toggled.connect(self.on_deletecheck)
        self.deletestart.valueChanged.connect(self.on_deletestart)
        self.deleteend.valueChanged.connect(self.on_deleteend)

        # Count options:
        self.countcheck.toggled.connect(self.on_countcheck)
        self.countbase.valueChanged.connect(self.on_countbase)
        self.countpos.valueChanged.connect(self.on_countpos)
        self.countstep.valueChanged.connect(self.on_countstep)
        self.countpreedit.textChanged.connect(self.on_countpreedit)
        self.countsufedit.textChanged.connect(self.on_countsufedit)
        self.countfillcheck.toggled.connect(self.on_countfillcheck)

        # Remove options:
        self.removecheck.toggled.connect(self.on_removecheck)
        self.removeduplicatescheck.toggled.connect(self.on_removeduplicates)
        self.removeextensionscheck.toggled.connect(self.on_removeextensions)
        self.removenonwordscheck.toggled.connect(self.on_removenonwords)
        self.removesymbolscheck.toggled.connect(self.on_removesymbols)

        self.casecheck.toggled.connect(self.on_casecheck)
        self.casebox.currentIndexChanged[int].connect(self.on_casebox)
        self.spacecheck.toggled.connect(self.on_spacecheck)
        self.spacebox.currentIndexChanged[int].connect(self.on_spacebox)

        self.mediamodecheck.toggled.connect(self.on_mediamodecheck)
        self.dualmodecheck.toggled.connect(self.on_dualmodecheck)

    def on_saveoptionsbutton(self):
        """Save current options to configfile."""
        log.info("Saving options.")
        helpers.save_configfile(self.fileops.configdir, self.get_options())
        self.statusbar.showMessage("Configuration file saved.")

    def on_restoreoptionsbutton(self):
        """Restore options to start point."""
        log.info("Restoring options.")
        self.set_options(self.startoptions)

    def on_clearoptionsbutton(self):
        """Reset/Clear all options."""
        log.info("Clearing options.")
        self.set_options(sanitize=True)

    def on_commitbutton(self):
        """Perform the currently previewed rename actions."""
        log.info("Committing previewed changes.")
        if self.committhread.isRunning():
            self.fileops.stopcommit = True
        else:
            self.fileops.stopcommit = False
            self.committhread.start()

    def on_undobutton(self):
        """Pops the history stack of commits, reverting the one on top."""
        log.info("Reverting last commit.")
        self.fileops.undo()
        self.update(2)

    def on_refreshbutton(self):
        """Force a refresh of browser view and model."""
        if self.updatethread.isRunning():
            self.fileops.stopupdate = True
        else:
            self.update(2)

    def on_autopreviewcheck(self, checked):
        self.autopreview = checked
        if checked:
            self.update(2)

    def on_keepextensioncheck(self, checked):
        self.fileops.keepext = checked
        if checked:
            self.removeextensionscheck.setChecked(False)
        self.update()

    def on_hiddencheck(self, checked):
        self.fileops.hidden = checked
        # TODO: Delegate gets overriden by filter here?
        if checked:
            self.dirmodel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Files |
                                    QtCore.QDir.NoDotAndDotDot |
                                    QtCore.QDir.Hidden)
        else:
            self.dirmodel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Files |
                                        QtCore.QDir.NoDotAndDotDot)
        self.update(2)

    def on_manualmirrorcheck(self, checked):
        self.fileops.manualmirror = checked
        self.update()

    def on_recursivecheck(self, checked):
        self.fileops.recursive = checked
        if not checked:
            self.recursivedepth.setValue(0)
        self.update(2)

    def on_recursivedepth(self, num):
        self.fileops.recursivedepth = int(num)
        self.update(2)

    def on_autostopcheck(self, checked):
        self.fileops.autostop = checked

    def on_matchcheck(self, checked):
        self.fileops.matchcheck = checked
        if not checked:
            self.matchedit.setEnabled(False)
            self.replaceedit.setEnabled(False)
            self.filteredit.setEnabled(False)
            self.excludeedit.setEnabled(False)
        else:
            if self.matchreplacecheck.isChecked():
                self.matchedit.setEnabled(True)
                self.replaceedit.setEnabled(True)
            if self.matchfiltercheck.isChecked():
                self.filteredit.setEnabled(True)
            if self.matchexcludecheck.isChecked():
                self.excludeedit.setEnabled(True)
        self.update()

    def on_matchignorecase(self, checked):
        self.fileops.ignorecase = checked
        self.update()

    def on_filteredit(self, text):
        text = str(text.toUtf8())
        self.fileops.filteredit = text
        self.update(2)

    def on_excludeedit(self, text):
        text = str(text.toUtf8())
        self.fileops.excludeedit = text
        self.update(2)

    def on_insertedit(self, text):
        text = str(text.toUtf8())
        self.fileops.insertedit = text
        self.update()

    def on_countpreedit(self, text):
        text = str(text.toUtf8())
        self.fileops.countpreedit = text
        self.update()

    def on_countsufedit(self, text):
        text = str(text.toUtf8())
        self.fileops.countsufedit = text
        self.update()

    def on_matchedit(self, text):
        text = str(text.toUtf8())
        self.fileops.matchedit = text
        self.update()

    def on_replaceedit(self, text):
        text = str(text.toUtf8())
        self.fileops.replaceedit = text
        self.update()

    def on_matchfiltercheck(self, checked):
        self.fileops.matchfiltercheck = checked
        self.update(2)

    def on_matchexcludecheck(self, checked):
        self.fileops.matchexcludecheck = checked
        self.update(2)

    def on_matchreplacecheck(self, checked):
        self.fileops.matchreplacecheck = checked
        self.update()

    def on_globradio(self, checked):
        self.fileops.regex = not checked
        if self.fileops.matchfiltercheck or self.fileops.matchexcludecheck:
            self.update(0)
        self.update()

    def on_regexradio(self, checked):
        self.fileops.regex = checked
        if self.fileops.matchfiltercheck or self.fileops.matchexcludecheck:
            self.update(0)
        self.update()

    def on_insertcheck(self, checked):
        self.fileops.insertcheck = checked
        self.update()

    def on_insertpos(self, num):
        self.fileops.insertpos = int(num)
        self.update()

    def on_countcheck(self, checked):
        self.fileops.countcheck = checked
        self.update()

    def on_countbase(self, num):
        self.fileops.countbase = int(num)
        self.update()

    def on_countpos(self, num):
        self.fileops.countpos = int(num)
        self.update()

    def on_countstep(self, num):
        self.fileops.countstep = int(num)
        self.update()

    def on_countfillcheck(self, checked):
        self.fileops.countfill = checked
        self.update()

    def on_removecheck(self, checked):
        self.fileops.removecheck = checked
        self.update()

    def on_removeduplicates(self, checked):
        self.fileops.remdups = checked
        self.update()

    def on_removeextensions(self, checked):
        self.fileops.remext = checked
        if checked:
            self.keepextensionscheck.setChecked(False)
        self.update()

    def on_removenonwords(self, checked):
        self.fileops.remnonwords = checked
        self.update()

    def on_removesymbols(self, checked):
        self.fileops.remsymbols = checked
        self.update()

    def save_premediaoptions(self):
        self.checksaves = {i: i.isChecked() for i in self.mediachecks}
        self.combosaves = {i: i.currentIndex() for i in self.mediaboxes}

    def restore_premediaoptions(self):
        for k, v in self.checksaves.items():
            k.setChecked(v)
        for k, v in self.combosaves.items():
            k.setCurrentIndex(v)

    def on_mediamodecheck(self, checked):

        self.autopreviewcheck.setChecked(False)

        if checked:
            self.save_premediaoptions()
#             self.fileops.keepext = True
            for i in self.mediachecks:
                i.setChecked(True)
            self.spacebox.setCurrentIndex(6)
            self.casebox.setCurrentIndex(0)
        else:
            self.restore_premediaoptions()

        self.autopreviewcheck.setChecked(True)
        self.update()

    def on_dualmodecheck(self, checked):
        if checked:
            self.dualoptions1 = self.get_options()
            self.set_options(self.dualoptions2)
        else:
            self.dualoptions2 = self.get_options()
            self.set_options(self.dualoptions1)
        self.update()

    def on_switchviewcheck(self, checked):
        self.switchview = checked
        log.debug("switchview: {}".format(checked))
        if self.filesradio.isChecked():
            self.on_filesradio(True)
        elif self.dirsradio.isChecked():
            self.on_dirsradio(True)
        elif self.bothradio.isChecked():
            self.on_bothradio(True)

    def on_bothradio(self, checked):
        self.fileops.filesonly = False
        self.fileops.dirsonly = False
        if self.switchview:
            self.dirmodel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Files |
                                    QtCore.QDir.NoDotAndDotDot |
                                    QtCore.QDir.Hidden)
        self.update(2)

    def on_dirsradio(self, checked):
        self.fileops.dirsonly = checked
        if self.switchview:
            self.dirmodel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Hidden |
                                    QtCore.QDir.NoDotAndDotDot)
        self.update(2)

    def on_filesradio(self, checked):
        self.fileops.filesonly = checked
        if self.switchview:
            self.dirmodel.setFilter(QtCore.QDir.Files | QtCore.QDir.Hidden |
                                    QtCore.QDir.NoDotAndDotDot)
        self.update(2)

    def on_spacecheck(self, checked):
        self.fileops.spacecheck = checked
        self.update()

    def on_casecheck(self, checked):
        self.fileops.casecheck = checked
        self.update()

    def on_deletecheck(self, checked):
        self.fileops.deletecheck = checked
        self.update()

    def on_deletestart(self, num):
        self.fileops.deletestart = int(num)
        self.update()

    def on_deleteend(self, num):
        self.fileops.deleteend = int(num)
        self.update()

    def on_casebox(self, index):
        self.fileops.casemode = index
        self.update()

    def on_spacebox(self, index):
        self.fileops.spacemode = index
        self.update()

    @property
    def cwd(self):
        return self._cwd

    @cwd.setter
    def cwd(self, path):
        path = str(path)
        # Exit out if dir is not a valid target.
        self._cwd = path
        log.debug("cwd: {}".format(path))
        if path:
            self.statusbar.showMessage("Root is now {}.".format(path))
        else:
            self.statusbar.showMessage("No root set.")

    @property
    def cwdidx(self):
        return self._cwdidx

    @cwdidx.setter
    def cwdidx(self, index):
        self._cwdidx = index

    @property
    def autopreview(self):
        return self._autopreview

    @autopreview.setter
    def autopreview(self, boolean):
        self._autopreview = boolean
        log.debug("autopreview: {}".format(boolean))


def main():
    "Main entry point for demimove-ui."
    startdir = os.getcwd()
    configfile = None
    try:
        args = docopt(__doc__, version="0.2")
#         args["-v"] = 3  # Force debug logging
        fileop = fileops.FileOps(verbosity=args["-v"],
                                 quiet=args["--quiet"])
        if args["<path>"]:
            startdir = args["<path>"]
        if args["--config"]:
            configfile = args["--config"]
    except NameError:
        fileop = fileops.FileOps()
        log.error("Please install docopt to use the CLI.")

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName("demimove-ui")
    gui = DemiMoveGUI(startdir, fileop, configfile)
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
