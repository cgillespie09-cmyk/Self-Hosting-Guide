import argparse
import asyncio
import sys

# Try to import rich for pretty output; fall back to plain print
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.markdown import Markdown
    from rich import print as rprint
    _RICH = True
    _console = Console()
except ImportError:
    _RICH = False
    _console = None


def _print(msg: str, style: str = ""):
    if _RICH and _console:
        _console.print(msg, style=style)
    else:
        print(msg)


def _print_result(result):
    if _RICH and _console:
        header = (
            f"[bold green]Agent:[/bold green] {result.agent_used}  "
            f"[bold blue]Score:[/bold blue] {result.score:.1f}/10  "
            f"[bold yellow]Tokens:[/bold yellow] {result.tokens_used}  "
            f"[bold magenta]Latency:[/bold magenta] {result.latency_ms:.0f}ms  "
            f"[bold cyan]Mode:[/bold cyan] {result.mode}"
        )
        _console.print(Panel(Markdown(result.output), title=header, border_style="green" if result.success else "red"))
    else:
        sep = "-" * 60
        print(sep)
        print(f"Agent: {result.agent_used} | Score: {result.score:.1f}/10 | Tokens: {result.tokens_used} | Latency: {result.latency_ms:.0f}ms")
        print(sep)
        print(result.output)
        print(sep)


def _print_stats(stats: list[dict]):
    if not stats:
        _print("No task history yet.", style="yellow")
        return

    if _RICH and _console:
        table = Table(title="Ruflo Agent Performance Stats", show_header=True, header_style="bold magenta")
        table.add_column("Agent", style="cyan", no_wrap=True)
        table.add_column("Tasks", justify="right")
        table.add_column("Successes", justify="right")
        table.add_column("Avg Score", justify="right")
        table.add_column("Avg Latency (ms)", justify="right")
        table.add_column("Total Tokens", justify="right")

        for row in stats:
            table.add_row(
                str(row.get("agent_used", "?")),
                str(int(row.get("total_tasks", 0))),
                str(int(row.get("successes", 0))),
                f"{float(row.get('avg_score', 0.0)):.1f}",
                f"{float(row.get('avg_latency_ms', 0.0)):.0f}",
                str(int(row.get("total_tokens", 0))),
            )

        _console.print(table)
    else:
        print(f"{'Agent':<12} {'Tasks':>6} {'Success':>8} {'AvgScore':>9} {'AvgLatency':>12} {'Tokens':>10}")
        print("-" * 62)
        for row in stats:
            print(
                f"{str(row.get('agent_used', '?')):<12} "
                f"{int(row.get('total_tasks', 0)):>6} "
                f"{int(row.get('successes', 0)):>8} "
                f"{float(row.get('avg_score', 0.0)):>9.1f} "
                f"{float(row.get('avg_latency_ms', 0.0)):>12.0f} "
                f"{int(row.get('total_tokens', 0)):>10}"
            )


def _print_memory(messages: list[dict]):
    if not messages:
        _print("No messages in this session.", style="yellow")
        return

    if _RICH and _console:
        for msg in messages:
            role = msg.get("role", "?")
            content = msg.get("content", "")
            created = msg.get("created_at", "")
            style = "bold blue" if role == "user" else "bold green"
            _console.print(f"[{style}]{role.upper()}[/{style}] [{created}]")
            _console.print(content[:500] + ("..." if len(content) > 500 else ""))
            _console.print()
    else:
        for msg in messages:
            role = msg.get("role", "?").upper()
            content = msg.get("content", "")
            created = msg.get("created_at", "")
            print(f"\n[{role}] {created}")
            print(content[:500] + ("..." if len(content) > 500 else ""))


# ------------------------------------------------------------------ #
# Async command handlers
# ------------------------------------------------------------------ #

async def cmd_run(args):
    from ruflo.core import Ruflo

    _print(f"Running task: {args.task}", style="bold")
    ruflo = Ruflo(provider=args.provider)

    try:
        result = await ruflo.run(args.task, mode=args.mode)
        _print_result(result)
    except Exception as e:
        _print(f"Error: {e}", style="bold red")
        sys.exit(1)
    finally:
        await ruflo.close()


