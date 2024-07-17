
""" Sundry command-line argument parsing routines. Provides a set of
common recognized arguments and allows passing through arguments to
Gunicorn verbatim, separated from application args by `--`.
"""

import argparse
import sys

from attrs import define, field

@define
class Args:
    parser_args: dict = {}
    _parser: argparse.ArgumentParser = field(init=False, default=None)
    _parsed_args: argparse.Namespace = field(init=False, default=None)
    _our_argv: list = field(init=False)
    _rest_of_argv: list = field(init=False)

    def __attrs_post_init__(self):
        (self._our_argv, self._rest_of_argv) = self._split_command_line()

    @property
    def parser(self):
        if not self._parser:
            defaults = dict(
                epilog="Any arguments specified after `--` are passed on to the gunicorn server."
            )

            self._parser = argparse.ArgumentParser(**(defaults | self.parser_args))

        return self._parser

    @property
    def parsed_args(self):
        if not self._parsed_args:
            self._parsed_args = self.parser.parse_args(self._our_argv)

        return self._parsed_args

    @property
    def gunicorn_argv(self):

        """ Return the portion of argv separated by `--`. Translate our
        arguments to gunicorn equivalents and append to the former. Note that
        this will parse arguments, if this has not happened alredy.
        """

        args = self.parsed_args
        gunicorn_argv = self._rest_of_argv.copy()

        if args.port:
            gunicorn_argv += ["--bind", f"{args.bind}:{args.port}"]

        return gunicorn_argv

    def add_common_argumets(self, **defaults):

        """ Add default arguments to the parser. Override in a subclass to add
        application-specific arguments.
        """

        parser = self.parser

        parser.add_argument(
            "-b", "--bind", default="127.0.0.1", type=str,
            help="The interface to bind to, 127.0.0.1 by default"
        )
        parser.add_argument(
            "-p", "--port", default=defaults.get("port"), type=int,
            help="The port to listen on, {} by default".format(defaults.get("port"))
        )
        parser.add_argument(
            "-d", "--database", default=defaults.get("database"), type=str,
            help="The database URL, {} by default".format(defaults.get("database"))
        )
        parser.add_argument(
            "-l", "--loglevel", default=defaults.get("loglevel"), type=str,
            help="Log level, {} by default".format(defaults.get("loglevel"))
        )
        parser.add_argument(
            "--extra-loglevel", type=str, help="Log level for extra SQLAlchemy loggers"
        )
        parser.add_argument(
            "--hide-sql-params", action="store_true", help="Hide SQL parameters from log entries"
        )

    @staticmethod
    def _split_command_line():

        """ Split the command line on `--` and return the lists of
        arguments.
        """

        args = sys.argv[1:]
        separator_idx = None

        for i, arg in enumerate(args):
            if arg == "--":
                separator_idx = i
                break

        if separator_idx is None:
            return (args, [])

        return (args[:separator_idx], args[separator_idx + 1:])
