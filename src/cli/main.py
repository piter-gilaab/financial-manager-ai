"""Command parsing and delegation; no financial or routing logic."""

import argparse
import json
import sys

from src.manager import FinancialManagerAgent, FinancialManagerSession
from src.mediation import ConversationMediator, LocalHTTPProvider
from src.mediation.local_provider import DEFAULT_TIMEOUT_SECONDS, DEFAULT_URL, MAX_TIMEOUT_SECONDS
from src.onboarding import OnboardingManager

from .chat import run_chat
from .dataset import render_dataset
from .formatting import answer, capabilities, details, plan, terminal_text


class CLIUsageError(Exception):
    pass


class HelpRequested(Exception):
    pass


class MediationConfigError(Exception):
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


def main(argv=None, *, manager=None, session=None, mediator=None, onboarding=None, stdin=None,
         stdout=None, stderr=None):
    stdout = sys.stdout if stdout is None else stdout
    stderr = sys.stderr if stderr is None else stderr
    parser = CLIParser(prog="python -m src.cli", allow_abbrev=False, output=stdout)
    parser.add_argument("--json", action="store_true", help="Emit the complete structured response.")
    parser.add_argument("--full", action="store_true", help="Emit expanded human evidence.")
    commands = parser.add_subparsers(dest="command", required=True)
    catalog = commands.add_parser("capabilities", help="List capability availability.", allow_abbrev=False, output=stdout)
    preview = commands.add_parser("plan", help="Preview routing without execution.", allow_abbrev=False, output=stdout)
    preview.add_argument("question", help="One quoted financial question.")
    ask = commands.add_parser("ask", help="Ask the Financial Manager.", allow_abbrev=False, output=stdout)
    ask.add_argument("question", help="One quoted financial question.")
    chat = commands.add_parser("chat", help="Start a bounded interactive session.",
                               allow_abbrev=False, output=stdout)
    chat.add_argument("--llm-model", help="Enable natural-language mediation with this local model name.")
    chat.add_argument("--llm-url", help="Loopback OpenAI-compatible chat-completions URL "
                      f"(default {DEFAULT_URL}).")
    chat.add_argument("--llm-timeout", type=float,
                      help=f"Seconds per mediation call, at most {MAX_TIMEOUT_SECONDS} "
                      f"(default {DEFAULT_TIMEOUT_SECONDS}).")
    dataset = commands.add_parser("dataset", help="Onboard a bounded local dataset.",
                                  allow_abbrev=False, output=stdout)
    dataset_commands = dataset.add_subparsers(dest="dataset_command", required=True)
    dataset_add = dataset_commands.add_parser("add", allow_abbrev=False, output=stdout)
    dataset_add.add_argument("file")
    dataset_add.add_argument("--sheet")
    dataset_add.add_argument("--provenance-note")
    dataset_add.add_argument("--llm-model")
    dataset_add.add_argument("--llm-url")
    dataset_add.add_argument("--llm-timeout", type=float)
    dataset_status = dataset_commands.add_parser("status", allow_abbrev=False, output=stdout)
    dataset_profile = dataset_commands.add_parser("profile", allow_abbrev=False, output=stdout)
    dataset_mappings = dataset_commands.add_parser("mappings", allow_abbrev=False, output=stdout)
    dataset_confirm = dataset_commands.add_parser("confirm", allow_abbrev=False, output=stdout)
    dataset_domain = dataset_commands.add_parser("confirm-domain", allow_abbrev=False, output=stdout)
    dataset_reject = dataset_commands.add_parser("reject", allow_abbrev=False, output=stdout)
    dataset_stop = dataset_commands.add_parser("stop", allow_abbrev=False, output=stdout)
    dataset_capabilities = dataset_commands.add_parser("capabilities", allow_abbrev=False, output=stdout)
    for command in (dataset_status, dataset_profile, dataset_mappings, dataset_capabilities):
        command.add_argument("dataset_id")
    dataset_confirm.add_argument("dataset_id")
    dataset_confirm.add_argument("column")
    dataset_confirm.add_argument("role")
    dataset_confirm.add_argument("--evidence", required=True)
    dataset_confirm.add_argument("--value-map")
    dataset_confirm.add_argument("--date-format", choices=("YYYY-MM-DD", "DD/MM/YYYY", "MM/DD/YYYY"))
    dataset_domain.add_argument("dataset_id")
    dataset_domain.add_argument("domain")
    dataset_domain.add_argument("--evidence", required=True)
    dataset_reject.add_argument("dataset_id")
    dataset_reject.add_argument("column")
    dataset_reject.add_argument("--evidence", required=True)
    dataset_stop.add_argument("dataset_id")
    dataset_stop.add_argument("--evidence", required=True)
    dataset_stop.add_argument("--reject-dataset", action="store_true")
    for command in (dataset_add, dataset_status, dataset_profile, dataset_mappings, dataset_confirm,
                    dataset_domain, dataset_reject, dataset_stop, dataset_capabilities):
        command.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                             help="Emit the complete structured response.")
    for command in (catalog, preview, ask):
        command.add_argument("--json", action="store_true", default=argparse.SUPPRESS,
                             help="Emit the complete structured response.")
        command.add_argument("--full", action="store_true", default=argparse.SUPPRESS,
                             help="Emit expanded human evidence.")
    try:
        args = parser.parse_args(argv)
        if args.json and args.full:
            raise CLIUsageError()
        if args.command == "chat":
            if args.json or args.full:
                raise CLIUsageError()
            if args.llm_model is None and (args.llm_url is not None or args.llm_timeout is not None):
                raise CLIUsageError()
            provider = None
            if mediator is None and args.llm_model is not None:
                options = {"model": args.llm_model}
                if args.llm_url is not None:
                    options["url"] = args.llm_url
                if args.llm_timeout is not None:
                    options["timeout"] = args.llm_timeout
                try:
                    provider = LocalHTTPProvider(**options)
                except ValueError:
                    raise MediationConfigError() from None
            if session is None:
                # An injected mediator already owns the one session the chat must use.
                session = (FinancialManagerSession(manager=manager) if mediator is None
                           else mediator.session)
            if provider is not None:
                mediator = ConversationMediator(session, provider)
            return run_chat(session, mediator=mediator, stdin=stdin, stdout=stdout)
        if args.command == "dataset":
            if args.full:
                raise CLIUsageError()
            if args.dataset_command == "add" and args.llm_model is None and (
                    args.llm_url is not None or args.llm_timeout is not None):
                raise CLIUsageError()
            if onboarding is None:
                semantic_provider = None
                if args.dataset_command == "add" and args.llm_model is not None:
                    options = {"model": args.llm_model}
                    if args.llm_url is not None:
                        options["url"] = args.llm_url
                    if args.llm_timeout is not None:
                        options["timeout"] = args.llm_timeout
                    try:
                        semantic_provider = LocalHTTPProvider(**options)
                    except ValueError:
                        raise MediationConfigError() from None
                onboarding = OnboardingManager(semantic_provider=semantic_provider)
            operation = args.dataset_command
            if operation == "add":
                result = onboarding.add(args.file, sheet=args.sheet,
                                        provenance_note=args.provenance_note)
            elif operation == "status":
                result = onboarding.status(args.dataset_id)
            elif operation == "profile":
                result = onboarding.profile(args.dataset_id)
            elif operation == "mappings":
                result = onboarding.mappings(args.dataset_id)
            elif operation == "confirm-domain":
                result = onboarding.confirm_domain(
                    args.dataset_id, args.domain, evidence=args.evidence,
                )
            elif operation == "confirm":
                value_mapping = None
                if args.value_map is not None:
                    try:
                        value_mapping = json.loads(args.value_map)
                    except ValueError:
                        raise CLIUsageError() from None
                    if type(value_mapping) is not dict:
                        raise CLIUsageError()
                result = onboarding.confirm(
                    args.dataset_id, args.column, args.role, evidence=args.evidence,
                    value_mapping=value_mapping, date_format=args.date_format,
                )
            elif operation == "reject":
                result = onboarding.reject(args.dataset_id, args.column, evidence=args.evidence)
            elif operation == "stop":
                result = onboarding.stop(
                    args.dataset_id, reject=args.reject_dataset, evidence=args.evidence,
                )
            else:
                result = onboarding.capabilities(args.dataset_id)
            text = details(result) if args.json else terminal_text(render_dataset(operation, result))
            stdout.write(text + "\n")
            stdout.flush()
            return 0
        manager = FinancialManagerAgent() if manager is None else manager
        if args.command == "capabilities":
            result, render = manager.list_capabilities(), capabilities
        elif args.command == "plan":
            result, render = manager.plan(args.question), plan
        else:
            result = manager.ask(args.question)
            render = lambda value: answer(value, full=args.full)
        text = details(result) if args.json else terminal_text(render(result))
        stdout.write(text + "\n")
        stdout.flush()
    except HelpRequested:
        return 0
    except MediationConfigError:
        stderr.write("Invalid LLM mediation configuration. Use --llm-model with a loopback "
                     "--llm-url (localhost, 127.0.0.1 or ::1) and --llm-timeout of at most 120 seconds.\n")
        return 2
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
