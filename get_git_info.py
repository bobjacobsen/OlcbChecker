#!/usr/bin/env python3.10

# print the git identification for the current code, if any
import subprocess
import git

import logging

logger = logging.getLogger("OLCBCHECKER")

# first get present SHA
sha = ""
p = subprocess.Popen('git rev-parse HEAD', shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
for line in p.stdout.readlines():
    sha = line.decode()[:20]
retval = p.wait()
if retval != 0 :
    # probably indicates git not present or not a git-controlled directory
    logger.error("Internal error "+str(retval)+", is this a Git checkout?")

else :
    # check for a tag
    tag = ""
    p = subprocess.Popen('git tag --contains '+sha, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in p.stdout.readlines():
        tag = line.decode()[:20]
    retval = p.wait()
    if retval != 0 :
        # unexpected error, sha in wrong format?
        logger.error("Unexpected error "+str(retval)+" retrieving tag for "+sha)
    else :
        # check whether any tracked files are changed
        if tag != "" :
            message = "OlcbChecker Tag: "+tag
        else :
            message = "OlcbChecker Revision: "+sha

        try :
            import gitx
            repo = git.Repo('.')
            diff = repo.git.diff('HEAD')
            if diff :
                message = message + " with additional changes"
        except :
            logger.error("gitpython package not present, can't look for changes in local files")
        logger.info(message)