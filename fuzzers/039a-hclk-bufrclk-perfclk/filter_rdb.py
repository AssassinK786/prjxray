#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# Copyright (C) 2017-2020  The Project X-Ray Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC
"""Split a raw segmatch .rdb into what may be published and what may not.

Three outputs, so that nothing silently reaches the database:

  segbits  rows that resolved to real bits.
  ppips    pips the specimens do route and for which segmatch found zero
           candidate bits, written as `default` pseudo-pips (the
           all-zero mux position, the convention INT_L.BYP_ALT* uses).
           The tag is rewritten to the tile type taken from the output
           file name, because mergedb has no pseudo-pip mode and these
           are applied to the database by hand after review.
  notes    every line that was refused, and why.

Two candidate bits are stripped by name because they belong to rows this
database already carries, and a correlation with an existing row is not a
new row:

  05_21   HCLK_L.HCLK_LEAF_CLK_B_BOTL5.HCLK_CK_BUFRCLK3
  29_937  CMT_TOP_*_LOWER_B.MMCME2_ADV.CLKOUT1_CLKOUT1_OUTPUT_ENABLE[0]

A `<const0>` tag was never 1 in the population: it is reported, never
published.  A row left with no bits after stripping is dropped too.
"""

import os
import re
import sys

BIT_RE = re.compile(r"!?[0-9]+_[0-9]+$")

# Bits that already belong to a row of the seed database, per tag suffix.
KNOWN_COLLISIONS = (
    ("ENABLE_BUFFER.HCLK_CK_BUFRCLK3", "05_21"),
    ("CLK_PERF3", "29_937"),
)


def tile_prefix_from(ppips_path):
    """ppips_cmt_top_r_lower_b.db -> CMT_TOP_R_LOWER_B."""
    base = os.path.basename(ppips_path)
    assert base.startswith("ppips_") and base.endswith(".db"), base
    return base[len("ppips_"):-len(".db")].upper() + "."


def collisions_for(tag):
    out = set()
    for needle, bit in KNOWN_COLLISIONS:
        if needle in tag:
            out.add(bit)
    return out


def main():
    fn_in, fn_segbits, fn_ppips, fn_notes = sys.argv[1:5]
    prefix = tile_prefix_from(fn_ppips)

    segbits, ppips, notes = [], [], []
    with open(fn_in) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            tag, rest = line.split(None, 1) if " " in line else (line, "")

            drop = collisions_for(tag)
            if drop:
                bits = rest.split()
                kept = [b for b in bits if b not in drop]
                gone = [b for b in bits if b in drop]
                if gone:
                    notes.append(
                        "stripped {} from {} -> {}".format(
                            " ".join(gone), tag, " ".join(kept) or "(empty)"))
                rest = " ".join(kept)

            if rest.startswith("<const0>"):
                notes.append("drop, never routed in the population: " + tag)
                continue
            if rest.startswith("<0 candidates>"):
                ppips.append(
                    "{} default".format(prefix + tag.split(".", 1)[1]))
                notes.append("routed with zero candidate bits: " + tag)
                continue
            if rest.startswith("<"):
                notes.append("drop, unresolved {}: {}".format(rest, tag))
                continue
            if not rest:
                notes.append("drop, no bit left: " + tag)
                continue
            if not all(BIT_RE.match(b) for b in rest.split()):
                notes.append("drop, not a bit list: " + line)
                continue
            segbits.append("{} {}".format(tag, rest))

    for path, lines in ((fn_segbits, segbits), (fn_ppips, ppips),
                        (fn_notes, notes)):
        with open(path, "w") as f:
            for l in lines:
                f.write(l + "\n")

    print(
        "{}: segbits={} ppips={} refused={}".format(
            os.path.basename(fn_in), len(segbits), len(ppips), len(notes)),
        file=sys.stderr)
    for n in notes:
        print("  " + n, file=sys.stderr)


if __name__ == "__main__":
    main()
