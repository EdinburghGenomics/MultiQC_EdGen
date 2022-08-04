#!/usr/bin/env python
"""
MultiQC_EdGen is a plugin for MultiQC, providing additional tools which are
specific to Edinburgh Genomics.

As we seem to need similar things to the NGI plugin I've tried to make
something based on that example.

For more information about Edinburgh Genomics, see http://genomics.ed.ac.uk/
For more information about MultiQC, see http://multiqc.info

To use this, run multiqc -t edgen ...

To install for tinkering and developing:
$ env PYTHONPATH="`python3 -m site --user-site`" python3 ./setup.py --verbose develop --prefix "`python3 -m site --user-base`"
"""

from setuptools import setup, find_packages

version = '1.4.1'

setup(
    name = 'multiqc_edgen',
    version = version,
    author = 'Tim Booth',
    author_email = 'tim.booth@ed.ac.uk',
    description = "MultiQC plugin for Edinburgh Genomics",
    long_description = __doc__,
    keywords = 'bioinformatics',
    url = 'http://gitlab.genepool.private/production-team/MultiQC_EdGen',
    download_url = 'http://gitlab.genepool.private/production-team/MultiQC_EdGen',
    license = 'MIT',
    packages = find_packages(),
    include_package_data = True,
    package_data = { '': ['utils/*.yaml', '*.html',
                          'templates/*/assets/img/*.*',
                          'templates/*/assets/js/*.*',
                          'templates/*/assets/js/packages/*.*',
                          'templates/*/assets/css/*.*' ] },
    install_requires = [
        'pyyaml',
        'yamlloader',
    ],
    entry_points = {
        # Extra QC modules that digest report files.
        'multiqc.modules.v1': [
            'edgen_interop  = multiqc_edgen.modules.edgen_interop:MultiqcModule',
            'edgen_cutadapt = multiqc_edgen.modules.edgen_cutadapt:MultiqcModule',
            'edgen_unassigned = multiqc_edgen.modules.edgen_unassigned:MultiqcModule',
            'edgen_fastqc_original = multiqc_edgen.modules.edgen_fastqc_original:MultiqcModule',
        ],
        # Template that has our branding and space for the meta-data to appear.
        'multiqc.templates.v1': [
            'edgen = multiqc_edgen.templates.edgen',
        ],
        # Extra CLI options. Do we need em?
        'multiqc.cli_options.v1': [
            'enable = multiqc_edgen.cli:enable_edgen',
            'run_id = multiqc_edgen.cli:run_id',
            'lane   = multiqc_edgen.cli:lane',
            'pipeline_status = multiqc_edgen.cli:pipeline_status',
        ],
        # Hooks.
        'multiqc.hooks.v1': [
            'before_modules = multiqc_edgen.multiqc_edgen:edgen_before_modules',
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

