Run these from this directory with e.g.
```
python3.10 control_master.py
```
The "-h" option will display the full set of available options.

The main program is "control_master.py"

Files whose names start with "check_" are the individual section checks.

Files whose names start with "control_" form a basic line-oriented user interface.

All of those can be individually run from the command line.

Plans describing the various checks and procedures are available as PDF files in the [plans/](plans/) directory.

An installation document is available as [plans/InstallingBasicChecker.pdf](plans/InstallingBasicChecker.pdf)

These checks require the `openlcb`. That's not yet available via PIP, though eventually it will be.  To get it now, you have to obtain a copy from GitHub.  See the [installation document] for more detail, but briefly you can:

```
cd (somewhere)
git clone https://github.com/bobjacobsen/PythonOlcbNode.git
cd PythonOlcbNode
export PYTHONPATH=$PWD
cd (where you put OlcbChecker)
```
The `export PYTHONPATH=$PWD` from the directory needs to be done each time you open a new window, or you can put the equivalent in your shell setup files.  Someday, there will be a `python3.10 -m pip install --editable openlcb` command to do this.

The CDI check requires the `xmlschema` moddule.  If you don't have that already, so
```
python3 -m pip install xmlschema
```
