from os.path import dirname, join

try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup


def read(filename):
    with open(join(dirname(__file__), filename)) as f:
        return f.read()


_name = "demimove"
_license = "MIT"


setup(
    name=_name,
    description="A filebrowser for mass renaming.",
    long_description=read("README.md"),
    version="0.1",
    license=_license,
    url="https://github.com/mikar/{}".format(_name),
    author="Max Demian",
    author_email="mikar@gmx.de",
    packages=[_name, _name + "/data"],
    package_data={_name: ["icon.png", "history.txt", "demimove.ini", "gui.ui"]},
    install_package_data=True,
    entry_points={
                  "console_scripts": [
                      "{0} = {0}.{0}:main".format(_name),
                      "{0}-dbus = {0}.{0}dbus:main".format(_name),
                  ],
                  "gui_scripts": [
                      "{0}-ui = {0}.{0}ui:main".format(_name),
                  ],
              }
)
