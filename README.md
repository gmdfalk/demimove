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
 * Performance: Demimove is fast and responsive, thanks to QT and its QFileSystemModel. Even thousands of files are no problem (although there's a ceiling, as always).
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
 
 