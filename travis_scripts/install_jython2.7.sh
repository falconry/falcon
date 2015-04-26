JYTHON_URL="http://search.maven.org/remotecontent?filepath=org/python/jython-installer/2.7-rc2/jython-installer-2.7-rc2.jar"
wget $JYTHON_URL -O jython_installer.jar
java -jar jython_installer.jar -s -d $HOME/jython
