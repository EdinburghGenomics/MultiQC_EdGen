#!/usr/bin/env python3
from __future__ import print_function, division, absolute_import

""" MultiQC module to include unassigned barcodes. For now just suck in
    the report and link to it.
"""
import logging
import re, os

import base64
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

        html = '<div id="unassigned"{}>'.format(self.hidediv)

        # Move all the files into the report and link them
        for n, f in enumerate(self.find_log_files('edgen_unassigned', filehandles=True)):
            self.reports.append(f['fn'])
            rep_savpath = os.path.join(config.data_dir, 'unassigned{}.html'.format(n))
            rep_relpath = os.path.join(config.data_dir_name, 'unassigned{}.html'.format(n))

            # Copy the file
            with open(rep_savpath, 'w') as ofh:
                ofh.write(f['f'].read())
            html = '<a href="{}">View tables of unassigned barcodes</a><br />'.format(rep_relpath)
        html += '</div>'

        # Abort if none found
        log.info("Found {} reports".format(len(self.reports)))
        if not self.reports:
            return


        self.add_section(name='', plot=html)

