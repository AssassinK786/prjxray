# Project X-Ray

[![Documentation Status](https://img.shields.io/readthedocs/prjxray?longCache=true&style=flat-square&logo=ReadTheDocs&logoColor=fff)](http://prjxray.readthedocs.org/)
[![License](https://img.shields.io/github/license/f4pga/prjxray.svg?longCache=true&style=flat-square&label=License)](https://github.com/f4pga/prjxray/blob/master/LICENSE)
![GitHub Actions](https://img.shields.io/github/actions/workflow/status/f4pga/prjxray/Automerge.yml?branch=master&longCache=true&style=flat-square&label=GHA&logo=Github%20Actions&logoColor=fff)

Documenting the Xilinx 7-series bit-stream format.

This repository contains both tools and scripts which allow you to document the
bit-stream format of Xilinx 7-series FPGAs.

More documentation can be found published on [prjxray ReadTheDocs site](https://prjxray.readthedocs.io/en/latest/) - this includes;
 * [Highlevel Bitstream Architecture](https://prjxray.readthedocs.io/en/latest/architecture/overview.html)
 * [Overview of DB Development Process](https://prjxray.readthedocs.io/en/latest/db_dev_process/index.html)

# Quickstart Guide
Instructions were originally written for Ubuntu 16.04. Please let us know if you have information on other distributions.

### Step 1: ###
Install Vivado 2017.2. If you did not install to /opt/Xilinx default, then set the environment variable
XRAY_VIVADO_SETTINGS to point to the settings64.sh file of the installed vivado version, ie

    export XRAY_VIVADO_SETTINGS=/opt/Xilinx/Vivado/2017.2/settings64.sh

Do not source the settings64.sh in your shell, since this adds directories of
the Vivado installation at the beginning of your PATH and LD_LIBRARY_PATH
variables, which will likely interfere with or break non-Vivado applications in
that shell. The Vivado wrapper utils/vivado.sh makes sure that the environment
variables from XRAY_VIVADO_SETTINGS are automatically sourced in a separate
shell that is then only used to run Vivado to avoid these problems.

**Why 2017.2?** Currently the fuzzers only work on `2017.2`, see [Issue #14 on prjxray](https://github.com/f4pga/prjxray/issues/14).

**Is 2017.2 really required?** Yes, only `2017.2` works. Until Issue #14 is solved, **only** `2017.2` works and will be supported.

### Step 2: ###
Clone the ``prjxray`` repository and its submodules:

```bash
git clone git@github.com:f4pga/prjxray.git
cd prjxray
git submodule update --init --recursive
```

### Step 3: ###
Install CMake:

```bash
sudo apt-get install cmake # version 3.5.0 or later required,
                           # for Ubuntu Trusty pkg is called cmake3
```

### Step 4: ###
Build the C++ tools, in the prjxray root directory run:

```bash
make build
```

### Step 5: ###
Choose one of the following options:

(Option 1) - Install the Python environment locally

```bash
sudo apt-get install virtualenv python3 python3-pip python3-virtualenv python3-yaml
make env
```

(Option 2) - Install the Python environment globally

```bash
sudo apt-get install python3 python3-pip python3-yaml
sudo -H pip3 install -r requirements.txt
```

This step is known to fail with a compiler error while building the `pyjson5`
library when using Arch Linux and Fedora. If this occurs, `pyjson5` needs one
change to build correctly:

```bash
git clone https://github.com/Kijewski/pyjson5.git
cd pyjson5
sed -i 's/char \*PyUnicode/const char \*PyUnicode/' src/_imports.pyx
sudo make
```

This might give you an error about `sphinx_autodoc_typehints` but it should
correctly build and install pyjson5. After this, run either option 1 or 2 again.

### Step 6: ###

Prepare the database with static part information, which are needed by the
fuzzers, either for all device families

```bash
make db-prepare-parts
```

or only for a selected one

```bash
make db-prepare-artix7
```

### Step 7: ###
Always make sure to set the environment for the device you are working on before
running any other commands:

```bash
source settings/artix7.sh
```

### Step 8: ###

(Option 1, recommended) - Download a current stable version (you can use the
Python API with a pre-generated database)

```bash
./download-latest-db.sh
```

(Option 2) - (Re-)create the entire database (this will take a very long time!)

```bash
cd fuzzers
make -j$(nproc)
```

### Step 9: ###
Pick a fuzzer (or write your own), from the ``prjxray`` root dir, run:

```bash
cd fuzzers/010-clb-lutinit
make -j$(nproc) run
```

### Step 10: ###
Create HTML documentation, from the ``prjxray`` root dir, run:

```
cd htmlgen
python3 htmlgen.py
```

# C++ Development

Tests are not built by default.  Setting the PRJXRAY\_BUILD\_TESTING option to
ON when running cmake will include them. From the ``prjxray`` root dir, run:

```bash
mkdir -p build
cd build
cmake -DPRJXRAY_BUILD_TESTING=ON ..
make
```

The default C++ build configuration is for releases (optimizations enabled, no
debug info). A build configuration for debugging (no optimizations, debug info)
can be chosen via the CMAKE\_BUILD\_TYPE option. From the ``prjxray`` root dir, run:

```bash
mkdir -p build
cd build
cmake -DCMAKE_BUILD_TYPE=ON ..
make
```

The options to build tests and use a debug build configuration are independent
to allow testing that optimizations do not cause bugs.  The build configuration
and build tests options may be combined to allow all permutations.

# Process

The documentation is done through a "black box" process were Vivado is asked to
generate a large number of designs which then used to create bitstreams. The
resulting bit streams are then cross correlated to discover what different bits
do.

## Parts

### [Minitests](minitests)

There are also "minitests" which are designs which can be viewed by a human in
Vivado to better understand how to generate more useful designs.

### [Experiments](experiments)

Experiments are like "minitests" except are only useful for a short period of
time. Files are committed here to allow people to see how we are trying to
understand the bitstream.

When an experiment is finished with, it will be moved from this directory into
the latest "prjxray-experiments-archive-XXXX" repository.

### [Fuzzers](fuzzers)

Fuzzers are the scripts which generate the large number of bitstream.

They are called "fuzzers" because they follow an approach similar to the
[idea of software testing through fuzzing](https://en.wikipedia.org/wiki/Fuzzing).

### [Tools](tools) & [Libs](lib)

Tools & libs are useful tools (and libraries) for converting the resulting
bitstreams into various formats.

Binaries in the tools directory are considered more mature and stable then
those in the [utils](utils) directory and could be actively used in other
projects.

### [Utils](utils)

Utils are various tools which are still highly experimental. These tools should
only be used inside this repository.

### [Third Party](third_party)

Third party contains code not developed as part of Project X-Ray.


# Database

Running the all fuzzers in order will produce a database which documents the
bitstream format in the [database](database) directory.

As running all these fuzzers can take significant time,
[Tim 'mithro' Ansell <me@mith.ro>](https://github.com/mithro) has graciously
agreed to maintain a copy of the database in the
[prjxray-db](https://github.com/f4pga/prjxray-db) repository.

Please direct enquires to [Tim](mailto:me@mith.ro) if there are any issues with
it.

# Current Focus

Current the focus has been on the Artix-7 50T part. This structure is common
between all footprints of the 15T, 35T and 50T varieties.

We have also started experimenting with the Kintex-7 and Virtex-7 parts.

The aim is to eventually document all parts in the Xilinx 7-series FPGAs but we
can not do this alone, **we need your help**!

## Virtex-7 Port Status (`virtex7-support` branch)

This branch ports the openXC7 prjxray flow to **Virtex-7 `xc7vx485tffg1761-2`**
(VC707 board), modelled on the Kintex-7 sub-flow. The goal is a fully
open-source bit→DCP / fasm→bit round-trip on a Virtex-7 HP-only part.

### Achievements

- **End-to-end smoke test passes** on `xc7vx485tffg1761-2`: System-Verilog
  → Yosys → nextpnr-xilinx → FASM → `fasm2frames.py` → `xc7frames2bit`
  → `.bit`. First run required 3 patches and surfaced 2 nextpnr-xilinx bugs
  (filed upstream).
- **Cross-family segbits/ppips transplant** from the openXC7
  [`prjxray-db`](https://github.com/openXC7/prjxray-db) Kintex-7 tree into
  `database/virtex7/`: ~39 381 segbits + ~12 273 ppips entries, plus targeted
  key copies for `clk_hrow_*`, `clk_bufg_*`, `hclk_cmt*`, `io_int_interface_*`
  (≈51 k entries total). Pre-transplant tree backed up at
  `database/virtex7.before_transplant/`.
- **11 fuzzers patched** for HP-bank / virtex7-grid awareness:
  - `037-iob18-pips` — left-side mirror sites (LIOI / LIOI_TBYTESRC /
    LIOI_TBYTETERM), `top.py` NOT_INCLUDED_TILES for `*_SING`, generate-side
    tile-type normalization, `ioi_pip_list.tcl` LIOI emission.
  - `039-hclk-config` — virtex7 split (HCLK_IOI vs HCLK_IOI3),
    `XRAY_IOSTANDARD` env var, IOB18M / IOB33M alternation in `top.py`.
  - `047a-hclk-idelayctrl-pips` — accepts both HCLK_IOI and HCLK_IOI3.
  - `034 / 034b / 041 / 043 / 044 / 045 / 046` — removed local
    `write_pip_txtdata` overrides that shadowed the patched `utils.tcl`
    bulk-fetch (~4× faster per specimen on xc7vx485t).
- **`utils/utils.tcl` bulk-fetch patch** for `write_pip_txtdata` —
  per-net `foreach pip` → bulk `get_pips` + bulk `get_property IS_DIRECTIONAL`
  + cached `dst_wire_to_num_pips`. ~4× speed-up; on
  `xc7vx485tffg1761-2` cuts `041-clk-hrow-pips`/`045-hclk-cmt-pips` specimens
  from ~1.5 h to ~25 min each.
- **`utils/fasm2frames.py` HP-bank fix** — was hard-coded to `HCLK_IOI3_*`
  tile prefix; now probes the grid for whichever of `HCLK_IOI_` / `HCLK_IOI3_`
  exists. STEPDOWN bank-anchor check widened accordingly.
- **`utils/mergedb.sh` extended** with LIOI / LIOI_TBYTESRC / LIOI_TBYTETERM
  / LIOB18 / mask_liob18 cases.
- **RapidWright `json2dcp.jar` rebuilt** against modern RapidWright (2025.2.1)
  and patched for virtex7 — at `~/rapidwright/build/rapidwright_json2dcp.jar`
  (17 KB). Verified `rst_to_led_routed.json` → 1.38 MB DCP that loads back
  cleanly on `xc7vx485tffg1761-2`. Patch list in
  `~/rapidwright/build/README.md`.

### Goals

- Document `xc7vx485tffg1761-2` bitstream format with parity sufficient for a
  Vivado-equivalent bitstream on IOB-only designs first, then SLICE and CMT.
- Achieve bit ↔ bit equivalence with Vivado on the `rst_to_led` pass-through
  reference, then incrementally on counter, BUFR/IDELAY, and CMT designs.
- Provide a runnable bit→DCP path so open-flow bitstreams can be inspected /
  diffed against Vivado checkpoints (Phase A via `json2dcp.jar` done; Phase B
  via a virtex7-aware `fasm2bels` still in progress).

### Work in Progress

- **030-iob18 N=200 rerun** for finer IOSTANDARD/DRIVE coverage on LIOB18.
  Running at one specimen per ~3 min, currently ≈187 of 200 specimens written;
  will trigger `make pushdb` automatically on completion.
- **LIOB18 IOSTANDARD bit-encoding bug** — `rst_to_led.bit` produced by our
  flow flickers and is unresponsive on hardware; Vivado-built reference works.
  Targeted bit-diff localised the discrepancy to LIOI and LIOI_TBYTETERM
  tiles sharing a frame range but with different word offsets — partial fix
  applied (per-tile partitioning) reduced missing bits 28 → 21 and extras
  14 → 12, but IOSTANDARD bits still wrong. Awaiting N=200 segdata to
  re-derive.
- **037-iob18-pips left-side coverage** — residual pip-convergence iteration;
  iter 1 was salvaged after a JVM crash on `spec_008` left 19 surviving
  specimens that yielded 128 LIOI entries.
- **Phase B — virtex7 `fasm2bels` port** — parked. Connection database for
  `xc7vx485tffg1761-2` builds successfully (14 min, 4.2 GB on disk, 56.8 M
  wires). First failure is in `clb_models.py` on the nextpnr-emitted
  PSEUDO_VCC packer cell (`assert False, {'NOCLKINV'}`). IOB18 / HP-bank BEL
  name substitutions drafted in `models/iob_models.py` (uncommitted).
- **Open TODOs (cross-cutting)** — expand the virtex7 ROI; add a Vivado DRC
  cross-check of nextpnr output; exclude `GTX_INT_INTERFACE` pips from the
  virtex7 chipdb; add bits info for `CFG_CENTER` / `*_SING` tiles.

### Constraints

- Patches must **not** regress other families (artix7 / kintex7 / zynq7 /
  spartan7). The HP-bank additions are gated on tile-type prefix so the
  HR-bank paths stay byte-identical.
- Build artefacts under `fuzzers/*/build/` are **retained** for debugging
  — `make clean` is not invoked between fuzzer iterations.

## Adding a new part to an existing family

We have written a [detailed guide](https://f4pga.readthedocs.io/projects/prjxray/en/latest/db_dev_process/newpart.html) that walks through the process of adding a new part to an existing family.

## TODO List

 - [ ] Write a TODO list


# Contributing

There are a couple of guidelines when contributing to Project X-Ray which are
listed here.

### Sending

All contributions should be sent as
[GitHub Pull requests](https://help.github.com/articles/creating-a-pull-request-from-a-fork/).

### License

All software (code, associated documentation, support files, etc) in the
Project X-Ray repository are licensed under the very permissive
[ISC Licence](https://opensource.org/licenses/ISC). A copy can be found in the [`LICENSE`](LICENSE) file.

All new contributions must also be released under this license.

### Code of Conduct

By contributing you agree to the [code of conduct](CODE_OF_CONDUCT.md). We
follow the open source best practice of using the [Contributor
Covenant](https://www.contributor-covenant.org/) for our Code of Conduct.

### Sign your work

To improve tracking of who did what, we follow the Linux Kernel's
["sign your work" system](https://github.com/wking/signed-off-by).
This is also called a
["DCO" or "Developer's Certificate of Origin"](https://developercertificate.org/).

**All** commits are required to include this sign off and we use the
[Probot DCO App](https://github.com/probot/dco) to check pull requests for
this.

The sign-off is a simple line at the end of the explanation for the
patch, which certifies that you wrote it or otherwise have the right to
pass it on as a open-source patch.  The rules are pretty simple: if you
can certify the below:

        Developer's Certificate of Origin 1.1

        By making a contribution to this project, I certify that:

        (a) The contribution was created in whole or in part by me and I
            have the right to submit it under the open source license
            indicated in the file; or

        (b) The contribution is based upon previous work that, to the best
            of my knowledge, is covered under an appropriate open source
            license and I have the right under that license to submit that
            work with modifications, whether created in whole or in part
            by me, under the same open source license (unless I am
            permitted to submit under a different license), as indicated
            in the file; or

        (c) The contribution was provided directly to me by some other
            person who certified (a), (b) or (c) and I have not modified
            it.

	(d) I understand and agree that this project and the contribution
	    are public and that a record of the contribution (including all
	    personal information I submit with it, including my sign-off) is
	    maintained indefinitely and may be redistributed consistent with
	    this project or the open source license(s) involved.

then you just add a line saying

	Signed-off-by: Random J Developer <random@developer.example.org>

using your real name (sorry, no pseudonyms or anonymous contributions.)

You can add the signoff as part of your commit statement. For example:

    git commit --signoff -a -m "Fixed some errors."

*Hint:* If you've forgotten to add a signoff to one or more commits, you can use the
following command to add signoffs to all commits between you and the upstream
master:

    git rebase --signoff upstream/master

### Contributing to the docs

In addition to the above contribution guidelines, see the guide to
[updating the Project X-Ray docs](UPDATING-THE-DOCS.md).
