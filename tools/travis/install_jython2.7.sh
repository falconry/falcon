#!/usr/bin/env bash

JYTHON_URL="http://search.maven.org/remotecontent?filepath=org/python/jython-installer/2.7.0/jython-installer-2.7.0.jar"
wget $JYTHON_URL -O jython_installer.jar
java -jar jython_installer.jar -s -d $HOME/jython
