We strongly recommend that you read the [installation manual](plans/InstallingBasicChecker.pdf) for information on how to install and run these scripts.

Plans describing the various checks and procedures are available as PDF files in the [plans/](plans/) directory. 

Some manual checks are made via a [questionnaire](plans/ImplementorQuestionnaire.pdf).
There's a list of checks still to be added/updated in the 
[ChecksToAdd.md file](ChecksToAdd.md).

Run the automated checks from this directory with e.g.
```
python3.10 control_master.py
```
or, depending on your Python installation, the shorter
```
./control_master.py
```

The "-h" option will display the full set of available options.

The main program is "control_master.py"

Files whose names start with "check_" are the individual section checks.

Files whose names start with "control_" form a basic line-oriented user interface.

All of those can be individually run from the command line.

These checks require Python 3.10 or later.

These checks require the `openlcb` Python module. To simplify installation, version 0.2.0 of that package has been directly included as the `openlcb` directory.

If you want to connect to your OpenLCB network via a serial adapter, you need the `pyserial` module.  If you don't have that already, do

```
python3.10 -m pip install pyserial
```

The CDI and FDI checks require the `xmlschema` module.  If you don't have that already, do

```
python3.10 -m pip install xmlschema
```

The `-v` option requires the `gitpython` module.  If you don't have that already, do

```
python3.10 -m pip install gitpython
```

Output is done via the Python `logging` module.  The scripts are self-configuring. If you want special output formats or locations, configure the logging package before calling the specific checks. See the "Logging" section in the [installation manual](plans/InstallingBasicChecker.pdf).

To configure OlcbChecker for your hardware, you can copy the `defaults.py` file to `localoverrides.py` and edit it with appropriate values.  Alternately you can run the `control_setup.py` script and provide the needed values interactively.
See the [installation manual](plans/InstallingBasicChecker.pdf).
