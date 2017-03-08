#!/usr/bin/env python
"""
MultiQC_EdGen is a plugin for MultiQC, providing additional tools which are
specific to Edinburgh Genomics.

As we seem to need similar things to the NGI plugin I've tried to make
something based on that example.

For more information about Edinburgh Genomics, see http://genomics.ed.ac.uk/
For more information about MultiQC, see http://multiqc.info

To use this, run multiqc -t edgen ...

To install for tinkering and devloping:
env PYTHONPATH="$HOME/.local/lib/python3.4/site-packages" python3 ./setup.py --verbose develop --prefix $HOME/.local
"""

from setuptools import setup, find_packages

version = '0.1'

setup(
    name = 'multiqc_edgen',
    version = version,
    author = 'Tim Booth',
    author_email = 'tim.booth@ed.ac.uk',
    description = "MultiQC plugin for Edinburgh Genomics",
    long_description = __doc__,
    keywords = 'bioinformatics',
    url = 'https://github.com/???',
    download_url = 'https://github.com/???',
    license = 'MIT',
    packages = find_packages(),
    include_package_data = True,
    install_requires = [
        'pyyaml',
        'requests'
    ],
    entry_points = {
        # Extra QC modules that digest report files.
        'multiqc.modules.v1': [
            'edgen_foo = multiqc_edgen.modules.edgen_foo:MultiqcModule',
        ],
        # Template that has our branding and space for the meta-data to appear.
        'multiqc.templates.v1': [
            'edgen = multiqc_edgen.templates.edgen',
        ],
        # Extra CLI options. Do we need em?
        'multiqc.cli_options.v1': [
            'enable = multiqc_edgen.cli:enable_edgen',
            'run_id = multiqc_edgen.cli:run_id',
        ],
        # Hooks.
        'multiqc.hooks.v1': [
            'before_report_generation = multiqc_edgen.multiqc_edgen:edgen_before_report',
            'execution_finish = multiqc_edgen.multiqc_edgen:edgen_finish'
        ]
    },
    classifiers = [
        'Development Status :: 7 - Uber',
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Operating System :: MacOS :: MacOS X',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Programming Language :: Python',
        'Programming Language :: JavaScript',
        'Topic :: Scientific/Engineering',
        'Topic :: Scientific/Engineering :: Bio-Informatics',
        'Topic :: Scientific/Engineering :: Visualization',
    ],
)

