import sys


def get_work_factor():
    if len(sys.argv) != 2:
        sys.stderr.write(f'{sys.argv[0]}: expected a single int argument.\n')
        sys.exit(2)

    try:
        return int(sys.argv[1])
    except ValueError:
        sys.stderr.write(f'{sys.argv[0]}: expected a single int argument.\n')
        sys.exit(2)
