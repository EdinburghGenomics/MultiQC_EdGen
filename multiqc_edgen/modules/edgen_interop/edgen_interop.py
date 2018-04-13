#!/usr/bin/env python3

""" MultiQC module to include interop data"""
from __future__ import print_function, division, absolute_import
import logging
import re, os

import base64
from html import escape as html_escape
from subprocess import Popen, PIPE, DEVNULL

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
            if f.get('fn','').startswith('flowcell_all'):
                # Special handling for these
                self.process_flowcell_all_plot(n, f)
            else:
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

    def process_flowcell_all_plot(self, plotnum, f):
        """Deals with the multi-plot files found in flowcell_all.interop_plot,
           where I've run interop_plot_flowcell --filter-by-cycle=N in a loop
           over all cycles.
        """
        tmp_dir = os.path.join(self.tmp_dir, 'iplot_{}'.format(plotnum))
        os.makedirs(tmp_dir, exist_ok=False)

        # Start GNUPlot within the new empty dir and to pipe in the commands
        # to make a bunch of files.
        # We can assume gnuplot is in the path (it should be in the TOOLBOX)
        def munger(ifh):
            width = 800
            height = 450
            cycle = 0
            title_match = re.compile(r'set title "(.*)"')
            for line in ifh:
                # Bump the cycle counter when we see a header line, Note there is a rogue
                # header on the end so don't rely on this to count the frames.
                # Fortunately running gnuplot on an empty command list is fine.
                if line.startswith('# Version'):
                    if cycle: yield None
                    cycle += 1
                # Fix the colour scale so all the plots are comparable
                # Do we want this? No, Tony says please keep the variable range per-cycle.
                #if line.startswith('set cbrange'):
                #    line = "set cbrange [50:300]\n"
                # Fudge the image size.
                if line.startswith('set terminal'):
                    line = "set terminal pngcairo size {},{} enhanced font 'sans,10'\n".format(width, height)
                # Fudge the file name
                if line.startswith('set output'):
                    assert cycle
                    line = "set output 'flowcell_all_cycle_{:04}.png'\n".format(cycle)
                # Fudge the title
                mo = re.match(title_match, line)
                if mo:
                    line = 'set title "{} Cycle {:03}"\n'.format(mo.group(1), cycle)

                yield line

        # Annoyingly I can't see how to get GNUPlot to output multiple plots in one call.
        # Answers on a postcard, please? In the meantime...
        eof = False
        munged_lines = munger(f['f']) # Returns a iterator, not a list.
        while not eof:
            with Popen( "gnuplot",
                        stdin = PIPE,
                        stderr = DEVNULL,
                        cwd = tmp_dir,
                        bufsize = 1,
                        universal_newlines = True) as gnuplot_process:

                for line in munged_lines:
                    if line is None:
                        break # Drops out to return code check
                    else:
                        print(line, file=gnuplot_process.stdin, end='')
                else:
                    # This only happens when we really run out of lines
                    eof = True


            if gnuplot_process.returncode != 0:
                log.warning("GNUPlot returned {}.".format(gnuplot_process.returncode))

        # See what files was made
        gp_output = os.listdir(tmp_dir)
        log.debug(repr(gp_output))

        if not gp_output:
            log.error("GNUPlot produced no files.")
        if any(not re.match(r'^flowcell_all_cycle_\d\d\d\d.png$', f) for f in gp_output):
            log.error("GNUPlot produced unexpected files not matching the expected name.")

        # Turn these plots into an APNG using apngasm. This program has funky syntax but
        # here it works well. Note that for our purposes I need the fudged version that
        # disables inter-frame optimisation.
        apngasm_process = Popen( ["apngasm-noopt", "flowcell_all.apng", "flowcell_all_cycle_0001.png", "-kp", "-kc"],
                                 stdout = DEVNULL,
                                 cwd = tmp_dir )
        apngasm_process.communicate()
        if apngasm_process.returncode != 0:
            log.warning("apngasm-noopt returned {}.".format(apngasm_process.returncode))

        # FIXME - title can maybe be better. For now, here's some string munging
        plot_file = "flowcell_all.apng"
        plot_title = "Flowcell Intensity all Cycles"

        self.interop_plots[plot_title] = dict(plot_file=plot_file)
        self.interop_plot_files[plot_title] = os.path.join(tmp_dir, plot_file)

        # Need to indicate to the report that APNG should be included in the template.
        # How to do this?
        # The hacky way, of course:
        from multiqc.utils import report
        report.edgen_run['include_apng'] = True

    def process_interop_plot(self, plotnum, f):
        """Needs to deal with a .interop_plot file as produced by the interop tools.
           These are all gnuplot command files, and the 'set output' line can be used
           to see what sort of plot it is. Simplistically, we can just run the file
           in GNUPlot and see what output appears.
           plotnum needs to be a counter over the plots
           f is a MultiQC file object with a handle (f['f']) and a name (f['fn'])
        """
        # What's the preferred way to make temporary directories within MultiQC?
        tmp_dir = os.path.join(self.tmp_dir, 'iplot_{}'.format(plotnum))

        os.makedirs(tmp_dir, exist_ok=False)

        # Now we need to start GNUPlot within the new empty dir and to pipe in the
        # commands.
        # assume gnuplot is in the path

        def munger(ifh, fn=''):
            # Heat maps want to be wider to align with line graphs
            width = 890 if 'heatmap' in fn else 800
            height = 450
            for line in ifh:
                if line.startswith('set terminal'):
                    line = "set terminal pngcairo size {},{} enhanced font 'sans,10'\n".format(width, height)
                yield line

        with Popen( "gnuplot",
                    stdin = PIPE,
                    stderr = DEVNULL,
                    cwd = tmp_dir,
                    bufsize = 1,
                    universal_newlines = True) as gnuplot_process:

            for line in munger(f['f'], f['fn']):
                print(line, file=gnuplot_process.stdin, end='')

        # Accessing gnuplot_process outside the context manager looks weird but it
        # is correct.
        retcode = gnuplot_process.returncode

        if retcode != 0:
            log.warning("GNUPlot returned {}.".format(retcode))

        # See what file was made
        gp_output = os.listdir(tmp_dir)

        if len(gp_output) != 1:
            log.error("GNUPlot produced no files or unexpected files: {}".format(gp_output))

        # FIXME - title can maybe be better. For now, here's some string munging
        plot_file = gp_output[0]
        plot_title = ' '.join([ w.capitalize() for n in plot_file.split('_') if '-' in n for w in n.split('-') ]).split('.')[0]

        self.interop_plots[plot_title] = dict(plot_file=plot_file)
        self.interop_plot_files[plot_title] = os.path.join(tmp_dir, plot_file)

    def interop_plots_html(self):
        """ Get the plots into the report. Sort order is by title.
        """
        for ipt, ipf in sorted(self.interop_plot_files.items()):

            # Code adapted from multiqc/plots/linegraph.py
            pid = "".join([c for c in ipt if c.isalpha() or c.isdigit() or c == '_' or c == '-'])
            hidediv = ''
            file_extn = ipf.split('.')[-1]

            # Output the figure to a base64 encoded string
            html = ""
            template_mod = config.avail_templates[config.template].load()
            if getattr(template_mod, 'base64_plots', True) is True:
                with open(ipf, "rb") as f:
                    b64_img = base64.b64encode(f.read()).decode('utf8')

                    if file_extn == 'apng':
                        # FIXME - If more apng options are added I'll need to make slider_label and zero_image dynamic.
                        html = (('<div id="{}" class="apng_slider" slider_label="Show cycle"' + \
                                 'zero_image="" apng_data="{}"{}></div>').format(pid, b64_img,  hidediv))
                    else:
                        html = ('<div id="{}"{}><img style="border:none" src="data:image/png;base64,{}" />' +
                                 '</div>').format(pid, hidediv, b64_img)

            # Or else move it to a file we want to keep and link <img>
            else:
                plot_savpath = os.path.join(config.data_dir, 'multiqc_plots', '{}.{}'.format(pid, file_extn))
                plot_relpath = os.path.join(config.data_dir_name, 'multiqc_plots', '{}.{}'.format(pid, file_extn))
                #Not sure about this...
                os.rename(ipf, plot_savpath)
                html = '<div id="{}"{}><img style="border:none" src="{}" /></div>'.format(pid, hidediv, plot_relpath)

            yield dict(name=ipt, plot=html)
