# -*- coding: utf-8 -*-
"""demimove-ui

Usage:
    demimove-ui [-d <path>] [-c <file>] [-v|-vv|-vvv] [-q] [-h]

Options:
    -c, --config=<file>  <NYI> Specify a config file to load.
    -d, --dir=<path>     Specify the working directory. Otherwise CWD is used.
    -v                   Logging verbosity level, up to -vvv.
    -q, --quiet          Do not print logging messages to console.
    -h,  --help          Show this help text and exit.
    --version            Show the current demimove-ui version.
"""
# TODO: History tab.
# TODO: Statustab with Errors/Warnings, Summaries etc.
# TODO: Threading for get_previews/get_targets and statusbar progress.
# TODO: Custom ContextMenu for Filebrowser
# FIXME: Filesonly radio + switchview, bold font.
# FIXME: Fix performance on many files (recursive)? Maybe threading?
# TODO: Use QFileSystemModels listing instead of fileops.get_targets()
import logging
import os
import sys

from PyQt4 import Qt, QtGui, QtCore, uic

import fileops
import history
from demimove import helpers


log = logging.getLogger("gui")

try:
    from docopt import docopt
except ImportError:
    print "ImportError: Please install docopt to use the CLI."


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
#                 item = self.data(fileindex, role).toString().toUtf8()
#                 item = str(item).decode("utf-8")
                return self.match_preview(fileindex)

        return super(DirModel, self).data(index, role)

    def match_preview(self, index, *args):
        if not self.p.cwdidx:
            return
        if not self.p.fileops.recursive and index.parent() != self.p.cwdidx:
            return
        itempath = str(self.filePath(index).toUtf8()).decode("utf-8")
        if self.p.cwd in itempath and itempath in self.p.joinedtargets:
            idx = self.p.joinedtargets.index(itempath)
            try:
                return self.p.previews[idx][1]
            except IndexError:
                pass  # Fail silently.

    def match_preview_depth(self, index, item):
        """Currently unused."""
        par, cidx = index.parent(), self.p.cwdidx
        parents = [par]
        # Create a list of n generations to specify path depth.
        if self.p.fileops.recursive:
            for _ in xrange(5):
                par = par.parent()
                parents.append(par)
        if cidx in parents:
            if item in self.p.nametargets:
                idx = self.p.nametargets.index(item)
                return self.p.previews[idx][1]


class DemiMoveGUI(QtGui.QMainWindow):

    def __init__(self, startdir, fileops, parent=None):

        super(DemiMoveGUI, self).__init__(parent)
        self.fileops = fileops
        # Current working directory.
        self._autopreview = True
        self._cwd = ""
        self._cwdidx = None
        self.basedir = os.path.dirname(os.path.realpath(__file__))
        self.guifile = os.path.join(self.basedir, "data/gui.ui")
        self.iconfile = os.path.join(self.basedir, "data/icon.png")
        self.switchview = False
        self.previews = []
        self.targets = []
        uic.loadUi(self.guifile, self)
        if self.fileops.configdir:
            self.histfile = os.path.join(self.fileops.configdir, "history.txt")
            self.apply_options()

        else:
            self.histfile = os.path.join(self.basedir, "data/history.txt")

        self.setWindowIcon(QtGui.QIcon(self.iconfile))
        self.mainsplitter.setStretchFactor(0, 2)
        self.mainsplitter.setStretchFactor(1, 3)

        self.checks = [self.casecheck, self.spacecheck, self.removecheck,
                       self.removesymbolscheck, self.removeduplicatescheck,
                       self.autopreviewcheck, self.keepextensionscheck,
                       self.removenonwordscheck, self.removeextensionscheck]
        self.boxes = [self.casebox, self.spacebox]

        self.create_browser(startdir)
        self.create_historytab()
        self.connect_elements()
        log.info("demimove-ui initialized.")
        self.statusbar.showMessage("Select a directory and press Enter.")

    def apply_options(self):
        options = helpers.load_configfile(self.fileops.configdir)
        print options
        helpers.save_configfile(self.fileops.configdir, options)
