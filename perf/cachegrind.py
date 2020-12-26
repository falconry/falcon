"""
As per the original author's recommendation, this script was simply copied from
https://github.com/pythonspeed/cachegrind-benchmarking @ 32d26691.

See also this awesome article by Itamar Turner-Trauring:
https://pythonspeed.com/articles/consistent-benchmarking-in-ci/.

The original file content follows below.

-------------------------------------------------------------------------------

Proof-of-concept: run_with_cachegrind a program under Cachegrind, combining all the various
metrics into one single performance metric.

Requires Python 3.

License: https://opensource.org/licenses/MIT

## Features

* Disables ASLR.
* Sets consistent cache sizes.
* Calculates a combined performance metric.

For more information see the detailed write up at:

https://pythonspeed.com/articles/consistent-benchmarking-in-ci/

## Usage

This script has no compatibility guarnatees, I recommend copying it into your
repository.  To use:

$ python3 cachegrind.py ./yourprogram --yourparam=yourvalues

If you're benchmarking Python, make sure to set PYTHONHASHSEED to a fixed value
(e.g. `export PYTHONHASHSEED=1234`).  Other languages may have similar
requirements to reduce variability.

The last line printed will be a combined performance metric, but you can tweak
the script to extract more info, or use it as a library.

Copyright © 2020, Hyphenated Enterprises LLC.
"""

from typing import List, Dict
from subprocess import check_call, check_output
import sys
from tempfile import NamedTemporaryFile

ARCH = check_output(["uname", "-m"]).strip()


def run_with_cachegrind(args_list: List[str]) -> Dict[str, int]:
    """
    Run the the given program and arguments under Cachegrind, parse the
    Cachegrind specs.

    For now we just ignore program output, and in general this is not robust.
    """
    temp_file = NamedTemporaryFile("r+")
    check_call([
        # Disable ASLR:
        "setarch",
        ARCH,
        "-R",
        "valgrind",
        "--tool=cachegrind",
        # Set some reasonable L1 and LL values, based on Haswell. You can set
        # your own, important part is that they are consistent across runs,
        # instead of the default of copying from the current machine.
        "--I1=32768,8,64",
        "--D1=32768,8,64",
        "--LL=8388608,16,64",
        "--cachegrind-out-file=" + temp_file.name,
    ] + args_list)
    return parse_cachegrind_output(temp_file)


def parse_cachegrind_output(temp_file):
    # Parse the output file:
    lines = iter(temp_file)
    for line in lines:
        if line.startswith("events: "):
            header = line[len("events: "):].strip()
            break
    for line in lines:
        last_line = line
    assert last_line.startswith("summary: ")
    last_line = last_line[len("summary:"):].strip()
    return dict(zip(header.split(), [int(i) for i in last_line.split()]))


def get_counts(cg_results: Dict[str, int]) -> Dict[str, int]:
    """
    Given the result of run_with_cachegrind(), figure out the parameters we will use for final
    estimate.

    We pretend there's no L2 since Cachegrind doesn't currently support it.

    Caveats: we're not including time to process instructions, only time to
    access instruction cache(s), so we're assuming time to fetch and run_with_cachegrind
    instruction is the same as time to retrieve data if they're both to L1
    cache.
    """
    result = {}
    d = cg_results

    ram_hits = d["DLmr"] + d["DLmw"] + d["ILmr"]

    l3_hits = d["I1mr"] + d["D1mw"] + d["D1mr"] - ram_hits

    total_memory_rw = d["Ir"] + d["Dr"] + d["Dw"]
    l1_hits = total_memory_rw - l3_hits - ram_hits
    assert total_memory_rw == l1_hits + l3_hits + ram_hits

    result["l1"] = l1_hits
    result["l3"] = l3_hits
    result["ram"] = ram_hits

    return result


def combined_instruction_estimate(counts: Dict[str, int]) -> int:
    """
    Given the result of run_with_cachegrind(), return estimate of total time to run_with_cachegrind.

    Multipliers were determined empirically, but some research suggests they're
    a reasonable approximation for cache time ratios.  L3 is probably too low,
    but then we're not simulating L2...
    """
    return counts["l1"] + (5 * counts["l3"]) + (35 * counts["ram"])


if __name__ == "__main__":
    print(combined_instruction_estimate(get_counts(run_with_cachegrind(sys.argv[1:]))))
