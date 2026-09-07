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
#
# Specimen generator.  Walks the HCLK_IOI3 tiles the way 039 does, but
# every BUFR that is IN_USE is actually consumed: its output clocks a
# counter on two SLICEs of the same clock region, so the regional clock
# has to cross the HCLK spine into the fabric.  That is what turns the
# HCLK_L enable buffers on.  A share of the BUFRs are fed from the
# region's MMCM instead of from a clock-capable pad, which is what
# exercises the CMT performance-clock path.
#
# FUZZ_MODE:
#   campaign (default)  random mix of unused / pad_clb / mmcm_clb / pad_oddr
#   cal0..cal3          one-hot: only that BUFRCLK index, pad-fed, every tile
#   neg_ioi             cal2 shape but the BUFR is consumed by an IOI ODDR
#   neg_unused          no BUFR at all
#   neg_bufh            BUFHCE into a CLB, no BUFR
#   neg_unconsumed      BUFR placed with its O left open
#   perf0 / perf1       MMCM CLKOUT0 only / CLKOUT1 only, CLB sink
import json
import os
import random
import sys

from prjxray.db import Database
from prjxray import util

REL_Y_TO_BUFRCLK = {0: 2, 1: 3, 2: 0, 3: 1}
BUFRCLK_TO_REL_Y = {v: k for k, v in REL_Y_TO_BUFRCLK.items()}

IOSTANDARD = os.getenv("XRAY_IOSTANDARD", "LVCMOS33")
MODE = os.getenv("FUZZ_MODE", "campaign")


def seed_rng():
    raw = os.getenv("SEED", "0")
    try:
        random.seed(int(raw, 16))
    except ValueError:
        random.seed(int(os.getenv("SEEDN", "1")))


def load_grid():
    db = Database(util.get_db_root(), util.get_part())
    return db.grid()


def mmcm_by_region(grid):
    out = {}
    for tn in grid.tiles():
        gi = grid.gridinfo_at_loc(grid.loc_of_tilename(tn))
        for st, sty in gi.sites.items():
            if sty == "MMCME2_ADV" and gi.clock_region is not None:
                out[str(gi.clock_region)] = (tn, st)
    return out


def slices_by_region(grid):
    out = {}
    for tn in grid.tiles():
        gi = grid.gridinfo_at_loc(grid.loc_of_tilename(tn))
        if gi.clock_region is None:
            continue
        if gi.tile_type not in ("CLBLL_L", "CLBLL_R", "CLBLM_L", "CLBLM_R"):
            continue
        cr = str(gi.clock_region)
        for st, sty in gi.sites.items():
            if sty in ("SLICEL", "SLICEM"):
                out.setdefault(cr, []).append(st)
    for cr in out:
        out[cr].sort()
    return out


def gen_hclk_ioi3(grid):
    """Yield (tile, x_min, y_min, bufr_sites, iob33m, iob33s, region, mmcm_site)."""
    xy_bufr = util.create_xy_fun("BUFR_")
    mmcm = mmcm_by_region(grid)
    for tile_name in sorted(grid.tiles()):
        loc = grid.loc_of_tilename(tile_name)
        gi = grid.gridinfo_at_loc(loc)
        sites = []
        for site, site_type in gi.sites.items():
            if site_type == "BUFR":
                x, y = xy_bufr(site)
                sites.append((site, x, y))
        if not sites:
            continue
        ioi3 = grid.gridinfo_at_loc((loc.grid_x, loc.grid_y - 1))
        if "IOI3" not in ioi3.tile_type:
            continue
        if ioi3.tile_type.startswith("R"):
            dx = 1
        else:
            dx = -1
        iobs_m, iobs_s = [], []
        for dy in (-1, -3, 2, 4):
            iob = grid.gridinfo_at_loc((loc.grid_x + dx, loc.grid_y + dy))
            for site, site_type in iob.sites.items():
                if site_type == "IOB33M":
                    iobs_m.append(site)
                elif site_type == "IOB33S":
                    iobs_s.append(site)
        region = str(gi.clock_region) if gi.clock_region is not None else ""
        mmcm_site = mmcm.get(region, (None, None))[1]
        xs = [s[1] for s in sites]
        ys = [s[2] for s in sites]
        yield (
            tile_name,
            min(xs),
            min(ys),
            sorted(sites, key=lambda t: t[2]),
            sorted(iobs_m),
            sorted(iobs_s),
            region,
            mmcm_site,
        )


def choose_state(rel_y):
    if MODE == "campaign":
        return random.choice(
            ["unused", "unused", "pad_clb", "pad_clb", "pad_clb",
             "mmcm_clb", "mmcm_clb", "pad_oddr"])
    if MODE in ("cal0", "cal1", "cal2", "cal3"):
        want = int(MODE[-1])
        return "pad_clb" if REL_Y_TO_BUFRCLK[rel_y] == want else "unused"
    if MODE == "neg_ioi":
        return "pad_oddr" if rel_y == 0 else "unused"
    if MODE == "neg_unused":
        return "unused"
    if MODE == "neg_bufh":
        return "unused"
    if MODE == "neg_unconsumed":
        return "pad_open" if rel_y == 0 else "unused"
    if MODE in ("perf0", "perf1"):
        return "mmcm_clb" if rel_y == 0 else "unused"
    raise SystemExit("unknown FUZZ_MODE={}".format(MODE))