#         for k, v in options["combos"]:
#         for k, v in options["edits"]:
#         for k, v in options["radios"]:
#         for k, v in options["spins"]:
#             print k, v

    def create_browser(self, startdir):
        # TODO: With readOnly disabled we can use setData for file operations?
        self.dirmodel = DirModel(self)
        self.dirmodel.setReadOnly(False)
        self.dirmodel.setRootPath("/")
        self.dirmodel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Files |
                                    QtCore.QDir.NoDotAndDotDot |
                                    QtCore.QDir.Hidden)

        self.dirview.setModel(self.dirmodel)
        self.dirview.setColumnHidden(2, True)
        self.dirview.header().swapSections(4, 1)
        self.dirview.header().resizeSection(0, 300)
        self.dirview.header().resizeSection(4, 220)
        self.dirview.header().resizeSection(3, 120)
        self.dirview.setEditTriggers(QtGui.QAbstractItemView.EditKeyPressed)
        self.dirview.setItemDelegate(BoldDelegate(self))
        self.dirview.setCurrentIndex(self.dirmodel.index(startdir))

    def create_historytab(self):
        self.historymodel = history.HistoryTreeModel(self.histfile, self)
        self.historytree.setModel(self.historymodel)

    def get_current_fileinfo(self):
        index = self.dirview.currentIndex()
        path = str(self.dirmodel.filePath(index).toUtf8()).decode("utf-8")
        return index, path

    def set_cwd(self, force=False):
        "Set the current working directory for renaming actions."
        index, path = self.get_current_fileinfo()
        if force or path != self.cwd and os.path.isdir(path):
            self.cwd = path
            self.cwdidx = index
            self.dirview.setExpanded(self.cwdidx, True)
        elif self.cwd and path == self.cwd:
            self.dirview.setExpanded(self.cwdidx, False)
            self.cwd = ""
            self.cwdidx = None
        self.update_single_index(index)

    def center(self, widget=None):
        if widget is None:
            widget = self
        qr = widget.frameGeometry()
        cp = QtGui.QDesktopWidget().availableGeometry().center()
        qr.moveCenter(cp)
        widget.move(qr.topLeft())

    def delete_item(self):
        index, path = self.get_current_fileinfo()
        name = os.path.basename(path)

        # TODO: Subclass MessageBox to center it on screen?
        m = QtGui.QMessageBox(self)
        reply = m.question(self, "Message", "Delete {}?".format(name),
                           m.Yes | m.No, m.Yes)

        if reply == QtGui.QMessageBox.Yes:
            self.dirmodel.remove(index)

    def keyPressEvent(self, e):
        "Overloaded to connect return key to self.set_cwd()."
        # TODO: Move this to TreeView only.
        if e.key() == QtCore.Qt.Key_Return:
            self.set_cwd()
            self.update_targets()
            self.update_preview()
        if e.key() == QtCore.Qt.Key_Delete:
            self.delete_item()

    def update_targets(self):
        if self.cwd:
            self.targets = self.fileops.get_targets(self.cwd)
            self.joinedtargets = ["".join(i) for i in self.targets]
            self.statusbar.showMessage("Found {} targets in {}."
                                       .format(len(self.targets), self.cwd))
        else:
            self.targets, self.joinedtargets = [], []

    def update_preview(self):
        if self.cwd:
            self.previews = self.fileops.get_previews(self.targets)
        else:
            self.previews = []
        self.update_view()

    def update_view(self):
        m, v = self.dirmodel, self.dirview
        r = v.rect()
        m.dataChanged.emit(v.indexAt(r.topLeft()), v.indexAt(r.bottomRight()))

    def update_single_index(self, index):
        m = self.dirmodel
        m.dataChanged.emit(index, m.index(index.row(), m.columnCount()))

    def connect_elements(self):
        # Main buttons:
        self.commitbutton.clicked.connect(self.on_commitbutton)
        self.undobutton.clicked.connect(self.on_undobutton)
        self.bothradio.toggled.connect(self.on_bothradio)
        self.dirsradio.toggled.connect(self.on_dirsradio)
        self.filesradio.toggled.connect(self.on_filesradio)
        self.switchviewcheck.toggled.connect(self.on_switchviewcheck)

        # Main options:
        self.autopreviewcheck.toggled.connect(self.on_autopreviewcheck)
        self.autostopcheck.toggled.connect(self.on_autostopcheck)
        self.keepextensionscheck.toggled.connect(self.on_extensioncheck)
        self.hiddencheck.toggled.connect(self.on_hiddencheck)
        self.manualmirrorcheck.toggled.connect(self.on_manualmirrorcheck)
        self.recursivecheck.toggled.connect(self.on_recursivecheck)
        self.recursivedepth.valueChanged.connect(self.on_recursivedepth)
        self.saveoptionsbutton.clicked.connect(self.on_saveoptionsbutton)
        self.resetoptionsbutton.clicked.connect(self.on_resetoptionsbutton)

        # Match options:
        self.matchcheck.toggled.connect(self.on_matchcheck)
        self.matchignorecase.toggled.connect(self.on_matchignorecase)
        self.matchreplacecheck.toggled.connect(self.on_matchreplacecheck)
        self.matchexcludecheck.toggled.connect(self.on_matchexcludecheck)
        self.matchfiltercheck.toggled.connect(self.on_matchfiltercheck)
        self.globradio.toggled.connect(self.on_matchglob)
        self.regexradio.toggled.connect(self.on_matchregex)
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
        log.info("Saving options.")
        self.update_preview()

    def on_resetoptionsbutton(self):
        log.info("Resetting options.")
        self.update_preview()

    def on_commitbutton(self):
        log.info("Committing previewed changes.")
        self.update_preview()
        commit = self.fileops.commit(self.previews)
