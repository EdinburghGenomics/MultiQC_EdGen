#!/usr/bin/env python3

""" MultiQC module to snag the HTML reports from FastqQC, in addition
    to the mutli-sample plots.
"""
import logging
import sys, os, re
import shutil
from collections import namedtuple
from distutils.version import StrictVersion

from multiqc import config
from multiqc.modules.base_module import BaseMultiqcModule

from html import escape as html_escape
from urllib.parse import quote as url_escape

# Initialise the logger, ensuring massages go to the main
# MultiQC modules log.
log = logging.getLogger('multiqc.modules.' + __name__)

class MultiqcModule(BaseMultiqcModule):
    """ Grab FastQC HTML reports. The .zip files are still fed to the regular
        FastQC modules.
    """

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='FastQC Original Reports', anchor='edgen_fastqc_original',
            href='http://www.bioinformatics.babraham.ac.uk/projects/fastqc/',
            info="are the original HTML files produced by FastQC.")

        # Find any HTML reports. We have to do this by finding the zips. Note there are maybe two FASTQC reports
        # per fragment, so each report looks like:
        FQCReport = namedtuple('FQCReport', "sample label read file".split())
        self.html_reports = []

        FIXME FIXME

        for zip_report in self.find_log_files('fastqc/zip', filehandles=True):

            rep_name = ( "{}_{}".format(zip_report['s_name'], zip_report.get('read_pairs'))
                          if zip_report.get('read_pairs')
                          else zip_report['s_name'] )

            self.html_reports[rep_name] = re.sub('\.zip$', '.html', zip_report['f'].name)
            zip_report['f'].close()

        if not self.html_reports:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(len(self.html_reports)))

        self.add_section( name = "Reports",
                          content = self.tack_on_reports() )

    def tack_on_reports(self):
        """ Copy every file into the data_dir and bung in a link to it here.
        """
        links = dict()

        for s_name, flist in self.html_reports.items():
            links[s_name] = "<span class='alt_col_link'>"

            for f in flist:
                fname = os.path.basename(f)

                shutil.copy(f, os.path.join( config.data_dir, fname ))
                file_relpath = os.path.join( config.data_dir_name, fname )

                links[s_name] += "<a href='{l}' title='{t} FastQC Report'>{t}</a>".format(
                                           l=url_escape(file_relpath), t=html_escape(s_name) )

            links[s_name] += "</span>"

        #Output in sorted order.
        if not links:
            links['error'] = "No FastQC HTML plots were found."

        return "<div>" +  " ".join(links[k] for k in sorted(links)) + "</div>"

