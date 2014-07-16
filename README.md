demimove
========

####A file browser for mass renaming  

Demimove is a file browser written with python2.7 and PyQt4.  
A couple of features you might find interesting:  
* Multiple Pattern Support: You can have any number of match and filter patterns by separating them with a slash ("/").
* Include/Exclude multiple targets at once interactively, by selecting them in the browser and right-clicking.
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
![ScreenShot](http://a.pomf.se/qqbmjz.png) 
![ScreenShot](http://a.pomf.se/ywdmuf.png)  

Press Enter or select "Set/Unset CWD" in the context menu to set the current index as working directory.
You can select multiple files and include/exclude them via context menu if you don't feel like matching them with an expression. 


#### TODO  
Features i'd like to include when i get time to work on this again:   
* A status tab that shows errors, warnings and general status information.  
* A history tab that stores and displays all commited rename operations and allows reversing them.  
* Metatags for Audio, Video and Image files
* Make the CLI functional.
* Replace os.walk with QDirIterator to possibly gain lots of speed.

#### Known Bugs
* Trying to access mounted but unavailable samba/nfs shares will freeze the program. I don't think this is something i can fix. Restart required.
* Renaming files on a mounted samba/nfs share can sometimes result in the QFileSystemModel not being able to refresh the listing for that directory. Restart required, if you want to keep working with that particular directory. 
