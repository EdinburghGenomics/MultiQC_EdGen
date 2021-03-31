#!/usr/bin/env python
from __future__ import print_function, division, absolute_import
""" MultiQC hook functions - we tie into the MultiQC
core here to add in extra functionality and logic for EdGen run reports. """

from collections import OrderedDict
import logging
import os, sys, re
from glob import glob
import yaml, yamlloader
from base64 import b64encode
from cgi import escape
from datetime import datetime

from pkg_resources import get_distribution
__version__ = get_distribution("multiqc_edgen").version

import multiqc # import before getting logger
from multiqc.utils import report, config

log = logging.getLogger('multiqc')

#Container for the meta-data etc. Add keys that match things in the HTML template(s).
report.edgen_run = dict()

class edgen_before_modules():
    """Blacklist some modules so that replacement ones can be provided
       by this plugin.
    """
    def __init__(self):
        self.blacklist_modules()

    def blacklist_modules(self):

        blacklist = ['cutadapt', 'vcftools', 'rsem']

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
        self.yaml_data = OrderedDict()
        self.yaml_flat = OrderedDict()

        self.pipeline_status = config.kwargs.get('pipeline_status')
        if self.pipeline_status:
            self.yaml_data['Pipeline Status'] = {'Pipeline Status': self.pipeline_status}

            # This was requested too, though it's a bit hacky.
            if self.pipeline_status == "Completed QC":
                self.yaml_data['Pipeline Status']['t4//Pipeline Completed'] = datetime.now().ctime()

        self.load_all_yaml()

        # Add HTML to report.edgen_run so the template can pick it up
        report.edgen_run['metadata1'] = self.yaml_to_html(skip='LaneCount')

        # How many lanes are there in this run? And which are we reporting on?
        self.lanes = int(self.yaml_flat.get('LaneCount') or 0)
        self.set_lane()

        # Fix the report title to be correct based on the metadata
        self.run_id = config.kwargs.get('rid') or self.yaml_flat.get('Run ID', '[unknown run]')
        config.title = "Run report for " + self.linkify(self.run_id)
        if self.lane:
            config.title += ' lane&nbsp;{}'.format(self.lane)

        # Add navigation between lanes on the run.
        report.edgen_run['navbar'] = self.make_navbar()

        #Slightly different title for the <title> tag
        config.ptitle = self.textify(self.run_id) + ( ' lane {}'.format(self.lane) if self.lane else  ' run report' )

    def set_lane(self):
        """Work out what lane we're reporting on, if any.
           Lane 0 is the overview report and the default if no lane is set.
        """
        lane_str = config.kwargs.get('lane') or '0'

        if lane_str.startswith('lane'):
            self.lane = int(lane_str[4:])
        elif lane_str[0] in '123456789':
            self.lane = int(lane_str)
        else:
            self.lane = 0

        return self.lane

    def make_navbar(self):
        """Make the navigation between reports for all the lanes on the run.
        """
        # The specific lane this report refers to should be passed with the --lane parameter;
        # see cli.py.
        # self.lanes should be set already from the yml
        # self.lane should be set by the caller too

        # This was true until we added the separate overview. Maybe we can still have a single report
        # for single-lane machines? (No, that's not desirable.)
        #if lanes <= 1:
        #    return '' # No navigation necessary

        # If this is the overview and we're not demultiplexed, suppress the other links
        # FIXME - this is all a bit hacky - we should really have an explicit list of lanes
        # for which there are reports to see.
        page_browser_class = 'page_browser_full'
        if (not self.lane) and (not 'post_demux_info' in self.yaml_data):
            page_browser_class = 'page_browser_overview'

        res = ['<div id="page_browser" class="{}" runid="{}">'.format(page_browser_class, self.run_id),
               '<div id="page_browser_header">',
               '<span id="page_browser_title">{l} lanes on this run</span>'.format(l=self.lanes),
               '<ul id="page_browser_tabs">']
        for l in reversed( range(self.lanes+1) ):
            # Reversed because that's how the CSS layout works.
            llabel = l if l else 'Overview'
            llink = 'lane{}'.format(l) if l else 'overview'

            lactive = 'class="active"' if l == self.lane else ''
            res.append(('<li id="nav_tab_{llink}" {lactive}>' + \
                        '<a href="multiqc_report_{llink}.html">{llabel}</a></li>').format(**locals()))

        res.append('</ul></div>')
        res.append('<div id="page_browser_lui" style="display: none">Status and <button>button</button></div>')
        res.append('</div>')

        return '\n'.join(res)


    def yaml_to_html(self, keys=None, skip=()):
        """Transform the metadata into HTML as a series of dl/dt/dd elements, though I could also
           use a table here.

           If keys is supplied it must be a list of (printable, yaml_key) pairs.

           TODO - I think we're going to need to break this out into multiple tables or summat.
                  For now I'm just using yaml_flat, which has already been sorted for me.
        """
        if keys is None:
            keys = [ (n, n) for n in self.yaml_flat.keys() ]

        # Key names may be in the form x//y in which case order on x and use y as the label,
        # overriding any previous ordering and structuring.
        keys = [ (y, k) for ((x, y), k) in [ (xy.split('//', 1), k) for xy, k in keys if '//' in xy ] if x <  'n0' ] + \
               [ (y, k) for y, k in keys if '//' not in y ] + \
               [ (y, k) for ((x, y), k) in [ (xy.split('//', 1), k) for xy, k in keys if '//' in xy ] if x >= 'n0' ]

        keys = [ k for k in keys if k[0] not in skip and k[1] not in skip ]

        res = ['''<div class="well"> <dl class="dl-horizontal" style="margin-bottom:0;">''']

        for pk, yk in keys:
            res.append('''<dt>{}:</dt><dd>{}</dd>'''.format(pk, self.linkify(self.yaml_flat[yk])))

        res.append('''</dl></div>''')

        return '\n'.join(res) + '\n'

    def linkify(self, val):
        """Turns an item [label, link] from the YAML into a link.
           Hyperlinks are simple.
           File links are trickier.
        """
        if type(val) is not list or len(val) != 2:
            return escape(str(val))

        if val[1] is None:
            # So there is no link
            return escape(str(val[0]))

        # See if the label has [brackets]
        mo = re.match(r'(.*)\[(.*)\](.*)', val[0])
        if mo:
            label_bits = [ escape(p) for p in mo.groups() ]
        else:
            label_bits = [ '', escape(val[0]), '' ]

        # Normal hyperlink is simple
        if re.match('https?://', val[1]):
            return "{lb[0]}<a href='{link}'>{lb[1]}</a>{lb[2]}".format(lb=label_bits, link=val[1])

        # File upload is trickier, partly due to:
        #  https://groups.google.com/a/chromium.org/forum/#!topic/blink-dev/GbVcuwg_QjM%5B1-25%5D
        if not os.path.exists(val[1]):
            return "{} (file not found)".format(escape(val[0]))
        else:
            # Make a fake extension to keep Windows happy
            fake_extn = '.csv' if '.csv.' in val[0] else ''
            # Embed the file
            with open(val[1], "rb") as f:
                fdata = "data:text/plain;charset=utf-8;base64," + b64encode(f.read()).decode('utf-8')
                return "{lb[0]}<a download='{lb[1]}{extn}' target='_blank' href='{fdata}'>{lb[1]}</a>{lb[2]}".format(
                            lb = label_bits,
                            extn = fake_extn,
                            fdata = fdata )

    def textify(self, val):
        """Like linkify, but just gets the text, ensuring it's quoted properly
        """
        if type(val) is not list or len(val) != 2:
            return escape(str(val))

        return escape(str(val[0]))

    def load_all_yaml(self):
        """Finds all files matching run_info.*.yml and loads them in order.
           Get the data into self.yaml_data.
        """
        # TODO - am I just looking in the CWD?? Or do I really have to explicitly say config.analysis_dir?
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
                # The point of this is to allow new sections to replace old ones,
                # including removing keys.
                self.yaml_data.update( yaml.load(yfh, Loader=yamlloader.ordereddict.CSafeLoader) )

        for sk, sv in self.yaml_data.items():
            self.yaml_flat.update(sv.items())


class edgen_finish():

    def __init__(self):

            log.debug("Running MultiQC_EdGen v{} (finish)".format(__version__))

            #try:

            #...
