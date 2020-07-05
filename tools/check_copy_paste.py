#!/usr/bin/env python

import argparse
import os
import textwrap
import sys

FALCON_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..'))

CODE_DIRECTIVE = '.. code::'
COPY_PASTE_DIRECTIVE = '.. Copy-paste under: '


def extract_files(document):
    with open(document, 'r') as rst:
        lines = rst.readlines()

    files = {}

    filename = None
    source = []
    for line in lines:
        if filename:
            if line.startswith(CODE_DIRECTIVE):
                continue
            if not line.strip():
                if source:
                    source.append('\n')
            elif line.startswith('    '):
                source.append(line)
            else:
                if source:
                    content = ''.join(source)
                    content = textwrap.dedent(content)
                    content = content.rstrip('\n') + '\n'
                    files[filename] = content
                filename = None
                source = []
        elif line.startswith(COPY_PASTE_DIRECTIVE):
            _, _, filename = line.partition(COPY_PASTE_DIRECTIVE)
            filename = filename.strip()

    return files


def main():
    parser = argparse.ArgumentParser(
        description='Check that example files are faithfully copy-pasted '
        'from code snippets inside the docs.')
    parser.add_argument(
        'document', help='Rst document to scan for inline files')

    args = parser.parse_args()

    files = extract_files(args.document)
    offending = []
    for filename, content in files.items():
        path = os.path.join(FALCON_ROOT, filename)
        try:
            with open(path, 'r') as example:
                if example.read() != content:
                    offending.append(filename)
        except (IOError, OSError):
            offending.append(filename)

    if offending:
        sys.stderr.write(
            f'File(s) {", ".join(offending)} differ from {args.document}!\n')
        sys.exit(1)

    if files:
        print(f'All file(s) faithfully match {args.document}:')
        for filename in sorted(files):
            print(f' * {filename}')


if __name__ == '__main__':
    main()