async def cmd_chat(args):
    from ruflo.core import Ruflo
    import datetime

    ruflo = Ruflo()
    session_id = f"chat-{datetime.datetime.now().strftime('%Y%m%d-%H%M%S')}"

    if _RICH and _console:
        _console.print("[bold cyan]Ruflo Chat[/bold cyan] — type 'quit' or 'exit' to stop, 'stats' to see performance.\n")
    else:
        print("Ruflo Chat — type 'quit' or 'exit' to stop, 'stats' to see performance.\n")

    try:
        while True:
            try:
                if _RICH and _console:
                    _console.print("[bold yellow]You:[/bold yellow] ", end="")
                else:
                    print("You: ", end="", flush=True)

                user_input = input()
            except (EOFError, KeyboardInterrupt):
                _print("\nGoodbye!", style="bold")
                break

            user_input = user_input.strip()
            if not user_input:
                continue

            if user_input.lower() in ("quit", "exit", "bye"):
                _print("Goodbye!", style="bold")
                break

            if user_input.lower() == "stats":
                stats = await ruflo.get_stats()
                _print_stats(stats)
                continue

            try:
                response = await ruflo.chat(user_input, session_id=session_id)
                if _RICH and _console:
                    _console.print(f"[bold green]Ruflo:[/bold green] {response}\n")
                else:
                    print(f"Ruflo: {response}\n")
            except Exception as e:
                _print(f"Error: {e}", style="bold red")
    finally:
        await ruflo.close()


async def cmd_stats(args):
    from ruflo.core import Ruflo

    ruflo = Ruflo()
    try:
        await ruflo._ensure_initialized()
        stats = await ruflo.get_stats()
        _print_stats(stats)
    except Exception as e:
        _print(f"Error: {e}", style="bold red")
        sys.exit(1)
    finally:
        await ruflo.close()


async def cmd_memory(args):
    from ruflo.core import Ruflo
    import datetime

    ruflo = Ruflo()
    session_id = datetime.date.today().isoformat()

    try:
        await ruflo._ensure_initialized()
        messages = await ruflo.get_memory(session_id)
        if _RICH and _console:
            _console.print(f"[bold]Memory for session:[/bold] {session_id}")
        else:
            print(f"Memory for session: {session_id}")
        _print_memory(messages)
    except Exception as e:
        _print(f"Error: {e}", style="bold red")
        sys.exit(1)
    finally:
        await ruflo.close()


# ------------------------------------------------------------------ #
# Dispatch
# ------------------------------------------------------------------ #

async def dispatch(args):
    if args.command == "run":
        await cmd_run(args)
    elif args.command == "chat":
        await cmd_chat(args)
    elif args.command == "stats":
        await cmd_stats(args)
    elif args.command == "memory":
        await cmd_memory(args)
    else:
        _print("No command specified. Use --help for usage.", style="yellow")


# ------------------------------------------------------------------ #
# Entry point
# ------------------------------------------------------------------ #

def main():
    parser = argparse.ArgumentParser(
        prog="ruflo",
        description="Ruflo — self-learning multi-agent AI system",
    )
    subparsers = parser.add_subparsers(dest="command", metavar="COMMAND")

    # run command
    run_parser = subparsers.add_parser("run", help="Run a one-shot task")
    run_parser.add_argument("task", help="The task to execute")
    run_parser.add_argument(
        "--mode",
        default="sequential",
        choices=["sequential", "parallel", "best_of"],
        help="Swarm execution mode (default: sequential)",
    )
    run_parser.add_argument(
        "--provider",
        default="claude",
        choices=["claude", "openai"],
        help="LLM provider to use (default: claude)",
    )

    # chat command
    subparsers.add_parser("chat", help="Interactive chat REPL")

    # stats command
    subparsers.add_parser("stats", help="Show agent performance statistics")

    # memory command
    mem_parser = subparsers.add_parser("memory", help="Memory operations")
    mem_parser.add_argument(
        "action",
        choices=["show"],
        help="Memory action to perform",
    )

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(0)

    try:
        asyncio.run(dispatch(args))
    except KeyboardInterrupt:
        _print("\nInterrupted.", style="yellow")
        sys.exit(0)


if __name__ == "__main__":
    main()
