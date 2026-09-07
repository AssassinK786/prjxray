# Copyright (C) 2017-2020  The Project X-Ray Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC
#
# 039's bitstream path plus a dump of the used pips of the HCLK and CMT
# tiles the rows live on.  The tags are read from those pips, not from
# the placed primitives, so the dump is part of the measurement.
proc dump_used_clock_pips {filename} {
    set fp [open $filename w]
    set nets [get_nets -quiet -hierarchical]
    foreach net $nets {
        foreach pip [get_pips -quiet -of_objects $net] {
            if {[regexp {HCLK_L_|HCLK_R_|HCLK_CMT|CMT_TOP_.*LOWER_B} $pip]} {
                puts $fp "$pip"
            }
        }
    }
    close $fp
}

proc dump_sites {filename filter} {
    set fp [open $filename w]
    foreach c [get_cells -quiet -hierarchical -filter $filter] {
        puts $fp "[get_property NAME $c] [get_sites -quiet -of_objects $c]"
    }
    close $fp
}

proc run {} {
    create_project -force -part $::env(XRAY_PART) design design
    read_verilog top.v
    synth_design -top top

    set_property CFGBVS VCCO [current_design]
    set_property CONFIG_VOLTAGE 3.3 [current_design]
    set_property BITSTREAM.GENERAL.PERFRAMECRC YES [current_design]

    place_design
    route_design

    dump_sites bufr_sites.txt {REF_NAME == BUFR}
    dump_sites bufh_sites.txt {REF_NAME == BUFHCE}
    dump_sites mmcm_sites.txt {REF_NAME =~ MMCME2*}
    dump_used_clock_pips design_pips.txt

    write_checkpoint -force design.dcp
    write_bitstream -force design.bit
}

run
