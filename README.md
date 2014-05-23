demimove
========

####A file browser for mass renaming  

![ScreenShot](http://a.pomf.se/thqawv.png) 

Demimove is a file browser written with python2.7 and PyQt4.  
A couple of features you might find interesting:  
 * Multiple Pattern Support: You can have any number of match and filter patterns by separating them with a slash ("/").
 * Include/Exclude files interactively, by selecting them in the browser.
 * Commit History: You can undo any commit, although currently only in order of last to first.  
 * Automatic Previews: Demimove is provides an automatic and immediate preview for any changes.  
 * Config File: You can save and restore options to and from a file (~/.config/demimove/demimove.ini).  
 * Recursive support: Demimove supports recursive lookups and renames. You can specify the depth of the recursion.  
 * Performance: Demimove is fast, thanks to Qt and its QFileSystemModel. Even thousands of files are no problem (although there's a ceiling, as always).  
 * Regular expression and globbing pattern support, as you'd expect.  
 * Lots of builtin options to experiment with.  
 
 #### Installation  
 Install demimove as follows:  
 ```
 git clone https://github.com/mikar/demimove
 cd demimove
 pip install .
 ```
 
 #### Usage
 The screenshot is pretty self-explanatory but what might not be apparent is that you need to select a working directory before any previews or changes will be shown.   
 You can do that by selecting a directory in the file browser and pressing Enter. Pressing Enter again on that same folder will unset the working directory.  
 Alternatively, a contextmenu will pop up when you right click on an item where you can set the working directory among other things.
 
 #### TODO  
 Features i'd like to include when i get time to work on this again:   
 * A status tab that shows errors, warnings and general status information.  
 * A history tab that stores and displays all commited rename operations and allows reversing them.  
 * Metatags for Audio, Video and Image files
 * Make the CLI functional.
 * Replace os.walk with QDirIterator to possibly gain lots of speed.