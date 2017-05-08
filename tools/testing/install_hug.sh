#!/usr/bin/env bash

HUG_PATH=.ecosystem/hug

# Clean up in case we are running locally and not in travis
rm -rf $HUG_PATH

mkdir -p .ecosystem
git clone https://github.com/timothycrosley/hug.git $HUG_PATH
virtualenv $HUG_PATH/.venv
source $HUG_PATH/.venv/bin/activate

pip install hug

pushd $HUG_PATH
git checkout master
git pull
HUG_VERSION=$(pip freeze | grep hug | cut -c 6-)
git checkout tags/$HUG_VERSION
pip install -rrequirements/build.txt
popd

pip install .  # Override Hug's Falcon version with the one under test
