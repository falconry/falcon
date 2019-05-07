#!/bin/bash
rm -rf dash

# Generate Dash Docs
doc2dash \
    -n Falcon \
    -f -j \
    -d dash \
    -I api/index.html \
    -i logo/favicon-32x32.png \
    docs/_build/html

# Create Dash Archive
tar \
    --exclude='.DS_Store' \
    -C dash/ \
    -cz \
    -f dash/Falcon.tgz \
    Falcon.docset/
