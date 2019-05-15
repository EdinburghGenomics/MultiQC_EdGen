#!/usr/bin/env python3
from __future__ import print_function, division, absolute_import

""" MultiQC module to include unassigned barcodes. For now just suck in
    the report and link to it.
"""
import logging
import re, os

import base64
import json
from html import escape as html_escape
# This needs Python >=3.5!
from subprocess import run

from pprint import pprint
from multiqc import config
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger, ensuring massages go to the main
# MultiQC modules log.
log = logging.getLogger('multiqc.modules.' + __name__)

class MultiqcModule(BaseMultiqcModule):
    """ Unassigned barcodes report linkerer.
    """

    def __init__(self):

        super(MultiqcModule, self).__init__(name='Unassigned Barcodes', anchor='unassigned',
                href='http://gitlab.genepool.private/production-team/illuminatus',
                info='Tries to identify and tabulate unassigned barcodes.')

        self.hidediv = ''

        # There should just be one report, but I'll allow for there to be many
        self.reports = []

        html = ''
        #html += '<div id="unassigned"{}>'.format(self.hidediv)

        # Move all the files into the report and link them
        for n, f in enumerate(self.find_log_files('edgen_unassigned', filehandles=True)):
            self.reports.append(f['fn'])
            rep_savpath = os.path.join(config.data_dir, 'unassigned{}.html'.format(n))
            rep_relpath = os.path.join(config.data_dir_name, 'unassigned{}.html'.format(n))

            # Copy the file
            with open(rep_savpath, 'w') as ofh:
                ofh.write(f['f'].read())
            html += '<a href="{}">View tables of unassigned barcodes</a><br />'.format(rep_relpath)
        #html += '</div>'


        log.info("Found {} reports".format(len(self.reports)))
        if self.reports:
            self.add_section(name='Legacy Report', plot=html)

        # We're now grabbing the barcodes out of Stats.json too. This is hacky, but what isn't?
        ub_sorted = []
        if os.path.exists("Stats.json"):
            with open("Stats.json") as sfh:
                ub = json.load(sfh).get("UnknownBarcodes", [])

            if len(ub) == 1:
                # There is one lane. Assume it's the right lane.
                ub_codes = ub[0]["Barcodes"]

                # Now we have a dict. In the original files the list is sorted by count but this will
                # be lost, so re-sort.
                ub_sorted = sorted(ub_codes.items(), key=lambda i: int(i[1]), reverse=True)

        if ub_sorted:

            html = '<textarea rows="12" columns="42">' + '\n'.join('\t'.join(i) for i in ub_sorted) + '</textarea>'

            self.add_section(name='UnknownBarcodes from Stats.json', plot=html)

