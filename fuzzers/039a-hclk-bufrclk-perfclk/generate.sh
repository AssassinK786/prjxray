#!/bin/bash
# Copyright (C) 2017-2020  The Project X-Ray Authors.
#
# Use of this source code is governed by a ISC-style
# license that can be found in the LICENSE file or at
# https://opensource.org/licenses/ISC
#
# SPDX-License-Identifier: ISC
#
# Specimen driver: derive FUZZ_MODE from the specimen directory name and
# hand over to the generic top_generate.mk.
set -euo pipefail

spec="${1:?specimen dir}"

# A directory left behind by an interrupted run would be picked up as
# finished work.  Drop only this specimen, never a sibling.
if [ -d "$spec" ] && [ ! -f "$spec/OK" ]; then
    rm -rf "$spec"
fi

# genheader.sh reads $SPECDIR before exporting it, which is fine without
# nounset and aborts with it.  Its own scripts run under `set -ex` only.
set +u
# shellcheck disable=SC1090
source "${XRAY_GENHEADER}"
set -u

case "$(basename "$SPECDIR")" in
    specimen_cal0) export FUZZ_MODE=cal0 ;;
    specimen_cal1) export FUZZ_MODE=cal1 ;;
    specimen_cal2) export FUZZ_MODE=cal2 ;;
    specimen_cal3) export FUZZ_MODE=cal3 ;;
    specimen_neg_ioi) export FUZZ_MODE=neg_ioi ;;
    specimen_neg_unused) export FUZZ_MODE=neg_unused ;;
    specimen_neg_bufh) export FUZZ_MODE=neg_bufh ;;
    specimen_neg_unconsumed) export FUZZ_MODE=neg_unconsumed ;;
    specimen_perf0) export FUZZ_MODE=perf0 ;;
    specimen_perf1) export FUZZ_MODE=perf1 ;;
    *) export FUZZ_MODE="${FUZZ_MODE:-campaign}" ;;
esac

make -f "${XRAY_DIR}/utils/top_generate.mk"
