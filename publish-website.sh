#!/usr/bin/env bash

if git checkout gh-pages
then
    rm -rf css
    rm -rf img
    rm -rf js
    cp -r ../falconframework.org/* .

    mv compressed/* ./
    rm compressed

    mv css/compressed/* css/
    rm css/compressed

    git add *
    git commit -m 'doc: Publish website'
    git push origin gh-pages
    git checkout master
fi
