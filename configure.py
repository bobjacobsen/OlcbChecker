'''
Initial configuration for a compatibility check.

This runs at the start of each check to 
load configuration values into the "default"
space.  E.g. 'default.portname' will give
the portname being used now.

The sequence of operations is:
    read from the `defaults.py` file
    read from the `localoverrides.py` file
    process the command line arguments

'''

import os
import logging

def options() :
    print ("")
    #   TODO finish this up
    print ("Available options are:")
    print ("")
    print ("-h, --help print this message and quit")
    print ("-v, --version print version information and continue")
    print ("-a, --address followed by a host[:port] IP address for GridConnect access.")
    print ("                This is mutually exclusive with the -d --device option")
    print ("-d, --device followed by a serial port device name.")
    print ("                This is mutually exclusive with the -h --hostname option")
    print ("-t, --targetnode followed by a nodeID for the device being checked in 01.23.45.67.89.0A form")
    print ("-r, --run run the checks instead of presenting a menu")
    print ("")
    print ("Less frequently needed:")
    print ("")
    print ("-T, --trace followed by an integer trace level.  Higher numbers are more informatiom.")
    print ("                0 is just error messages, 10 includes success messages, 20 includes message traces, ")
    print ("                30 includes frame traces, 40 includes physical layer traces, 50 includes internal code traces")
    print ("-o, --ownnode followed by a nodeID for the checking device in 01.23.45.67.89.0A form")
    print ("-p do not check results against PIP bits")
    print ("-P do check results against PIP bits")
    print ("-I execute interactive checks")
    print ("-i skip interactive checks")
    print ("")

# To start option configuration, get the defaults.py file,
try:
    import defaults
except:
    print ("defaults.py not found, ending")
    quit(3)

#   TODO: Make the following into a loop over dir(defaults)
hostname = defaults.hostname
portnumber = defaults.portnumber
devicename = defaults.devicename
targetnodeid = defaults.targetnodeid
ownnodeid = defaults.ownnodeid
checkpip = defaults.checkpip
trace = defaults.trace
skip_interactive = defaults.skip_interactive

# Next override with local definitions.
if os.path.isfile("./localoverrides.py") :
    try:
        import localoverrides
        
        #   TODO: Make the following into a loop over dir(localoverrides)
        if 'hostname' in dir(localoverrides) :      hostname = localoverrides.hostname
        if 'portnumber' in dir(localoverrides) :    portnumber = localoverrides.portnumber
        if 'devicename' in dir(localoverrides) :    devicename = localoverrides.devicename
        if 'targetnodeid' in dir(localoverrides) :  targetnodeid = localoverrides.targetnodeid
        if 'ownnodeid' in dir(localoverrides) :     ownnodeid = localoverrides.ownnodeid
        if 'checkpip' in dir(localoverrides) :      checkpip = localoverrides.checkpip
        if 'trace' in dir(localoverrides) :         trace = localoverrides.trace
        if 'skip_interactive' in dir(localoverrides) : skip_interactive = localoverrides.skip_interactive

    except:
        pass  # no local overrides is a normal condition

# Next process command line options

import getopt, sys

runimmediate = False

try:
    opts, remainder = getopt.getopt(sys.argv[1:], "d:n:o:t:T:a:pPhiIrv", ["host=", "device=", "ownnode=", "targetnode=", "trace=", "help", "version"])
except getopt.GetoptError as err:
    # print help information and exit:
    print (str(err)) # will print something like "option -a not recognized"
    options()
    sys.exit(2)
hostpresent = False
devicepresent = False
for opt, arg in opts:
    if opt in ("-h", "--help"):
        options()
        sys.exit(0)
    elif opt in ("-v", "--version"):
        import get_git_info
        # runs when imported
    elif opt == "-p":
        checkpip = False
    elif opt == "-P":
        checkpip = True
    elif opt == "-i":
        skip_interactive = True
    elif opt == "-I":
        skip_interactive = False
    elif opt in ("-t", "--targetnode"):
        targetnodeid = arg
    elif opt in ("-d", "--device"):
        hostname = None # only one
        devicepresent = True
        if hostpresent :
            print ("You can only specify the host address or the device name, not both")
            options()
            sys.exit(2)
        devicename = arg
    elif opt in ("-o", "--ownnode"):
        ownnodeid = arg
    elif opt in ("-T", "--trace"):
        trace = int(arg)
    elif opt in ("-r", "--run"):
        runimmediate = True
    elif opt in ("-a", "--address"):
        devicename = None # only one
        hostname = arg
        hostpresent = True
        if devicepresent :
            print ("You can only specify the host address or the device name, not both")
            options()
            sys.exit(2)
        parts = arg.split(":")
        if len(parts) == 2:
            hostname = parts[0]
            try:
                portnumber = int(parts[1])
            except ValueError:
                usage()
                print("Error: Port {} is not an integer.".format(parts[1]),
                      file=sys.stderr)
                options()
                sys.exit(2)
        elif len(parts) > 2:
            print("Error: Too many colons in hostname argument",
                      file=sys.stderr)
            options()
            sys.exit(2)

# configure logging based on trace level:  This is temporary
logger = logging.getLogger('root')  # Root Logger

match (trace) :
    case 0:
        logger.setLevel(logging.WARN)
    case 10: 
        logger.setLevel(logging.INFO)
    case _:
        logger.setLevel(logging.DEBUG)

import builtins

# check that a connection has been configured unless told not to
print("in configure")
print(devicename)
print(hostname)
print(targetnodeid)
print(hasattr(builtins, "olcbchecker_bypass_a_or_d_check"))

if (not hasattr(builtins, "olcbchecker_bypass_a_or_d_check")) or not builtins.olcbchecker_bypass_a_or_d_check:
    # in this case, the  bypass_a_or_d_check hasn't been set or is False
    if devicename is None and hostname is None :
        print ("Either the host address or the device name must be specified")
        options()
        sys.exit(2)
    if devicename is not None and hostname is not None :
        print ("You can only specify the host address or the device name, not both")
        
#  check that a target node is configured
if (not hasattr(builtins, "olcbchecker_bypass_a_or_d_check")) or not builtins.olcbchecker_bypass_a_or_d_check:
    if not targetnodeid :
        print ("A target node ID must be configured. See the -t option or targetnodeid symbol value")
        options()
        sys.exit(2)
