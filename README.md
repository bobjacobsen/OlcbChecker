Run these from this directory with e.g.
```
python3.10 control_master.py
```
or, depending on your Python installation, the shorter
```
./control_master.py
```

The "-h" option will display the full set of available options.

The main program is "control_master.py"

Plans describing the various checks and procedures are available as PDF files in the [plans/](plans/) directory.

Files whose names start with "check_" are the individual section checks.

Files whose names start with "control_" form a basic line-oriented user interface.

All of those can be individually run from the command line.

An installation document is available as [plans/InstallingBasicChecker.pdf](plans/InstallingBasicChecker.pdf)

These checks require Python 3.10 or later.

These checks require the `openlcb` Python module. That's not yet available via PIP, though eventually it will be.  To get it now, you have to obtain a copy from GitHub.  See the [installation document](plans/InstallingBasicChecker.pdf) for more detail, but briefly you can:

```
cd (somewhere)
git clone https://github.com/bobjacobsen/python-openlcb.git
python3.10 -m pip install --editable python-openlcb
cd (where you put OlcbChecker)
```

The CDI check requires the `xmlschema` module.  If you don't have that already, do

```
python3 -m pip install xmlschema
```

Output is done via the Python `logging` module.  The scripts are self-configuring. If you want special output formats or locations, configure the logging package before calling the specific tests.
