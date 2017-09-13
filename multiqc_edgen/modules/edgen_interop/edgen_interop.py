#!/usr/bin/env python3

""" MultiQC module to include interop data"""
from __future__ import print_function, division, absolute_import
import logging
import re, os

import base64
from html import escape as html_escape
from subprocess import call

from multiqc import config
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger, ensuring massages go to the main
# MultiQC modules log.
log = logging.getLogger('multiqc.modules.' + __name__)

class MultiqcModule(BaseMultiqcModule):
    """ InterOP module.

        Note that this module does not find data by sample. Therefore we can't add anything
        to the overview table or participate in the global sample searching and hilighting.
        However, it is useful to use the search function to discover relevant data files
        and so it makes sense for this to be a module and not just a piece of extension
        code.
    """

    def __init__(self):

        super(MultiqcModule, self).__init__(name='InterOP', anchor='interop',
                href='https://github.com/Illumina/interop',
                info='shows selected data from the Illumina InterOP files')

        # Prepare to store any interop_plot files found
        self.interop_plots = dict()
        self.interop_plot_files = dict()


        self.tmp_dir = os.path.join(config.data_tmp_dir, 'edgen_interop')

        for n, f in enumerate(self.find_log_files('edgen_interop', filehandles=True)):
            self.process_interop_plot(n, f)

        # Abort if none found
        log.info("Found {} files".format(len(self.interop_plots)))
        if not self.interop_plots:
            return

        # Write parsed report data to a file (currently this just lists the file names,
        # but it needs to be a dict of dict (normally sample->factor->value)
        self.write_data_file(self.interop_plots, 'edgen_interop')

        # Add the plots to the output of this module.
        for sect in self.interop_plots_html():
            self.add_section(**sect)

    def process_interop_plot(self, n, f):
        """Needs to deal with a .interop_plot file as produced by the interop tools.
           These are all gnuplot command files, and the 'set output' line can be used
           to see what sort of plot it is. Simplistically, we can just run the file
           in GNUPlot and see what output appears.
        """
        # What's the preferred way to make temporary directories within MultiQC?
        tmp_dir = os.path.join(self.tmp_dir, 'plot_{}'.format(n))

        os.makedirs(tmp_dir, exist_ok=False)

        # Now we need to start GNUPlot within the new empty dir and to pipe in the
        # commands.
        # assume gnuplot is in the path
        retcode = call("gnuplot", stdin=f['f'], cwd=tmp_dir)

        if retcode != 0:
            log.warning("GNUPlot returned {}.".format(retcode))

        # See what file was made
        gp_output = os.listdir(tmp_dir)

        if len(gp_output) != 1:
            logger.error("GNUPlot produced no files or unexpected files: {}".format(gp_output))

        # FIXME - title can be better.
        plot_title = plot_file = gp_output[0]

        self.interop_plots[plot_title] = dict(plot_file=plot_file)
        self.interop_plot_files[plot_title] = os.path.join(tmp_dir, plot_file)

    def interop_plots_html(self):
        """Get the plots into the report.
        """
        for ipt, ipf in sorted(self.interop_plot_files.items()):

            # Code adapted from multiqc/plots/linegraph.py
            pid = "".join([c for c in ipt if c.isalpha() or c.isdigit() or c == '_' or c == '-'])
            hidediv = ''

            # Output the figure to a base64 encoded string
            html = ""
            template_mod = config.avail_templates[config.template].load()
            if getattr(template_mod, 'base64_plots', True) is True:
                with open(ipf, "rb") as f:
                    b64_img = base64.b64encode(f.read()).decode('utf8')
                    html = ('<div id="{}"{}><img style="border:none" src="data:image/png;base64,{}" />' +
                             '</div>').format(pid, hidediv, b64_img)

            # Or else move it to a file we want to keep and link <img>
            else:
                plot_relpath = os.path.join(config.data_dir_name, 'multiqc_plots', '{}.png'.format(pid))
                #Not sure about this...
                os.rename(ipf, plot_relpath)
                html = '<div id="{}"{}><img style="border:none" src="{}" /></div>'.format(pid, hidediv, plot_relpath)

            yield dict(name=ipt, plot=html)