#         self.history.append(commit)

    def on_undobutton(self):
        log.info("Reverting last commit.")
        self.fileops.undo()

    def on_autopreviewcheck(self, checked):
        self.autopreview = checked
        if checked:
            self.update_preview()

    def on_extensioncheck(self, checked):
        self.fileops.keepext = checked
        if checked:
            self.removeextensionscheck.setChecked(False)
        if self.autopreview:
            self.update_preview()

    def on_hiddencheck(self, checked):
        self.fileops.hidden = checked
        if self.autopreview:
            self.update_targets()
            self.update_preview()

    def on_manualmirrorcheck(self, checked):
        self.fileops.manualmirror = checked
        if self.autopreview:
            self.update_preview()

    def on_recursivecheck(self, checked):
        self.fileops.recursive = checked
        if self.autopreview:
            self.update_targets()
            self.update_preview()

    def on_recursivedepth(self, num):
        self.fileops.recursivedepth = int(num)
        if self.autopreview:
            self.update_targets()
            self.update_preview()

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
        if self.autopreview:
            self.update_preview()

    def on_matchignorecase(self, checked):
        self.fileops.ignorecase = checked
        if self.autopreview:
            self.update_preview()

    def on_filteredit(self, text):
        text = str(text.toUtf8())
        self.fileops.filteredit = text
        if self.autopreview:
            self.update_preview()

    def on_excludeedit(self, text):
        text = str(text.toUtf8())
        self.fileops.excludeedit = text
        if self.autopreview:
            self.update_preview()

    def on_matchfiltercheck(self, checked):
        self.fileops.matchexcludecheck = checked
        if self.autopreview:
            self.update_preview()

    def on_matchexcludecheck(self, checked):
        self.fileops.matchexcludecheck = checked
        if self.autopreview:
            self.update_preview()

    def on_matchreplacecheck(self, checked):
        self.fileops.matchreplacecheck = checked
        if self.autopreview:
            self.update_preview()

    def on_matchglob(self, checked):
        self.fileops.regex = not checked
        if self.autopreview:
            self.update_preview()

    def on_matchregex(self, checked):
        self.fileops.regex = checked
        if self.autopreview:
            self.update_preview()

    def on_insertcheck(self, checked):
        self.fileops.insertcheck = checked
        if self.autopreview:
            self.update_preview()

    def on_insertpos(self, num):
        self.fileops.insertpos = int(num)
        if self.autopreview:
            self.update_preview()

    def on_insertedit(self, text):
        text = str(text.toUtf8())
        self.fileops.insertedit = text
        if self.autopreview:
            self.update_preview()

    def on_countcheck(self, checked):
        self.fileops.countcheck = checked
        if self.autopreview:
            self.update_preview()

    def on_countbase(self, num):
        self.fileops.countbase = int(num)
        if self.autopreview:
            self.update_preview()

    def on_countpos(self, num):
        self.fileops.countpos = int(num)
        if self.autopreview:
            self.update_preview()

    def on_countstep(self, num):
        self.fileops.countstep = int(num)
        if self.autopreview:
            self.update_preview()

    def on_countpreedit(self, text):
        text = str(text.toUtf8())
        self.fileops.countpreedit = text
        if self.autopreview:
            self.update_preview()

    def on_countsufedit(self, text):
        text = str(text.toUtf8())
        self.fileops.countsufedit = text
        if self.autopreview:
            self.update_preview()

    def on_countfillcheck(self, checked):
        self.fileops.countfill = checked
        if self.autopreview:
            self.update_preview()

    def on_removecheck(self, checked):
        self.fileops.removecheck = checked
        if self.autopreview:
            self.update_preview()

    def on_removeduplicates(self, checked):
        self.fileops.remdups = checked
        if self.autopreview:
            self.update_preview()

    def on_removeextensions(self, checked):
        self.fileops.remext = checked
        if checked:
            self.keepextensionscheck.setChecked(False)
        if self.autopreview:
            self.update_preview()

    def on_removenonwords(self, checked):
        self.fileops.remnonwords = checked
        if self.autopreview:
            self.update_preview()

    def on_removesymbols(self, checked):
        self.fileops.remsymbols = checked
        if self.autopreview:
            self.update_preview()

    def save_options(self):
        self.checksaves = {i: i.isChecked() for i in self.checks}
        self.combosaves = {i: i.currentIndex() for i in self.boxes}

    def restore_options(self):
        for k, v in self.checksaves.items():
            k.setChecked(v)
        for k, v in self.combosaves.items():
            k.setCurrentIndex(v)

    def set_defaultoptions(self):
        for i in self.checks:
            i.setChecked(False)
        self.autopreviewcheck.setChecked(True)
        self.spacebox.setCurrentIndex(0)
        self.casebox.setCurrentIndex(0)

    def set_mediaoptions(self):
        for i in self.checks[:-2]:
            i.setChecked(True)
        self.spacebox.setCurrentIndex(6)
        self.casebox.setCurrentIndex(0)

    def toggle_options(self, boolean, mode=0):
        if boolean:
            self.save_options()
            if mode == 0:
                self.set_mediaoptions()
            elif mode == 1:
                self.set_defaultoptions()
        else:
            self.restore_options()

    def on_dualmodecheck(self, checked):
        self.toggle_options(checked, mode=1)
        if self.autopreview:
            self.update_preview()

    def on_mediamodecheck(self, checked):
        self.toggle_options(checked, mode=0)
        if self.autopreview:
            self.update_preview()

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
        if self.autopreview:
            self.update_targets()
            self.update_preview()

    def on_dirsradio(self, checked):
        self.fileops.dirsonly = checked
        if self.switchview:
            self.dirmodel.setFilter(QtCore.QDir.Dirs | QtCore.QDir.Hidden |
                                    QtCore.QDir.NoDotAndDotDot)
        if self.autopreview:
            self.update_targets()
            self.update_preview()

    def on_filesradio(self, checked):
        self.fileops.filesonly = checked
        if self.switchview:
            self.dirmodel.setFilter(QtCore.QDir.Files | QtCore.QDir.Hidden |
                                    QtCore.QDir.NoDotAndDotDot)
        if self.autopreview:
            self.update_targets()
            self.update_preview()

    def on_spacecheck(self, checked):
        self.fileops.spacecheck = checked
        if self.autopreview:
            self.update_preview()

    def on_casecheck(self, checked):
        self.fileops.casecheck = checked
        if self.autopreview:
            self.update_preview()

    def on_matchedit(self, text):
        text = str(text.toUtf8())
        self.fileops.matchedit = text
        if self.autopreview:
            self.update_preview()

    def on_replaceedit(self, text):
        text = str(text.toUtf8())
        self.fileops.replaceedit = text
        if self.autopreview:
            self.update_preview()

    def on_deletecheck(self, checked):
        self.fileops.deletecheck = checked
        if self.autopreview:
            self.update_preview()

    def on_deletestart(self, num):
        self.fileops.deletestart = int(num)
        if self.autopreview:
            self.update_preview()

    def on_deleteend(self, num):
        self.fileops.deleteend = int(num)
        if self.autopreview:
            self.update_preview()

    def on_casebox(self, index):
        self.fileops.casemode = index
        if self.autopreview:
            self.update_preview()

    def on_spacebox(self, index):
        self.fileops.spacemode = index
        if self.autopreview:
            self.update_preview()

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

    @property
    def matchpat(self):
        return self._matchpat

    @matchpat.setter
    def matchpat(self, text):
        log.debug("matchpat: {}".format(text))
        self._matchpat = str(text)

    @property
    def replacepat(self):
        return self._replacepat

    @replacepat.setter
    def replacepat(self, text):
        log.debug("replacepat: {}".format(text))
        self._replacepat = str(text)


def main():
    "Main entry point for demimove-ui."
    startdir = os.getcwd()
    try:
        args = docopt(__doc__, version="0.1")
        args["-v"] = 3  # Force debug mode, for now.
        fileop = fileops.FileOps(verbosity=args["-v"],
                                 quiet=args["--quiet"])
        if args["--dir"]:
            startdir = args["--dir"]
    except NameError:
        fileop = fileops.FileOps()
        log.error("Please install docopt to use the CLI.")

    app = QtGui.QApplication(sys.argv)
    app.setApplicationName("demimove-ui")
#     app.setStyle("plastique")
    gui = DemiMoveGUI(startdir, fileop)
    gui.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
