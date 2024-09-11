import argparse
import logging
import random
import re
import sys
import unittest

from typing import Callable

from alembic.config import Config as AlembicConfig
from alembic.script import ScriptDirectory
from alembic.migration import MigrationContext
from attrs import define
from sqlalchemy import MetaData

from pyvoog.app import Application
from pyvoog.db import setup_database
from pyvoog.logging import setup_logging
from pyvoog.testing.signals import app_ctx_pushed

@define
class TestRunner:

    """ A high-level test runner class for quick bootstrapping of a test
    runner script. Provides argument handling (e.g. `--filter` and `--
    verbose`; use `--help` for a synopsis), test case filtering and
    discovery, running and reporting results from test suites.

    Attributes, all optional:

    - alembic_config_fn - Alembic configuration file name. If passed, the
      database is checked to be fully migrated.
    - app - Instance of the application under test. If passed, its `testing`
      flag will be set to True and it will be passed on to every TestCase as
      its `app` attribute.
    - db_url - Test database URL.
    - env_env_var - The env var name for specifying the application.
      environment. Only used for the migration error message for now.
    - on_app_ctx_push - A callable invoked upon pushing a test app context.
      Initialize any app context variables in the provided callback.
    - test_dir - The directory containing test suites.
    """

    alembic_config_fn: str = None
    app: Application = None
    db_url: str = None
    env_env_var: str = None
    on_app_ctx_push: Callable = None
    test_dir: str = "./lib/test"

    def run(self):
        args = self._parse_command_line()

        if self.db_url:
            engine = setup_database(self.db_url)

            if self.alembic_config_fn:
                self._check_test_database(engine)

            self._truncate_test_database(engine)

        if self.app:
            self.app.testing = True

        if args.loglevel:
            setup_logging(args.loglevel, args.extra_loglevel)
        else:
            logging.disable()

        if self.on_app_ctx_push:
            receiver = lambda _, **kwargs: self.on_app_ctx_push(**kwargs)
            app_ctx_pushed.connect(receiver)

        self._init_rng(args.random_seed)
        self._run(filter_regex=args.filter, verbose=args.verbose)

    def _run(self, filter_regex=None, verbose=True):
        suite = unittest.defaultTestLoader.discover(self.test_dir, pattern="test_*.py")

        if errors := unittest.defaultTestLoader.errors:
            print(errors[0], file=sys.stderr)

            raise SystemExit(2)

        suite = self._filter_suite(suite, filter_regex)
        runner = unittest.TextTestRunner(verbosity=(2 if verbose else 1))
        exit_value = 0 if runner.run(suite).wasSuccessful() else 1

        raise SystemExit(exit_value)

    def _filter_suite(self, suite, filter_regex):
        filtered_suite = unittest.TestSuite()
        test_cases = self._get_test_cases(suite)
        pattern = re.compile(filter_regex) if filter_regex else None

        for test_case in test_cases:
            nonrunnable = type(test_case).__dict__.get("NONRUNNABLE_BASE_CLASS", False)

            if (not pattern or (pattern.search(test_case.id()) is not None)) and not nonrunnable:
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
                self._set_test_case_ctx(item)
                test_cases.append(item)
            else:
                raise TypeError(
                    "Encountered a bad TestSuite member ({})".format(type(item).__name__))

        random.shuffle(test_cases)

        return test_cases

    def _set_test_case_ctx(self, test_case):

        """ Pass on some context to each test case, only the current app
        instance for now.
        """

        test_case.app = self.app

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
            help="Only run tests whose fully qualified name matches the given regex"
        )
        parser.add_argument(
            "-l", "--loglevel", default=None, type=str,
            help="Enable logging with the given log level"
        )
        parser.add_argument(
            "--extra-loglevel", type=str, help="Log level for extra SQLAlchemy loggers"
        )
        parser.add_argument(
            "-r", "--random-seed", type=int,
            help="Seed for the random number generator"
        )
        parser.add_argument(
            "-v", "--verbose", default=False, action="store_true",
            help="Increase verbosity"
        )

        return parser.parse_args()

    def _init_rng(self, randseed=None):
        if randseed is None:
            randseed = random.randint(0, 9999)

        random.seed(randseed)

        self._print_stderr(f"Using random seed {randseed} for shuffling test cases")

    def _err(self, *args):
        self._print_stderr("ERROR:", *args)
        raise SystemExit(2)

    @staticmethod
    def _print_stderr(*args):
        print(*args, file=sys.stderr)
