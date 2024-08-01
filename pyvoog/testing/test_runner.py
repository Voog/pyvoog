import argparse
import sys
import unittest

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from attrs import define
from sqlalchemy import MetaData

from pyvoog.db import setup_database

@define
class TestRunner:

    """ A high-level test runner class for quick bootstrapping of a test
    runner script. Provides argument handling (e.g. `--filter` and `--
    verbose`; use `--help` for a synopsis), test case filtering and
    discovery, running and reporting results from test suites.

    Attributes, all optional:

    - db_url - Test database URL.
    - alembic_config_fn - Alembic configuration file name. If passed, the
      database is checked to be fully migrated.
    - env_env_var - The env var name for specifying the application.
      environment. Only used for the migration error message for now.
    - test_dir - The directory containing test suites.
    """

    db_url: str = None
    env_env_var: str = None
    alembic_config_fn: str = None
    test_dir: str = "./lib/test"

    def run(self):
        args = self._parse_command_line()

        if self.db_url:
            engine = setup_database(self.db_url)

            if self.alembic_config_fn:
                self._check_test_database(engine)

            self._truncate_test_database(engine)

        self._run(filter_string=args.filter, verbose=args.verbose)

    def _run(self, filter_string=None, verbose=True):
        suite = unittest.defaultTestLoader.discover(self.test_dir, pattern="test_*.py")

        if errors := unittest.defaultTestLoader.errors:
            print(errors[0], file=sys.stderr)

            raise SystemExit(2)

        suite = self._filter_suite(suite, filter_string)
        runner = unittest.TextTestRunner(verbosity=(2 if verbose else 1))
        exit_value = 0 if runner.run(suite).wasSuccessful() else 1

        raise SystemExit(exit_value)

    def _filter_suite(self, suite, filter_str):
        filtered_suite = unittest.TestSuite()
        test_cases = self._get_test_cases(suite)

        for test_case in test_cases:
            nonrunnable = type(test_case).__dict__.get("NONRUNNABLE_BASE_CLASS", False)

            if (not filter_str or filter_str in test_case.id()) and not nonrunnable:
                filtered_suite.addTest(test_case)

        return filtered_suite

    def _get_test_cases(self, suite):

        """ Get TestCases of a TestSuite recursively, in effect flattening the
        structure.
        """

        test_cases = []

        for item in suite:
            if isinstance(item, unittest.TestSuite):
                test_cases += self._get_test_cases(item)
            elif isinstance(item, unittest.TestCase):
                test_cases.append(item)
            else:
                raise TypeError(
                    "Encountered a bad TestSuite member ({})".format(type(item).__name__))

        return test_cases

    def _check_test_database(self, engine):

        """ Bail out if the test database does not exist or is not fully
        migrated.
        """

        alembic_cfg = AlembicConfig(self.alembic_config_fn)
        connection = engine.connect()
        current_head = ScriptDirectory.from_config(alembic_cfg).get_current_head()

        try:
            current_revision = MigrationContext.configure(connection).get_current_revision()
        finally:
            connection.close()

        if current_head != current_revision:
            instructions = ""

            if self.env_env_var:
                instructions = (
                    "\n\nRun:\n\n"
                    f"{self.env_env_var}=\"test\" alembic --config alembic/alembic.ini upgrade head"
                )

            self._err(
                "Test database not accessible or not fully migrated "
                f"(head {current_head} vs revision {current_revision}){instructions}"
            )

    def _truncate_test_database(self, engine):

        """ Truncate all test database tables (except alembic_version). """

        metadata = MetaData()
        connection = engine.connect()
        transaction = connection.begin()

        metadata.reflect(bind=engine)

        for table in metadata.sorted_tables:
            if table.name == "alembic_version":
                continue

            connection.execute(table.delete())

        transaction.commit()
        connection.close()

    def _parse_command_line(self):
        parser = argparse.ArgumentParser(description="Run tests")

        parser.add_argument(
            "-f", "--filter", type=str,
            help="Only run tests whose fully qualified name contains the given string"
        )
        parser.add_argument(
            "-v", "--verbose", default=False, action="store_true",
            help="Increase verbosity"
        )

        return parser.parse_args()

    @staticmethod
    def _err(*args):
        print("ERROR:", *args, file=sys.stderr)
        raise SystemExit(2)
