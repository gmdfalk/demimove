demimove
========

####A file browser for mass renaming  

Demimove is a mass renaming file browser for Linux and Windows, written with python2.7 and PyQt4.  

A couple of features you might find interesting:
* Interactivity: Demimove allows adding/removing of (multiple) targets quickly by mouse interaction (instead of  or complementary to matching via regex/globbing patterns).
* Automatic Previews: Demimove provides an automatic and immediate preview of any change.  
* Performance: Demimove is fast, thanks to Qt and its QFileSystemModel. Even thousands of files are no problem (although there's a ceiling, as always).  
* Commit History: You can undo any commit, although currently only in order of last to first.  
* Multiple Pattern Support: You can have any number of match and filter patterns by separating them with a slash ("/").
* Recursive support: Demimove supports recursive lookups and renames. You can specify the depth of the recursion.  
* Config File: You can save and restore options to and from a file (~/.config/demimove/demimove.ini).  

Other than that, it hopefully comes with everything you'd expect from a standard mass renamer, including regex/globbing support and preconfigured actions.

#### Installation  
Make sure you have the following packages on your system:  
* Python2.7  
* PyQt4  
* git  
* pip  
* docopt (optional for the GUI, enables some startup options)

To install pip on Windows I suggest using `get-pip.py` from https://pip.pypa.io/en/latest/installing.html.  

Install demimove as follows:  
```
git clone https://github.com/mikar/demimove
cd demimove
(pip install docopt)
pip install .
```

To just test the application or if you do not wish to install it, navigate to `demimove/demimove` and try python[.exe] gui.py.  

#### Usage
![ScreenShot](http://a.pomf.se/qqbmjz.png) 
![ScreenShot](http://a.pomf.se/ywdmuf.png)  

Press Enter or select "Set/Unset CWD" in the context menu to set the current index as working directory.
You can select multiple files and include/exclude them via context menu if you don't feel like matching them with an expression. 

# Note on regular expressions vs globbing
All globbing patterns are translated to regular expressions. Especially for non-trivial patterns (multiple wildcards etc) translation errors might occur.
The translation method is something i plan to revisit but for the time being I suggest you use regular expressions if you notice your globbing pattern behaving oddly.

#### TODO  
Features i'd like to include when i get time to work on this again:   
* A status tab that shows errors, warnings and general status information.  
* A history tab that stores and displays all commited rename operations and allows reversing them.  
* A metatags tab to allow mass renaming of audio, video and image metatags.  
* Making the CLI functional. This includes revisiting globbing to regex translation which is currently rudimentary.
* Replacing os.walk with QDirIterator to possibly gain lots of speed.

#### Known Bugs
* Trying to access mounted but unavailable samba/nfs shares will freeze the program. I don't think this is something i can fix. Restart of demimove required.
* Renaming files on a mounted samba/nfs share can sometimes result in the QFileSystemModel not being able to refresh the listing for that directory. Restart of demimove required, if you want to keep working with that particular directory. 
