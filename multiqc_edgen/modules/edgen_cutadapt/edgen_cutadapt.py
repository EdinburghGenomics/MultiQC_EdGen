#!/usr/bin/env python3

""" MultiQC module to parse output from Cutadapt """
from __future__ import print_function, division, absolute_import
import logging
import re
from distutils.version import StrictVersion

# python2 doesn't have this!
from itertools import accumulate
from collections import defaultdict

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

    #Anything shorter than this after trimming is considered an adapter dimer.
    SIZE_CUTOFF = 5

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='Cutadapt', anchor='cutadapt',
        href='https://github.com/marcelm/cutadapt',
        info="is used to detect excessive adapter sequence - ie. short inserts" \
             "and adapter dimers in the read1 sequence data.")

        # Find and load any Cutadapt reports
        self.cutadapt_data = dict()
        self.cutadapt_trimmed_histo = dict()

        #Use the standard configuration when looking for cutadapt files.
        for f in self.find_log_files('cutadapt'):
            self.parse_cutadapt_log(f)
        self.calculate_extra_numbers()

        if len(self.cutadapt_data) == 0:
            log.debug("Could not find any reports in {}".format(config.analysis_dir))
            raise UserWarning

        log.info("Found {} reports".format(len(self.cutadapt_data)))

        # Write parsed report data to a file
        self.write_data_file(self.cutadapt_data, 'edgen_cutadapt')

        # Add the percentage of seqs <5bp to the general stats table
        self.cutadapt_general_stats_table()

        # Trimming Length Profiles
        # Only one section, so add to the intro
        self.intro += self.cutadapt_length_plot()


    def parse_cutadapt_log(self, f):
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
            c_version = re.match(r'^This is cutadapt ([\d\.dev]+)', l)
            if c_version:
                #We're on a new log, and so a new sample.
                s_name = None
                cutadapt_version = c_version.group(1)

            # Get sample name from end of command line params
            if l.startswith('Command line parameters'):
                s_name = l.split()[-1]
                s_name = self.clean_s_name(s_name, f['root'])
                self.add_data_source(f, s_name)
                if s_name in self.cutadapt_data:
                    log.warning("Duplicate sample name found in {}! Overwriting: {}".format(f['fn'], s_name))
                self.cutadapt_data[s_name] = dict(adapter_count=0)
                self.cutadapt_trimmed_histo[s_name] = defaultdict(int)

            if s_name is not None:

                # Search regexes for overview stats
                for k, r in regexes.items():
                    match = re.search(r, l)
                    if match:
                        self.cutadapt_data[s_name][k] = int(match.group(1).replace(',', ''))

                # Histogram showing lengths trimmed. We'll ignore expect and max.err as they
                # are fairly useless but still look for them in the header.
                if l.startswith('length\tcount\texpect\tmax.err'):
                    # Nested loop to read this section while the regex matches
                    self.cutadapt_data[s_name]['adapter_count'] += 1
                    for l in fh:
                        r_seqs = re.search("^(\d+)\s+(\d+)\s+([\d\.]+)", l)
                        if r_seqs:
                            #Snag just cols 1 and 2
                            a_len = int(r_seqs.group(1))
                            #Adding up the numbers may not make sense if --times was set >1 when
                            #running cutadapt, but in that case I don't know what would make sense.
                            self.cutadapt_trimmed_histo[s_name][a_len] += int(r_seqs.group(2))
                        else:
                            break #go back to main loop

    def calculate_extra_numbers(self):
        """Calculate a few extra numbers of our own.
           This wants to be called once after all the logs are parsed.
           self.cutadapt_data is currently a dict where
           the keys are sample names and the values are dicts of summary stats.
        """
        for s_name, d in self.cutadapt_data.items():
            if 'bp_processed' in d and 'bp_written' in d:
                self.cutadapt_data[s_name]['percent_trimmed'] = 100 * \
                    ( float(d['bp_processed'] - d['bp_written'])
                      / d['bp_processed'] )
            elif 'bp_processed' in d and 'bp_trimmed' in d:
                self.cutadapt_data[s_name]['percent_trimmed'] = 100 * \
                    ( (float(d.get('bp_trimmed', 0)) + float(d.get('quality_trimmed', 0)))
                      / d['bp_processed'] )

            #Re-format the cutadapt_trimmed_histo to be more useful for our purposes.
            lh = self.cutadapt_data[s_name]['length_histo'] = self.get_length_histo(s_name)

            #Use this to ask how many of the sequences were less than SIZE_CUTOFF
            self.cutadapt_data[s_name]['percent_short'] = 100 * \
                sum(lh[:self.SIZE_CUTOFF]) / sum(lh[:])


    def get_length_histo(self, s_name):
        """Calculate the lengths of sequences after trimming, by subtracting the trimmed
           values from the sequence length. For visualising short sequences and dimers this
           makes more sense than a raw plot of bases trimmed.
           We assume all the sequences are the same length - if not, this will still produce
           an array of numbers but they will be wrong.
        """
        cdata = self.cutadapt_data[s_name]
        cth = self.cutadapt_trimmed_histo[s_name]

        #Infer read length
        read_length = max( (cdata['bp_processed'] // cdata['r_processed']),
                           *cth.keys() )

        # Return a list indexed by trimmed_length tl from 0 to read_length inclusive
        # The final value will be all the untrimmed reads which are not in ctl.
        return [ cth.get(read_length-tl,0) for tl in range(read_length) ] + \
               [ cdata['r_processed'] - sum( cth.values() ) ]

    def cutadapt_general_stats_table(self):
        """ Take the parsed stats from the Cutadapt report and add it to the
            basic stats table at the top of the report.
            We're interested in the number of sequences shorter than 5bp after
            trimming.
        """

        headers = {}
        headers['percent_short'] = {
            'title': '% Dimer',
            'description': '% of sequences <{}bp after adapter trimming'.format(self.SIZE_CUTOFF),
            'max': 100,
            'min': 0,
            'suffix': '%',
            'scale': 'RdYlBu-rev',
            'format': '{:.3f}%'
        }
        self.general_stats_addcols(self.cutadapt_data, headers)


    def cutadapt_length_plot (self):
        """ Generate the post-trim length plot """
        html = '''<p>
            This plot shows the cumulative number of reads with certain lengths after the adapter was trimmed.
            You can view up to 10 bases or up to the ful sequence length.
            You can show the numbers as raw counts or as percentages of the reads.</p>
        '''

        pconfig = {
            'id': 'cutadapt_plot',
            'title': 'Lengths of Trimmed Sequences',
            'xlab': 'Cumulative length After Trim (bp)',
            'xDecimals': False,
            'xPlotBands': [5], #Not supported on highcharts graphs?
            'ymin': 0,
            'yMinRange': 1,
            'tt_label': '<b>{point.x} bp</b>: {point.y:.0f}',
            'data_labels': [
                            {'name': 'Percentages up to 10bp', 'ylab': 'Percent'},
                            {'name': 'Counts up to 10bp', 'ylab': 'Count'},
                            {'name': 'Percentages', 'ylab': 'Percent'},
                            {'name': 'Counts', 'ylab': 'Count'},
                           ]
        }

        #The length_histo needs to be converted to cumulative values.
        #After doing that, we can divide all numbers by the total to get a percentage plot.
        #Also, the lists need to be supplied as dicts
        acc_len_10 = { k: dict(enumerate(accumulate(v['length_histo'][:11]))) for k, v in self.cutadapt_data.items() }
        acc_perc_10 = { k: {k2: 100*l/self.cutadapt_data[k]['r_processed'] for k2, l in v.items()} for k, v in acc_len_10.items() }

        acc_len = { k: dict(enumerate(accumulate(v['length_histo']))) for k, v in self.cutadapt_data.items() }
        acc_perc = { k: {k2: 100*l/self.cutadapt_data[k]['r_processed'] for k2, l in v.items()} for k, v in acc_len.items() }

        html += linegraph.plot([ acc_perc_10, acc_len_10, acc_perc, acc_len ], pconfig)

        return html
