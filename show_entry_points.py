#!/usr/bin/python3
import site, sys
#import pkg_resources - no, must be later or else we could reload it
from pprint import pprint

# This script only shows the entry points set in the directory the
# script is in, clearly by reading
#  *.egg-info/entry_points.txt
# So how come multiqc sees all the entry points under site.USER_SITE?

# Aha - as explained in http://setuptools.readthedocs.io/en/latest/pkg_resources.html,
# the pkg_resources import needs to come after the manipulation of sys.path, even if this
# is done indirectly via site.addsitedir()

# To ensure we see modules in my home dir.
site.addsitedir(site.USER_SITE)

import pkg_resources

# Some code to help me test the entry points are all working.
eps = [ 'multiqc.modules.v1',
        'multiqc.templates.v1',
        'multiqc.cli_options.v1',
        'multiqc.hooks.v1' ]

for ep in eps:
    print("Scanning entry points for {}...".format(ep))
    pprint(list(pkg_resources.iter_entry_points(ep)))