def ibuf_block(site, idx, ioclk):
    return """
    wire {ioclk};
    (* KEEP, DONT_TOUCH, LOC="{site}" *)
    IBUF #(.IOSTANDARD("{iost}")) ibuf_{idx} (
        .I(clks[{idx}]),
        .O({ioclk})
    );
""".format(ioclk=ioclk, site=site, idx=idx, iost=IOSTANDARD)


def mmcm_block(name, clkin, site):
    return """
    wire {n}_fb, {n}_out0, {n}_out1, {n}_out2, {n}_out3;
    (* KEEP, DONT_TOUCH, LOC="{site}" *)
    MMCME2_BASE #(
        .CLKIN1_PERIOD(10.0), .CLKFBOUT_MULT_F(8.0), .DIVCLK_DIVIDE(1),
        .CLKOUT0_DIVIDE_F(8.0), .CLKOUT1_DIVIDE(8),
        .CLKOUT2_DIVIDE(8), .CLKOUT3_DIVIDE(8)
    ) {n} (
        .CLKIN1({clkin}), .CLKFBIN({n}_fb), .CLKFBOUT({n}_fb),
        .CLKOUT0({n}_out0), .CLKOUT1({n}_out1),
        .CLKOUT2({n}_out2), .CLKOUT3({n}_out3),
        .RST(1'b0), .PWRDWN(1'b0)
    );
""".format(n=name, clkin=clkin, site=site)


def bufr_block(site, src, consume, oddr_site=None, out_idx=0):
    head = """
    wire {site}_o;
    (* KEEP, DONT_TOUCH, LOC="{site}" *)
    BUFR #(.BUFR_DIVIDE("BYPASS")) buf_{site} (
        .CE(1'b1), .CLR(1'b0), .I({src}), .O({site}_o)
    );
""".format(site=site, src=src)
    if consume == "clb":
        return head  # flops added by the caller from the wire
    if consume == "oddr" and oddr_site is not None:
        return head + """
    wire {site}_q;
    (* KEEP, DONT_TOUCH *)
    ODDR #(.DDR_CLK_EDGE("SAME_EDGE")) oddr_{site} (
        .C({site}_o), .CE(1'b1), .D1(1'b1), .D2(1'b0),
        .R(1'b0), .S(1'b0), .Q({site}_q)
    );
    (* KEEP, DONT_TOUCH, LOC="{obuf}" *)
    OBUF #(.IOSTANDARD("LVCMOS33")) obuf_{site} (.I({site}_q), .O(outs[{idx}]));
""".format(site=site, obuf=oddr_site, idx=out_idx)
    # unconsumed: still drive O so the primitive exists, but no sink
    return """
    (* KEEP, DONT_TOUCH, LOC="{site}" *)
    BUFR #(.BUFR_DIVIDE("BYPASS")) buf_{site} (
        .CE(1'b1), .CLR(1'b0), .I({src})
    );
""".format(site=site, src=src)


def counter_block(clk, slices, tag):
    """8 FDRE on two SLICEs, clocked by clk."""
    if len(slices) < 2:
        return ""
    s0, s1 = slices[0], slices[1]
    lines = ["    wire [7:0] q_{t};".format(t=tag)]
    d_expr = [
        "~q_{t}[0]".format(t=tag),
        "q_{t}[1] ^ q_{t}[0]".format(t=tag),
        "q_{t}[2] ^ (q_{t}[1] & q_{t}[0])".format(t=tag),
        "q_{t}[3] ^ (q_{t}[2] & q_{t}[1] & q_{t}[0])".format(t=tag),
        "q_{t}[4] ^ (q_{t}[3] & q_{t}[2] & q_{t}[1] & q_{t}[0])".format(t=tag),
        "q_{t}[5] ^ (q_{t}[4] & q_{t}[3] & q_{t}[2] & q_{t}[1] & q_{t}[0])".format(t=tag),
        "q_{t}[6] ^ (q_{t}[5] & q_{t}[4] & q_{t}[3] & q_{t}[2] & q_{t}[1] & q_{t}[0])".format(t=tag),
        "q_{t}[7] ^ (q_{t}[6] & q_{t}[5] & q_{t}[4] & q_{t}[3] & q_{t}[2] & q_{t}[1] & q_{t}[0])".format(t=tag),
    ]
    bels = ["AFF", "BFF", "CFF", "DFF"]
    for i in range(8):
        sl = s0 if i < 4 else s1
        bel = bels[i % 4]
        lines.append("""
    (* KEEP, DONT_TOUCH, LOC="{sl}", BEL="{bel}" *)
    FDRE #(.INIT(1'b0)) ff_{t}_{i} (
        .C({clk}), .CE(1'b1), .R(1'b0), .D({d}), .Q(q_{t}[{i}])
    );""".format(sl=sl, bel=bel, t=tag, i=i, clk=clk, d=d_expr[i]))
    return "\n".join(lines)


