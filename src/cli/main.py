"""Command parsing and delegation; no financial or routing logic."""

import argparse
import sys

from src.manager import FinancialManagerAgent

from .formatting import answer, capabilities, details, plan, terminal_text


class CLIUsageError(Exception):
    pass


class HelpRequested(Exception):
    pass


class CLIParser(argparse.ArgumentParser):
    def __init__(self, *args, output=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.output = sys.stdout if output is None else output

    def error(self, message):
        # Argparse's normal message may echo secret/path-shaped arguments.
        raise CLIUsageError()

    def print_help(self, file=None):
        (self.output if file is None else file).write(self.format_help())

    def exit(self, status=0, message=None):
        if status == 0:
            raise HelpRequested()
        raise CLIUsageError()


def main(argv=None, *, manager=None, stdout=None, stderr=None):
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = CLIParser(prog="python -m src.cli", allow_abbrev=False, output=stdout)
    parser.add_argument("--json", action="store_true", help="Emit the complete structured response.")
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("capabilities", help="List capability availability.", allow_abbrev=False, output=stdout)
    preview = commands.add_parser("plan", help="Preview routing without execution.", allow_abbrev=False, output=stdout)
    preview.add_argument("question", help="One quoted financial question.")
    ask = commands.add_parser("ask", help="Ask the Financial Manager.", allow_abbrev=False, output=stdout)
    ask.add_argument("question", help="One quoted financial question.")
    for command in (catalog, preview, ask):
        command.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                             help="Emit the complete structured response.")
    try:
        args = parser.parse_args(argv)
        manager = FinancialManagerAgent() if manager is None else manager
        if args.command == "capabilities":
            result, render = manager.list_capabilities(), capabilities
        elif args.command == "plan":
            result, render = manager.plan(args.question), plan
        else:
            result, render = manager.ask(args.question), answer
        text = details(result) if args.json else terminal_text(render(result))
        stdout.write(text + "\n")
        stdout.flush()
    except HelpRequested:
        return 0
    except CLIUsageError:
        stderr.write("Invalid CLI syntax. Use python -m src.cli --help; quote the question as one argument.\n")
        return 2
    except KeyboardInterrupt:
        stderr.write("Command cancelled.\n")
        return 1
    except Exception:
        # The CLI is the user-facing error presenter. Internal exceptions remain
        # available through the existing Python interfaces, never printed here.
        stderr.write("Unable to complete the command. Check the local setup or use the Python interface for development diagnostics.\n")
        return 1
    return 0
