#!/usr/bin/env python

""" Stub MultiQC module for Edinburgh Genomics Run QC """

from __future__ import print_function, absolute_import, division
from collections import OrderedDict
import logging

from multiqc import config
from multiqc.modules.base_module import BaseMultiqcModule

# Initialise the logger
log = logging.getLogger('multiqc.modules.ngi_rnaseq')

class MultiqcModule(BaseMultiqcModule):

    def __init__(self):

        # Initialise the parent object
        super(MultiqcModule, self).__init__(name='EdGenModule', anchor='edgen_foo',
                                            href="https://genomics.ed.ac.uk",
                                            info=" is a stub module just now.")

        # Set up class objects to hold parsed data
        self.sections = list()
        self.general_stats_headers = OrderedDict()
        self.general_stats_data = dict()
        n = dict()

        # And then do nothing
        pass
