#!/usr/bin/env python
"""Test runner script - run this after making changes to verify nothing broke"""
import sys
import unittest

if __name__ == "__main__":
    # Discover and run all tests
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Exit with error code if tests failed
    sys.exit(0 if result.wasSuccessful() else 1)
