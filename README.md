demimove
========

####A file browser for mass renaming  

![ScreenShot](http://a.pomf.se/thqawv.png) 

Demimove is a file browser written with python2.7 and PyQt4.  
A couple of features you might find interesting:  
 * Commit History: You can undo any commit, although currently only in order of last to first.  
 * Automatic Previews: Demimove is very responsive and provides an immediate preview for any changes.  
 * Config File: You can save and restore options to and from a file (~/.config/demimove/demimove.ini).  
 * Recursive support: Demimove supports recursive lookups and renames. You can specify the depth of the recursion, too.  
 * Performance: Demimove is fast and responsive, thanks to Qt and its QFileSystemModel. Even thousands of files are no problem (although there's a ceiling, as always).  
 * Regular expression and globbing pattern support, as you'd expect.  
 * Lots of more or less useful builtin options to experiment with.  
 
 #### Installation  
 Install demimove as follows:  
 ```
 git clone https://github.com/mikar/demimove
 cd demimove
 pip install .
 ```

 There is a CLI version but its currently not really in a usable state.  
 
 #### Usage
 The screenshot is pretty self-explanatory but what might not be apparent is that you need to select a working directory before any previews or changes will be shown.   
 You can do that by selecting a directory in the file browser and pressing Enter. Pressing Enter again on that same folder will unset the working directory.  
 
 #### TODO  
 Features i'd like to include when i get time to work on this again:   
 * A status tab that shows errors, warnings and general status information.  
 * A history tab that stores and displays all commited rename operations and allows reversing them.  
 * Threading to avoid possible lag for a high amount of targets (>10k).  
 * A custom contextmenu for the QFileSystemModel/QTreeView with typical file browser actions (Rename, Delete, Toggle show/hidden etc).  
 
 There are also some defunct features, currently:  
 * The ignorecase check is not hooked to anything.  
 * The same goes for "Mirror manual" and "Stop on error" although these three would all be trivial to implement and may come soon.  
