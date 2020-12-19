"""
As per the original author's recommendation, this script was simply copied from
https://github.com/pythonspeed/cachegrind-benchmarking @ b9dabb6c.

See also this awesome article by Itamar Turner-Trauring:
https://pythonspeed.com/articles/consistent-benchmarking-in-ci/.

The original file content follows below.

-------------------------------------------------------------------------------

Proof-of-concept: run a program under Cachegrind, combining all the various
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
repository. To use:

$ python3 cachegrind.py ./yourprogram --yourparam=yourvalues

The last line printed will be a combined performance metric.


Copyright © 2020, Hyphenated Enterprises LLC.
"""

from typing import List, Dict
from subprocess import check_output, PIPE, Popen
import re
import sys

ARCH = check_output(["uname", "-m"]).strip()


def _run(args_list: List[str]) -> Dict[str, int]:
    """
    Run the the given program and arguments under Cachegrind, parse the
    Cachegrind specs.

    For now we just ignore program output, and in general this is not robust.
    """
    complete_args = [
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
    ] + args_list
    popen = Popen(complete_args, stderr=PIPE, universal_newlines=True)
    stderr = popen.stderr.read()
    popen.wait()

    # Discovered afterwards we can parse the cachegrind.out.<pid> file's last
    # line. Oh well, maybe in rewrite.
    result = {}
    for line in stderr.splitlines():
        if re.match("^==[0-9]*== ", line):
            match = re.match("^==[0-9]*== ([ILD][A-Za-z0-9 ]*):  *([0-9,]*)", line)
            if match:
                name, value = match.groups()
                # Drop extra spaces:
                name = " ".join(name.split())
                # Convert "123,456" into integer:
                value = int(value.replace(",", ""))
                result[name] = value
        sys.stderr.write(line + "\n")
    return result


def get_counts(cg_results: Dict[str, int]) -> Dict[str, int]:
    """
    Given the result of _run(), figure out the parameters we will use for final
    estimate.

    We pretend there's no L2 since Cachegrind doesn't currently support it.

    Caveats: we're not including time to process instructions, only time to
    access instruction cache(s), so we're assuming time to fetch and run
    instruction is the same as time to retrieve data if they're both to L1
    cache.
    """
    result = {}

    ram_hits = cg_results["LL misses"]
    assert ram_hits == cg_results["LLi misses"] + cg_results["LLd misses"]

    l3_hits = cg_results["LL refs"]
    assert l3_hits == cg_results["I1 misses"] + cg_results["D1 misses"]

    total_memory_rw = cg_results["I refs"] + cg_results["D refs"]
    l1_hits = total_memory_rw - l3_hits - ram_hits

    result["l1"] = l1_hits
    result["l3"] = l3_hits
    result["ram"] = ram_hits
    return result


def combined_instruction_estimate(counts: Dict[str, int]) -> int:
    """
    Given the result of _run(), return estimate of total time to run.

    Multipliers were determined empirically, but some research suggests they're
    a reasonable approximation for cache time ratios.
    """
    return counts["l1"] + (5 * counts["l3"]) + (30 * counts["ram"])


if __name__ == "__main__":
    print(combined_instruction_estimate(get_counts(_run(sys.argv[1:]))))
