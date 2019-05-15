#!/usr/bin/env python3

""" MultiQC module to snag the HTML reports from FastqQC, in addition
    to the mutli-sample plots.
"""
import logging
import re
from distutils.version import StrictVersion

# python2 doesn't have this!
from itertools import accumulate
from collections import defaultdict

from multiqc import config
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger, ensuring massages go to the main
# MultiQC modules log.
log = logging.getLogger('multiqc.modules.' + __name__)

class MultiqcModule(BaseMultiqcModule):
    """ Grab FastQC HTML reports. The .zip files are still fed to the regular
        FastQC modules.
    """

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='FastQC Original Reports', anchor='eggen_fastqc_original',
        href='http://www.bioinformatics.babraham.ac.uk/projects/fastqc/',
        info="are the original HTML files produced by FastQC.")

        # Find any HTML reports
        self.html_reports = list(self.find_log_files('edgen_fastqc_original', filehandles=False))

        if not self.html_reports:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(len(self.html_reports)))

        self.add_section( name = "Reports",
                          content = self.tack_on_reports() )

    def tack_on_reports(self):
        """ Copy the file into the data_dir and bung in a link to it here.
        """
        links = dict()
        for f in self.html_reports:

            shutil.copy(os.path.join(f['root'], f['fn']),
                        os.path.join(config.data_dir, f['fn']))
            file_relpath = os.path.join(config.data_dir_name, f['fn'])

            #Let's use a popover, since bootstrap is already loaded in the document.
            #https://www.w3schools.com/bootstrap/bootstrap_popover.asp
            links[f['s_name']] = "<a href='{l}' title='{t} FastQC Report'>{t}</a>".format(
                                    l=url_escape(file_relpath), t=html_escape(f['s_name']) )

        #Output in sorted order.
        if not links:
            links['error'] = "No FastQC HTML plots were found."

        return jscript + "<div>" +  " ".join([links[k] for k in sorted(links)]) + "</div>"

