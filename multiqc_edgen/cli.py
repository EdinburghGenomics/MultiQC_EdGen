#!/usr/bin/env python
""" MultiQC command line options - we tie into the MultiQC
core here and add some new command line parameters. """

import click

# TODO - at present it just always runs.
enable_edgen = click.option('--enable_edgen', '--enable-edgen', 'edgen',
    is_flag = True,
    help = "Enable the MultiQC_EdGen plugin on this run"
)
# Not sure if we need this for anything really.
run_id = click.option('--run_id', '--run-id', '--rid',
    type = str,
    help = 'Manually specify the Run ID'
)
