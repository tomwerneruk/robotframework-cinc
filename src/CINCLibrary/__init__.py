"""Top-level package for cinc Robot Framework Library."""
__author__ = 'Tom Werner'
__email__ = 'tom@fluffycloudsandlines.cc'
__version__ = '0.1.0'

import subprocess
import logging
import json
from robot.api.deco import keyword, library
from robot.running.model import TestSuite
from robot.model.body import BodyItem


@library(scope='TEST SUITE', version=__version__)
class CINCLibrary(object):
    
    def __init__(self):
        """Intiliase CINC Auditor Library

        Init our library to be a robot listener, using the v2 API.
        This allows hooking into the execution lifecycle of a Test Suite to 
        dynamically add cinc controls into the suite as test cases.
        
        """
        self.ROBOT_LIBRARY_LISTENER = self
        self.ROBOT_LISTENER_API_VERSION = 3
        self.current_suite = None

    def start_suite(self, suite, result):
        """Start Suite Hook

        Listener API Hook, invoked when the suite starts. 
        Save the suite reference so that we can append tests to the handle.
        
        """
        self.current_suite = suite
    
    @keyword("Validate cinc Profile")
    def validate_profile(self, profile, auditor_executable='cinc-auditor'):
        """Validate CINC Profile

        Run the auditor tool to parse the provided profile to allow us to fail quick. Parse the number of controls for logging purposes.

        :param str cinc-auditor: Optional over-ride of the executable name, incase the upstream tool (or other whitelabel) is being used instead.
        :param str profile: Path to the profile to be exeucted.
        :raise: AssertionError if the profile is invalid

        """
        # Run `cinc-auditor json`` which parses the profile and provides
        # a list of controls to then create dynamic test cases for
        cinc_validate_execution = subprocess.run([auditor_executable, "json", profile], capture_output=True)
        if cinc_validate_execution.returncode == 0:
            cinc_validation_result = json.loads(cinc_validate_execution.stdout)
            logging.info("Found {0} controls in {1}".format(len(cinc_validation_result["controls"]), profile))
            return True
        else:
            raise AssertionError("Non zero return from cinc validate ... [{0}]. {1}".format(
                    cinc_validate_execution.returncode, 
                    cinc_validate_execution.stdout
                ))

    @keyword("Execute cinc Profile")
    def exec_profile(self, profile, auditor_executable='cinc-auditor', backend="local"):
        cinc_execution = subprocess.run([auditor_executable, "exec", profile, "--reporter", "json"], capture_output=True)
        if cinc_execution.returncode in (0,100,101):
            cinc_execution_json = json.loads(cinc_execution.stdout)
            logging.debug(json.dumps(cinc_execution_json))
            for control in cinc_execution_json["profiles"][0]["controls"]:
                tc = self.current_suite.tests.create(name="cinc Control - [ {0} ]".format(control['title']))
                tc.body.create_keyword(name="Process cinc Control Result", args=[control])    
        else:
            logging.info(cinc_execution.returncode)
            logging.info(cinc_execution.stdout)

    @keyword("Process cinc Control Result")
    def process_cinc_control_result(self, control_json):
        logging.debug(control_json)
        for result in control_json['results']:
            if result['status'] != 'passed':
                raise AssertionError("Failed")

globals()[__name__] = CINCLibrary