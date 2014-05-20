# -*- coding: utf-8 -*-
"""demimove

Usage:
    demimove [<matchpattern> [<replacepattern>]] [-d|-f] [-e <names>]
             [-v|-vv|-vvv] [options]

Arguments:
    matchpattern    (Optional) Pattern to identify targets by.
                    Defaults to globbing but can be set to regular expression.
                    With no other options set, this will match against all
                    non-hidden file and folder names in the current directory.
    replacepattern  Optional replacement pattern for the match pattern.
                    For glob patterns, the number of wild cards has to match
                    those in the match pattern.

Options:
    -a, --all              Include hidden files/directories.
    -c, --count=<n>        Inserts an index at position n counting up from 1.
    -d, --dirsonly         Only search directory names. Default is files + dirs.
    -e, --exclude=<names>  Exclude files/directories (glob). Colon separated.
    -f, --filesonly        Only search file names. Default is files + dirs.
    -k, --keep-extension   Preserve file remext.
    -i, --interactive      Confirm before renaming.
    -n, --no-clobber       Do not overwrite an existing file.
    -p, --path=<path>      Specify the path to start in. Otherwise cwd is used.
    -r, --recursive        Apply changes recursively.
    -s, --simulate         Do a test run and dump the results to console.
    -C, --casemode         0 = All lowercase, 1 = uppercase, 2 = capitalize.
    -D, --remduplicates    Remove duplicate symbols.
    -E, --remextensions    Remove filetype extensions.
    -I, --ignorecase       Disable case sensitivity.
    -M, --media            Option bundle: All lowercase, remove duplicate symbols,
                           Spaces and dots to underscore, keep extensions...
    -R, --regex            Use regex matching instead of globbing.
    -S, --spacemode        0 = to underscore, 1 = to hyphen, 2 = to dot,
                           3-5 = reversed(0-2), 6 = space and dot to underscore.
    -S, --remsymbols       Remove most symbols and normalize accents.
    -W, --no-wordchars     Remove wordchars
    -v                     Logging verbosity, up to -vvv (debug).
    -q, --quiet            Do not print log messages to console.
    --version              Show the current demimove version.
    -h, --help             Show this help message and exit.

Examples:
    dmv "*.txt" "*.pdf" (will replace all .txt remext with .pdf)
    dmv -f "*" "season-*" (will prepend "season-" to every file in the cwd)
"""
# TODO: Better examples..
import sys

from fileops import FileOps


try:
    from docopt import docopt
except ImportError:
    print "Please install docopt first."
    sys.exit()


def main():
    args = docopt(__doc__, version="0.1")
    fileops = FileOps(quiet=args["--quiet"],
                      dirsonly=args["--dirsonly"],
                      filesonly=args["--filesonly"],
                      simulate=args["--simulate"],
                      interactive=args["--interactive"],
                      noclobber=args["--no-clobber"],
                      remnonwords=args["--no-wordchars"],
                      ignorecase=args["--ignorecase"],
                      recursive=args["--recursive"],
                      keepext=args["--keep-extension"],
                      regex=args["--regex"],
                      hidden=args["--all"],
                      mediamode=args["--media"],
                      remsymbols=args["--remsymbols"],
                      remdups=args["--remduplicates"],
                      remext=args["--remextensions"],
                      exclude=args["--exclude"],
                      spacemode=args["--spacemode"],
                      casemode=args["--casemode"],
                      countpos=args["--count"],
                      verbosity=args["-v"])
    replaces = fileops.get_replaces(args["--path"])
    fileops.get_previews(replaces, args["<match>"], args["<replace>"])


if __name__ == "__main__":
    main()
