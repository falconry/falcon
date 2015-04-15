if [ "$JYTHON" = "true" ]; then
    travis_scripts/install_jython2.7.sh
    $HOME/jython/bin/pip install -r tools/test-requires
else
    pip install tox coveralls --use-mirrors
fi