def bufh_block(clkin, slice_site):
    return """
    wire bufh_o;
    wire ff_bufh_q;
    (* KEEP, DONT_TOUCH *)
    BUFHCE bufh_i (.I({clkin}), .CE(1'b1), .O(bufh_o));
    (* KEEP, DONT_TOUCH, LOC="{sl}", BEL="AFF" *)
    FDRE #(.INIT(1'b0)) ff_bufh (
        .C(bufh_o), .CE(1'b1), .R(1'b0), .D(~ff_bufh_q), .Q(ff_bufh_q)
    );
""".format(clkin=clkin, sl=slice_site)


def main():
    seed_rng()
    grid = load_grid()
    slices = slices_by_region(grid)

    params = []
    outputs = []
    num_clocks = 0
    num_outs = 0
    slice_cursor = {cr: 0 for cr in slices}

    def take_slices(cr, n=2):
        pool = slices.get(cr, [])
        i = slice_cursor.get(cr, 0)
        got = pool[i:i + n]
        slice_cursor[cr] = i + n
        return got

    tiles = list(gen_hclk_ioi3(grid))
    if not tiles:
        sys.stderr.write("no HCLK_IOI3 tiles\n")
        sys.exit(1)

    for tile, x_min, y_min, bufr_sites, iobs_m, iobs_s, region, mmcm_site in tiles:
        ioclks = []
        for iob in iobs_m:
            ioclk = "clk_{}".format(iob.replace("/", "_"))
            ioclks.append(ioclk)
            outputs.append(ibuf_block(iob, num_clocks, ioclk))
            num_clocks += 1
        if not ioclks:
            continue

        mmcm_name = "mmcm_{}".format(tile.replace("/", "_"))
        mmcm_declared = False
        clkout_for_mode = 0 if MODE != "perf1" else 1

        for site, x, y in bufr_sites:
            rel_y = y - y_min
            state = choose_state(rel_y)
            rec = {
                "tile": tile,
                "site": site,
                "rel_y": rel_y,
                "bufrclk": REL_Y_TO_BUFRCLK.get(rel_y),
                "region": region,
                "state": state,
                "IN_USE": 0 if state == "unused" else 1,
            }
            if state == "unused":
                params.append(rec)
                continue

            src = ioclks[rel_y % len(ioclks)]
            if state.startswith("mmcm"):
                if mmcm_site is None:
                    state = "pad_clb"
                    rec["state"] = state
                else:
                    if not mmcm_declared:
                        outputs.append(mmcm_block(mmcm_name, ioclks[0], mmcm_site))
                        mmcm_declared = True
                    if MODE in ("perf0", "perf1"):
                        src = "{}_out{}".format(mmcm_name, clkout_for_mode)
                    else:
                        src = "{}_out{}".format(mmcm_name, rel_y % 4)
                    rec["source"] = "mmcm"
            else:
                rec["source"] = "pad"

            if state in ("pad_clb", "mmcm_clb"):
                rec["sink"] = "clb"
                outputs.append(bufr_block(site, src, "clb"))
                sl = take_slices(region, 2)
                outputs.append(counter_block("{}_o".format(site), sl, site.replace("/", "_")))
            elif state == "pad_oddr":
                rec["sink"] = "oddr"
                if not iobs_s:
                    sys.stderr.write(
                        "no IOB33S for ODDR on {}, leaving O open\n"
                        .format(tile))
                    rec["sink"] = "open"
                    rec["oddr_skipped"] = 1
                    outputs.append(bufr_block(site, src, "open"))
                else:
                    ob = iobs_s[num_outs % len(iobs_s)]
                    outputs.append(bufr_block(site, src, "oddr", ob, num_outs))
                    num_outs += 1
            elif state == "pad_open":
                rec["sink"] = "open"
                outputs.append(bufr_block(site, src, "open"))
            params.append(rec)

        if MODE == "neg_bufh" and tile == tiles[0][0]:
            sl = take_slices(region, 1)
            if sl:
                outputs.append(bufh_block(ioclks[0], sl[0]))
                params.append({
                    "tile": tile,
                    "kind": "BUFH",
                    "region": region,
                    "IN_USE": 1,
                })

    nclk = max(num_clocks - 1, 0)
    nout = max(num_outs - 1, 0)
    # Do not emit an undriven `outs` port: Vivado then tries to place it
    # and IO placer dies (`Place 30-58`, 1 unplaced port, 0 pins).
    # Hits every cal* / neg_unconsumed / neg_unused / neg_bufh specimen.
    if num_outs == 0:
        print("module top(input [{}:0] clks);".format(nclk))
    else:
        print("module top(input [{}:0] clks, output [{}:0] outs);".format(nclk, nout))
    print("    (* KEEP, DONT_TOUCH *) LUT6 dummy ();")
    for block in outputs:
        print(block)
    print("endmodule")

    with open("params.json", "w") as f:
        json.dump(params, f, indent=2)
    sys.stderr.write("MODE={} clocks={} bufr_used={}\n".format(
        MODE, num_clocks, sum(1 for p in params if p.get("IN_USE"))))


if __name__ == "__main__":
    main()
