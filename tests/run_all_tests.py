"""
Testing guide for crypto-trigger.

The test suite is organized by modules for clarity and maintainability.
"""

import unittest

if __name__ == "__main__":
    # Discover and run all tests from the tests directory
    loader = unittest.TestLoader()
    suite = loader.discover("tests", pattern="test_*.py")
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    exit(0 if result.wasSuccessful() else 1)
