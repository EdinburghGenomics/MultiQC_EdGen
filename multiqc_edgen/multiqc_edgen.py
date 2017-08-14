#!/usr/bin/env python
from __future__ import print_function, division, absolute_import
""" MultiQC hook functions - we tie into the MultiQC
core here to add in extra functionality and logic for EdGen run reports. """

from collections import OrderedDict
import logging
import os, sys, re
from glob import glob
import yaml
import base64
from cgi import escape

from pkg_resources import get_distribution
__version__ = get_distribution("multiqc_edgen").version

import multiqc
from multiqc.utils import report, util_functions, config

log = logging.getLogger('multiqc')

#Container for the meta-data. Add keys that match things in the HTML template(s).
report.edgen_run = dict()

class edgen_before_modules():
    """Blacklist some modules so that replacement ones can be provided
       by this plugin.
    """
    def __init__(self):
        self.blacklist_modules()

    def blacklist_modules(self):

        blacklist = ['cutadapt', 'vcftools']

        for m in blacklist:
            if m in config.run_modules:
                log.info("Suppressing default {} module.".format(m))

                del(config.run_modules[m])


class edgen_before_report():
    """ Custom code to run after the modules have finished but before the report.
        This is the place to insert metadata tables at the top of the report and
        any other tweaks we need to do.
    """

    def __init__(self):

        log.debug("Running MultiQC_EdGen v{} (before_report)".format(__version__))

        # NGI uses a global try statement to catch any unhandled exceptions
        # and stop MultiQC from crashing. But I think I want to fail if this bit fails.
        # At least for now.

        # Down the line, note that installing the package automatically makes the
        # plugin run for every multiqc invocation, so we need to be forgiving otherwise
        # multiqc will only ever work on run folders.
        # Actually that's not true - we can add a CLI option to enable/disable.

        #I think the idea is to call absolutely everything from the constructor!
        self.yaml_data = dict()
        self.yaml_flat = dict()
        self.load_all_yaml()

        # Add HTML to report.edgen_run so the template can pick it up
        report.edgen_run['metadata1'] = self.yaml_to_html(skip='LaneCount')

        # Add navigation between lanes on the run.
        report.edgen_run['navbar'] = self.make_navbar()

        # Fix the report title to be correct based on the metadata
        config.title = "Run report for " + self.linkify(self.yaml_flat.get('Run ID', '[unknown run]'))
        if self.lane[1] > 1:
            config.title += ' lane {}'.format(self.lane[0])

    def make_navbar(self):
        """Make the navigation between reports for all the lanes on the run.
        """
        # How many lanes are there and which lane is this report for?
        lanes = int(self.yaml_flat.get('LaneCount') or 1)

        # And the lane this report refers to should be passed with the --lane parameter;
        # see cli.py. I think this is how you access the setting...
        lane = int(config.kwargs.get('lane') or 0)

        # As a side effect, set self.lane
        self.lane = [ lane, lanes ]

        if lanes <= 1:
            return '' # No navigation necessary

        res = ['<div id="page_browser"><div id="page_browser_header">',
               '<span id="page_browser_title">{l} lanes on this run</span>'.format(l=lanes),
               '<ul id="page_browser_tabs">']
        for l in reversed(range(1, lanes+1)):
            # Reversed because that's how the CSS layout works.
            if l != lane:
                res.append('<li><a href="multiqc_report_lane{l}.html">{l}</a></li>'.format(l=l))
            else:
                res.append('<li class="active"><a href="multiqc_report_lanel{l}.html">{l}</a></li>'.format(l=l))
        res.append("</ul></div></div>")

        return '\n'.join(res)


    def yaml_to_html(self, keys=None, skip=()):
        """Transform the YAML into HTML as a series of dl/dt/dd elements, though I could also
           use a table here.

           If keys is supplied it must be a list of (printable, yaml_key) pairs.

           TODO - I think we're going to need to break this out into multiple tables.
        """
        if keys is None:
            keys = [ (n, n) for n in sorted(self.yaml_flat.keys()) ]
        keys = [ k for k in keys if k[0] not in skip and k[1] not in skip ]

        res = ['''<div class="well"> <dl class="dl-horizontal" style="margin-bottom:0;">''']

        for pk, yk in keys:
            res.append('''<dt>{}:</dt><dd>{}</dd>'''.format(pk, self.linkify(self.yaml_flat[yk])))

        res.append('''</dl></div>''')

        return '\n'.join(res) + '\n'

    def linkify(self, val):
        """Turns an item from the YAML into a link.
           Hyperlinks are simple.
           File links are trickier.
        """
        if type(val) is not list or len(val) != 2:
            return escape(str(val))

        if val[1] is None:
            return escape(str(val[0]))

        # Normal hyperlink is simple
        if re.match('https?://', val[1]):
            return "<a href='{}'>{}</a>".format(val[1], escape(val[0]))

        # File upload is trickier
        if not os.path.exists(val[1]):
            return "{} (file not found)".format(escape(val[0]))

        # Embed the file
        with open(val[1], "rb") as f:
            return "<a href='data:text/plain;charset=utf-8;base64,{}'>{}</a>".format(
                        base64.b64encode(f.read()).decode('utf-8'),
                        escape(val[0]) )

    def load_all_yaml(self):
        """Finds all files matching run_info.*.yml and loads them in order.
           Get the data into self.yaml_data.
        """
        #FIXME - Am I just looking in the CWD?? Or do I have to explicitly say config.analysis_dir?
        def _getnum(filename):
            #Extract the number from the penultimate part of the filename.
            try:
                return int(filename.split('.')[-2])
            except (ValueError, IndexError):
                return -1

        yamls = sorted( ( y for d in config.analysis_dir
                            for y in glob(d + '/run_info.*.yml') ),
                        key = _getnum )

        for y in yamls:
            with open(y) as yfh:
                log.info("Loading metadata from {}".format(y))
                self.yaml_data.update( yaml.safe_load(yfh) )

        self.yaml_flat = { k: v for d in self.yaml_data.values() for k, v in d.items() }


class edgen_finish():

    def __init__(self):

            log.debug("Running MultiQC_EdGen v{} (finish)".format(__version__))

            #try:

            #...
