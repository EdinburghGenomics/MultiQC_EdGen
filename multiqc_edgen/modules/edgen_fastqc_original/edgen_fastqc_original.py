#!/usr/bin/env python3

""" MultiQC module to snag the HTML reports from FastqQC, in addition
    to the mutli-sample plots.
"""
import logging
import sys, os, re
import shutil
from collections import namedtuple, OrderedDict
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
            info="are the original HTML files produced by FastQC. Paired-end runs have two reports per library.")

        # Find any HTML reports. We have to do this by finding the associated zips! Note there are maybe two FASTQC reports
        # per fragment, so each report looks like:
        FQCReport = namedtuple('FQCReport', "sample read file".split())
        self.html_reports = []

        for zip_report in self.find_log_files('fastqc/zip', filehandles=True):

            self.html_reports.append( FQCReport( zip_report['s_name'],
                                                 zip_report.get('read_pairs'),
                                                 re.sub('\.zip$', '.html', zip_report['f'].name) ) )

            zip_report['f'].close()

        if not self.html_reports:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        self.samples_list = sorted(set(r.sample for r in self.html_reports))
        log.info("Found {} reports for {} samples".format(len(self.html_reports), len(self.samples_list)))

        self.add_section( name = "Reports",
                          content = self.tack_on_reports() )

    def tack_on_reports(self):
        """ Copy every file into the data_dir and bung in a link to it here.
        """
        links = OrderedDict()

        # Go through the already-sorted list of samples.
        for s_name in self.samples_list:
            links[s_name] = "<span class='alt_col_link'>"

            # Cycle through the reports. Presumably there are one or two.
            reps = sorted( [ r for r in self.html_reports if r.sample == s_name ],
                           key = lambda r: r.read )
            for n, rep in enumerate(reps):

                # This is a little funky but seems most legible...
                rep_label = "{}_{}".format(rep.sample, rep.read) if len(reps) > 1 else rep.sample
                link_label = rep_label if n == 0 else "..._{}".format(rep.read)
                fname = os.path.basename(rep.file)

                shutil.copy(rep.file, os.path.join( config.data_dir, fname ))
                file_relpath = os.path.join( config.data_dir_name, fname )

                links[s_name] += "<a href='{f}' title='{rl} FastQC Report'>{ll}</a> ".format(
                                        f = url_escape(file_relpath),
                                        rl = html_escape(rep_label),
                                        ll = html_escape(link_label) )

            links[s_name] += "</span>"

        #Output in sorted order.
        if not links:
            links['error'] = "No FastQC HTML plots were found."

        return "<div>" +  " ".join(links[k] for k in sorted(links)) + "</div>"

