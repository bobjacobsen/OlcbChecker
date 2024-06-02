'''
Initial configuration for a compatibility check.

This runs at the start of each check to 
load configuration values into the "default"
space.  E.g. 'default.portname' will give
the portname being used now.

'''

import os

# First get the defaults.py file,
try:
    import defaults
except:
    print ("defaults.py not found, ending")
    quit(3)


class TestConfiguration:
    _hostname = defaults.hostname
    _portnumber = defaults.portnumber
    _devicename = defaults.devicename
    _targetnodeid = defaults.targetnodeid
    _ownnodeid = defaults.ownnodeid
    _checkpip = defaults.checkpip
    _trace = defaults.trace
    _skip_interactive = defaults.skip_interactive
    _tests = []

    @property
    def hostname(self):
        return self._hostname

    @hostname.setter
    def hostname(self, value):
        self._hostname = value

    @property
    def trace(self):
        return self._trace

    @trace.setter
    def trace(self, value):
        self._trace = value

    @property
    def devicename(self):
        return self._devicename

    @devicename.setter
    def devicename(self, name):
        self._devicename = name

    @property
    def portnumber(self):
        return self._portnumber

    @portnumber.setter
    def portnumber(self, value):
        self._portnumber = value

    @property
    def ownnodeid(self):
        return self._ownnodeid

    @ownnodeid.setter
    def ownnodeid(self, value):
        self._ownnodeid = value

    @property
    def targetnodeid(self):
        return self._targetnodeid

    @targetnodeid.setter
    def targetnodeid(self, value):
        self._targetnodeid = value

    @property
    def skip_interactive(self):
        return self._skip_interactive

    @skip_interactive.setter
    def skip_interactive(self, value):
        self._skip_interactive = value

    @property
    def checkpip(self):
        return self._checkpip

    @checkpip.setter
    def checkpip(self, value):
        self._checkpip = value

    @property
    def tests(self):
        return self._tests

    def set_config(self, values : dict):
        if 'hostname' in values:
            self.hostname = values['hostname']
        if 'portnumber' in values:
            self._portnumber = int(values['portnumber'])
        if 'devicename' in values:
            self._devicename = values['devicename']
        if 'targetnodeid' in values:
            self._targetnodeid = values['targetnodeid']
        if 'skip-interactive' in values:
            val = values['skip-interactive']
            if val == 'False':
                self._skip_interactive = False
            elif val == 'True':
                self._skip_interactive = True
        if 'check-pip' in values:
            val = values['check-pip']
            if val == 'False':
                self._checkpip = False
            elif val == 'True':
                self._checkpip = True
        if 'tests' in values:
            val = values['tests']
            for test_name in val.split(','):
                self._tests.append(test_name)



# Global configuration variable
# It's not the prettiest solution, but it does work...
global_config = TestConfiguration()
