if [ "$JYTHON" = "true" ]; then
    $HOME/jython/bin/nosetests
else
    tox -e $TOX_ENV
fi
