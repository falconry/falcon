DIST_DIR=./dist

read -p "Sign and upload $DIST_DIR/* to PyPI? [y/N]: " CONTINUE

if [[ $CONTINUE =~ ^[Yy]$ ]]; then
    pip install -U twine
    twine upload -s --skip-existing $DIST_DIR/*
fi
