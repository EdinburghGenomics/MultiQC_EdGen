#!/usr/bin/env python3
from __future__ import print_function, division, absolute_import

""" MultiQC module to include unassigned barcodes. For now just suck in
    the report and link to it.
"""
import logging
import os

import shutil
from glob import glob

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
                href='https://github.com/EdinburghGenomics/illuminatus',
                info='Tries to identify and tabulate unassigned barcodes.')

        self.hidediv = ''

        html = ''
        #html += '<div id="unassigned"{}>'.format(self.hidediv)

        # For the old-school reports, move all the files into the report and link them
        analysis_dir = config.analysis_dir[0] if config.analysis_dir else "."
        legacy_reports = sorted(glob( analysis_dir + '/*.unassigned' ) ) # May be 0?
        log.info("Found {} legacy reports".format(len(legacy_reports)))
        for n, f in enumerate(legacy_reports):
            log.info("Found legacy report {}".format(f))
            rep_savpath = os.path.join(config.data_dir, 'unassigned{}.html'.format(n))
            rep_relpath = os.path.join(config.data_dir_name, 'unassigned{}.html'.format(n))

            # Copy the file
            shutil.copy(f, rep_savpath)
            html += '<a href="{}">View tables of unassigned barcodes</a><br />'.format(rep_relpath)
        #html += '</div>'

        if legacy_reports:
            self.add_section(name='Legacy Report', plot=html)

        # Now the unassigned_table.txt which is just a basic text file emitted by the pipeline.
        # We expect just one.
        html = ''
        for n, f in enumerate(self.find_log_files('edgen_unassigned', filehandles=True)):
            ub = f['f'].read()

            html += '<textarea rows="8" cols="100" readonly="true" style="font-family: monospace,monospace;">'
            html += ub.strip() or '---'
            html += '</textarea>'

        # Assume there was at least one report, or we'd not have been called at all.
        self.add_section(name='UnknownBarcodes list in Stats.json', plot=html)

