# -*- coding: utf-8 -*-
"""
Alle Tests der Dateien test_*.py durchführen

Alle Laufzeit Fehlermeldungen sind bei der Testausführung gewollt 

Nach der Ausführung steht am Ende OK wenn alle Tests durchgefürt wurden.

Bei Fehlern in den Überprüfungen steht am Ende::
 
    ======================================================================  
    FAIL:
        .......
    
    FAILED (failures=x)

"""

from os import path as osp

import site

# alle Module auch von der Konsole erreichbar machen 
ABSPATH = osp.dirname( osp.abspath( __file__) )
BASEPATH = osp.join( ABSPATH , "..")
FILESPATH = osp.join( BASEPATH, 'data', 'tests') 

site.addsitedir(BASEPATH)


# Coverage am Anfang initialisieren damit alles berücksichtigt wird
all_cov = None
import coverage
    
# ausschalten wenn coverage nicht durchgeführt werden soll 
runCoverage = True

if runCoverage:
    all_cov = coverage.Coverage( )
    
    all_cov.config.set_option("run:relative_files", True)
    all_cov.config.set_option("run:omit", [
        "*/ui/*", 
        "*/docs/*",
        "*/.docs/*",
        "*/.htmlcov/*",
        "*/tests/*",
        "*/files/*"
    ])
    
    # Regexes for lines to exclude from consideration
    options = [
       "pragma: no cover",
       "if 0:",
       "if __name__ == .__main__.:"
    ]
    all_cov.config.set_option("report:exclude_lines", options)
    all_cov.config.set_option("html:directory", osp.join( BASEPATH, ".htmlcov" ) )
    all_cov.config.set_option("html:extra_css", osp.join( ABSPATH, "resources", "coverage.css" ) )

    all_cov.start()


import unittest

# -----------------------------------------------------------------------------    
if __name__ == '__main__':

    '''
    0 (quiet): you just get the total numbers of tests executed and the global result
    1 (default): you get the same plus a dot for every successful test or a F for every failure
    2 (verbose): you get the help string of every test and the result
    '''
 
    loader = unittest.TestLoader()
    test_suite = loader.discover( ABSPATH, pattern='test_*.py' )
    
    testRunner = unittest.runner.TextTestRunner()
    testRunner.run(test_suite)

    
    if all_cov:
        all_cov.stop()
        all_cov.save()
        
        all_cov.html_report()