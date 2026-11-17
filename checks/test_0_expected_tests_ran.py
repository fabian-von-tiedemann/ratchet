"""The comparison of ratchet.expected-tests-ran, collected by discover before every other module.

    python3 -m unittest discover -s checks -v

Discover loads the modules of a directory in the order of their names, and this name
sorts first. Its load_tests gives one suite that holds no test. When the run reaches it,
it hooks the comparison into the run's result, so the comparison runs when the run
stops, whatever happens to the tests that load fixtures. See checks/expected_tests.py.
Standard library only.
"""

from expected_tests import load_tests_hook

load_tests = load_tests_hook()
