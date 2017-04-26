#!/usr/bin/env python

""" MultiQC module to parse output from Cutadapt """
from __future__ import print_function, division, absolute_import
import logging
import re
from distutils.version import StrictVersion

from multiqc import config
from multiqc.plots import linegraph
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger, ensuring massages go to the main
# MultiQC modules log.
log = logging.getLogger('multiqc.modules.' + __name__)

class MultiqcModule(BaseMultiqcModule):
    """
    Cutadapt module class, parses stdout logs.
    This is a custom version for the EG Run reports. Support for cutadapt <1.7
    has been removed.
    """

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='Cutadapt', anchor='cutadapt',
        href='https://github.com/marcelm/cutadapt',
        info="is used to detect excessive adapter sequence - ie. short inserts" \
             "and adapter dimers in the read1 sequence data.")

        # Find and load any Cutadapt reports
        self.cutadapt_data = dict()
        self.cutadapt_length_counts = dict()

        #Use the standard configuration when looking for cutadapt files.
        for f in self.find_log_files(config.sp['cutadapt'], filehandles=True):
            self.parse_cutadapt_logs(f)

        if len(self.cutadapt_data) == 0:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(len(self.cutadapt_data)))

        # Write parsed report data to a file
        self.write_data_file(self.cutadapt_data, 'eg_cutadapt')

        # Add the percentage of seqs <5bp to the general stats table
        self.cutadapt_general_stats_table()

        # Trimming Length Profiles
        # Only one section, so add to the intro
        self.intro += self.cutadapt_length_trimmed_plot()


    def parse_cutadapt_logs(self, f):
        """ Go through one log file looking for cutadapt output """
        fh = f['f']
        regexes = {
                'bp_processed': "Total basepairs processed:\s*([\d,]+) bp",
                'bp_written': "Total written \(filtered\):\s*([\d,]+) bp",
                'quality_trimmed': "Quality-trimmed:\s*([\d,]+) bp",
                'r_processed': "Total reads processed:\s*([\d,]+)",
                'r_with_adapters': "Reads with adapters:\s*([\d,]+)"
            }
        s_name = None
        cutadapt_version = 'unknown'
        for l in fh:
            # Parse a line. Note there may be multiple logs in one file.
            s_name = None
            c_version = re.match(r'^This is cutadapt ([\d\.dev]+)', l)
            if c_version:
                cutadapt_version = c_version.group(1)

            # Get sample name from end of command line params
            if l.startswith('Command line parameters'):
                s_name = l.split()[-1]
                s_name = self.clean_s_name(s_name, f['root'])
                if s_name in self.cutadapt_data:
                    log.debug("Duplicate sample name found! Overwriting: {}".format(s_name))
                self.cutadapt_data[s_name] = dict()
                self.cutadapt_length_counts[s_name] = dict()

            if s_name is not None:
                self.add_data_source(f, s_name)

                # Search regexes for overview stats
                for k, r in regexes.items():
                    match = re.search(r, l)
                    if match:
                        self.cutadapt_data[s_name][k] = int(match.group(1).replace(',', ''))

                # Histogram showing lengths trimmed
                if 'length' in l and 'count' in l and 'expect' in l:
                    # Nested loop to read this section while the regex matches
                    for l in fh:
                        r_seqs = re.search("^(\d+)\s+(\d+)\s+([\d\.]+)", l)
                        if r_seqs:
                            a_len = int(r_seqs.group(1))
                            self.cutadapt_length_counts[s_name][a_len] = int(r_seqs.group(2))
                            self.cutadapt_length_exp[s_name][a_len] = float(r_seqs.group(3))
                            if float(r_seqs.group(3)) > 0:
                                self.cutadapt_length_obsexp[s_name][a_len] = float(r_seqs.group(2)) / float(r_seqs.group(3))
                            else:
                                # Cheating, I know. Infinity is difficult to plot.
                                self.cutadapt_length_obsexp[s_name][a_len] = float(r_seqs.group(2))
                        else:
                            break

        # Calculate a few extra numbers of our own
        for s_name, d in self.cutadapt_data.items():
            if 'bp_processed' in d and 'bp_written' in d:
                self.cutadapt_data[s_name]['percent_trimmed'] = (float(d['bp_processed'] - d['bp_written']) / d['bp_processed']) * 100
            elif 'bp_processed' in d and 'bp_trimmed' in d:
                self.cutadapt_data[s_name]['percent_trimmed'] = ((float(d.get('bp_trimmed', 0)) + float(d.get('quality_trimmed', 0))) / d['bp_processed']) * 100



    def cutadapt_general_stats_table(self):
        """ Take the parsed stats from the Cutadapt report and add it to the
        basic stats table at the top of the report """

        headers = {}
        headers['percent_trimmed'] = {
            'title': '% Trimmed',
            'description': '% Total Base Pairs trimmed',
            'max': 100,
            'min': 0,
            'suffix': '%',
            'scale': 'RdYlBu-rev',
            'format': '{:.1f}%'
        }
        self.general_stats_addcols(self.cutadapt_data, headers)


    def cutadapt_length_trimmed_plot (self):
        """ Generate the trimming length plot """
        html = '<p>This plot shows the number of reads with certain lengths of adapter trimmed. \n\
        Obs/Exp shows the raw counts divided by the number expected due to sequencing errors. A defined peak \n\
        may be related to adapter length. See the \n\
        <a href="http://cutadapt.readthedocs.org/en/latest/guide.html#how-to-read-the-report" target="_blank">cutadapt documentation</a> \n\
        for more information on how these numbers are generated.</p>'

        pconfig = {
            'id': 'cutadapt_plot',
            'title': 'Lengths of Trimmed Sequences',
            'ylab': 'Counts',
            'xlab': 'Length Trimmed (bp)',
            'xDecimals': False,
            'ymin': 0,
            'tt_label': '<b>{point.x} bp trimmed</b>: {point.y:.0f}',
            'data_labels': [{'name': 'Counts', 'ylab': 'Count'},
                            {'name': 'Obs/Exp', 'ylab': 'Observed / Expected'}]
        }

        html += linegraph.plot([self.cutadapt_length_counts, self.cutadapt_length_obsexp], pconfig)

        return html
