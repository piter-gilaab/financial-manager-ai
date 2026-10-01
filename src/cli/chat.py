"""Interactive input adapter over the bounded conversation session."""

import sys

from .formatting import answer, details, terminal_text


PROMPT = "Financial Manager > "
CLARIFICATION_PROMPT = "Financial Manager [clarification] > "
HELP_TEXT = """Plain text starts a new request.
Commands:
/help
/status
/answer <value>
/follow <reference> <why_selected|record_detail>
/cancel
/reset
/exit"""
CHAT_USAGE_HINTS = (
    "Use the one-shot ask command with --full or --json for complete evidence.",
)


def _pending_clarification(status):
    context = status.get("active_context") if type(status) is dict else None
    return (context.get("pending_clarification")
            if type(context) is dict else None)


def _answer_example(choice):
    labels = {
        "FINANCIAL_ANALYSIS": "financial analysis",
        "ANOMALY_DETECTION": "anomaly screening",
        "receiver_general": "receiver general",
        "company_financials": "company financials",
    }
    return labels.get(choice, choice)


def _write_outcome(session, outcome, stdout):
    result = outcome.get("result")
    if type(result) is dict and "execution_status" in result:
        rendered = answer(result, full=False, usage_hints=CHAT_USAGE_HINTS)
        stdout.write(terminal_text(rendered) + "\n")
    elif result is not None:
        stdout.write("Result:\n" + terminal_text(details(result)) + "\n")
    if outcome.get("error") is not None:
        stdout.write("Session outcome: " + outcome["status"] + "\n")
        stdout.write(terminal_text(details(outcome["error"])) + "\n")
        if outcome.get("status") == "SESSION_EXPIRED":
            stdout.write("Enter a complete new request or use /reset to start a new session.\n")
    elif result is None:
        stdout.write("Session outcome: " + outcome["status"] + "\n")

    references = outcome.get("references")
    if type(references) is list and references:
        stdout.write("Evidence references:\n")
        for reference in references:
            stdout.write(f"- {reference['handle']} ({reference['kind']})\n")
        stdout.write("Use /follow <reference> why_selected\n")
        stdout.write("or /follow <reference> record_detail\n")

    status = session.status()
    pending = _pending_clarification(status)
    if pending is not None:
        stdout.write("Clarification pending. Use one of:\n")
        for choice in pending["choices"]:
            stdout.write("/answer " + _answer_example(choice) + "\n")
    elif outcome.get("status") == "CLARIFICATION_REQUIRED":
        stdout.write("This clarification cannot be continued with /answer; "
                     "enter a complete new request.\n")


def _answer_value(text):
    prefix = "/answer "
    if not text.startswith(prefix):
        return None
    value = text[len(prefix):]
    return value if value.strip() else None


def _write_status(session, stdout):
    status = session.status()
    safe = {
        key: status.get(key)
        for key in (
            "conversation_version", "status", "created_at", "last_activity_at",
            "inactivity_expires_at", "absolute_expires_at", "active_context",
        )
    }
    stdout.write("Session status:\n" + terminal_text(details(safe)) + "\n")


def _run_chat_loop(session, *, stdin, stdout):
    stdin = sys.stdin if stdin is None else stdin
    stdout = sys.stdout if stdout is None else stdout
    while True:
        prompt_status = session.status()
        prompt = (CLARIFICATION_PROMPT
                  if _pending_clarification(prompt_status) else PROMPT)
        stdout.write(prompt)
        stdout.flush()
        line = stdin.readline()
        if line == "":
            stdout.write("Chat ended.\n")
            stdout.flush()
            return 0
        request_text = line.rstrip("\r\n")
        text = request_text.strip()
        if not text:
            continue
        if text == "/exit":
            stdout.write("Chat ended.\n")
            stdout.flush()
            return 0
        if text == "/help":
            stdout.write(HELP_TEXT + "\n")
            stdout.flush()
            continue
        if text == "/status":
            _write_status(session, stdout)
            stdout.flush()
            continue
        if text == "/cancel":
            _write_outcome(session, session.cancel(), stdout)
            stdout.flush()
            continue
        if text == "/reset":
            _write_outcome(session, session.reset(), stdout)
            stdout.flush()
            continue
        value = _answer_value(text)
        if value is not None:
            _write_outcome(session, session.answer(value), stdout)
            stdout.flush()
            continue
        follow = text.split()
        if len(follow) == 3 and follow[0] == "/follow":
            _write_outcome(
                session,
                session.follow_up(reference=follow[1], intent=follow[2]),
                stdout,
            )
            stdout.flush()
            continue
        if text.startswith("/"):
            stdout.write("Invalid chat command. Use /help.\n")
            stdout.flush()
            continue
        current = session.status()
        if _pending_clarification(current) is not None:
            stdout.write("Starting a new request; the pending clarification is replaced.\n")
        outcome = session.new_request(request_text)
        _write_outcome(session, outcome, stdout)
        stdout.flush()


def run_chat(session, *, stdin=None, stdout=None):
    """Run one process-local chat until explicit exit, interrupt or end of input."""
    stdout = sys.stdout if stdout is None else stdout
    try:
        return _run_chat_loop(session, stdin=stdin, stdout=stdout)
    except KeyboardInterrupt:
        stdout.write("Chat ended.\n")
        stdout.flush()
        return 0
