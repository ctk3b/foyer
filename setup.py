"""Foyer: A package for atom-typing as well as applying and disseminating forcefields

"""

from __future__ import print_function

import os
import subprocess
from setuptools import setup, find_packages

#####################################
VERSION = "0.2.0"
ISRELEASED = False
if ISRELEASED:
    __version__ = VERSION
else:
    __version__ = VERSION + '.dev0'
#####################################


def git_version():
    # Return the git revision as a string
    # copied from numpy setup.py
    def _minimal_ext_cmd(cmd):
        # construct minimal environment
        env = {}
        for k in ['SYSTEMROOT', 'PATH']:
            v = os.environ.get(k)
            if v is not None:
                env[k] = v
        # LANGUAGE is used on win32
        env['LANGUAGE'] = 'C'
        env['LANG'] = 'C'
        env['LC_ALL'] = 'C'
        out = subprocess.Popen(
            cmd, stdout=subprocess.PIPE, env=env).communicate()[0]
        return out

    try:
        out = _minimal_ext_cmd(['git', 'rev-parse', 'HEAD'])
        GIT_REVISION = out.strip().decode('ascii')
    except OSError:
        GIT_REVISION = 'Unknown'

    return GIT_REVISION


def write_version_py(version, isreleased, filename):
    cnt = """
# This file is generated in setup.py at build time.
version = '{version}'
short_version = '{short_version}'
full_version = '{full_version}'
git_revision = '{git_revision}'
release = {release}
"""
    # git_revision
    if os.path.exists('.git'):
        git_revision = git_version()
    else:
        git_revision = 'Unknown'

    # short_version, full_version
    if isreleased:
        full_version = version
        short_version = version
    else:
        full_version = ("{version}+{git_revision}"
                        .format(version=version, git_revision=git_revision))
        short_version = version

    with open(filename, 'w') as f:
        f.write(cnt.format(version=version,
                           short_version=short_version,
                           full_version=full_version,
                           git_revision=git_revision,
                           release=isreleased))

write_version_py(VERSION, ISRELEASED, 'foyer/version.py')

setup(
    name='foyer',
    version=__version__,
    description=__doc__.split('\n')[0],
    long_description=__doc__,
    author='Janos Sallai, Christoph Klein',
    author_email='janos.sallai@vanderbilt.edu, christoph.klein@vanderbilt.edu',
    url='https://github.com/mosdef-hub/foyer',
    download_url='https://github.com/mosdef-hub/foyer/tarball/{}'.format(__version__),
    packages=find_packages(),
    package_data={'foyer': ['tests/*.txt',
                            '../opls_validation/*.top',
                            '../opls_validation/*.gro',
                            '../opls_validation/oplsaa.ff/*',
                            ]},
    package_dir={'foyer': 'foyer'},
    include_package_data=True,
    license="MIT",
    zip_safe=False,
    keywords='foyer',
    classifiers=[
        'Development Status :: 4 - Beta',
        'Intended Audience :: Science/Research',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Topic :: Scientific/Engineering :: Chemistry',
        'Operating System :: Microsoft :: Windows',
        'Operating System :: POSIX',
        'Operating System :: Unix',
        'Operating System :: MacOS',
    ],
)
