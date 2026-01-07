"""
Command-line interface for the Autonomous Research Agent.
"""

import argparse
import asyncio
import sys
from pathlib import Path


def main():
    """Main entry point for the CLI."""
    parser = argparse.ArgumentParser(
        description="Autonomous Research Agent - AI-powered research assistant",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  research-agent web              Start the web interface (Streamlit)
  research-agent research TOPIC   Run autonomous research on a topic
  research-agent --version        Show version information
        """,
    )

    parser.add_argument(
        "--version",
        action="version",
        version="%(prog)s 1.0.0",
    )

    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Web interface command
    web_parser = subparsers.add_parser("web", help="Start the Streamlit web interface")
    web_parser.add_argument(
        "--port",
        type=int,
        default=8501,
        help="Port to run the server on (default: 8501)",
    )
    web_parser.add_argument(
        "--host",
        default="localhost",
        help="Host to bind to (default: localhost)",
    )

    # Research command
    research_parser = subparsers.add_parser("research", help="Run autonomous research")
    research_parser.add_argument(
        "topic",
        help="Research topic to investigate",
    )
    research_parser.add_argument(
        "--depth",
        choices=["quick", "standard", "deep"],
        default="standard",
        help="Research depth (default: standard)",
    )
    research_parser.add_argument(
        "--max-papers",
        type=int,
        default=10,
        help="Maximum number of papers to analyze (default: 10)",
    )
    research_parser.add_argument(
        "--output",
        type=Path,
        help="Output directory for research results",
    )

    # Config command
    config_parser = subparsers.add_parser("config", help="Show configuration")
    config_parser.add_argument(
        "--check",
        action="store_true",
        help="Validate configuration",
    )

    args = parser.parse_args()

    if args.command == "web":
        run_web_interface(args)
    elif args.command == "research":
        asyncio.run(run_research(args))
    elif args.command == "config":
        show_config(args)
    else:
        parser.print_help()
        sys.exit(0)


def run_web_interface(args):
    """Start the Streamlit web interface."""
    import subprocess

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(Path(__file__).parent.parent.parent / "streamlit_app.py"),
        "--server.port",
        str(args.port),
        "--server.address",
        args.host,
    ]

    try:
        subprocess.run(cmd, check=True)
    except KeyboardInterrupt:
        print("\nShutting down...")
    except subprocess.CalledProcessError as e:
        print(f"Error starting web interface: {e}", file=sys.stderr)
        sys.exit(1)


async def run_research(args):
    """Run autonomous research on a topic."""
    from research_agent.config import settings

    # Validate configuration
    errors = settings.validate()
    if errors:
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    print(f"Starting research on: {args.topic}")
    print(f"Depth: {args.depth}")
    print(f"Max papers: {args.max_papers}")

    # Import and run the autonomous agent
    try:
        from research_agent.autonomous_agent import ResearchRequest, run_autonomous_research

        request = ResearchRequest(
            topic=args.topic,
            background="",
            depth=args.depth,
            max_papers=args.max_papers,
        )

        result = await run_autonomous_research(request)
        print(f"\nResearch complete!")
        print(f"Report saved to: {result.get('report_path', 'N/A')}")

    except ImportError as e:
        print(f"Error importing research module: {e}", file=sys.stderr)
        sys.exit(1)
    except Exception as e:
        print(f"Research error: {e}", file=sys.stderr)
        sys.exit(1)


def show_config(args):
    """Show current configuration."""
    from research_agent.config import settings

    print("Current Configuration:")
    print("-" * 40)
    print(f"App Name:        {settings.app_name}")
    print(f"Version:         {settings.app_version}")
    print(f"Debug:           {settings.debug}")
    print(f"Base Directory:  {settings.base_dir}")
    print(f"Sessions Dir:    {settings.research_sessions_dir}")
    print(f"Papers Dir:      {settings.papers_dir}")
    print(f"Streamlit Port:  {settings.streamlit_port}")
    print(f"Max Papers:      {settings.max_papers}")
    print("-" * 40)
    print(f"Anthropic Key:   {'✓ Set' if settings.anthropic_api_key else '✗ Missing'}")
    print(f"Tavily Key:      {'✓ Set' if settings.tavily_api_key else '✗ Missing'}")

    if args.check:
        print("-" * 40)
        errors = settings.validate()
        if errors:
            print("Validation FAILED:")
            for error in errors:
                print(f"  ✗ {error}")
            sys.exit(1)
        else:
            print("Validation PASSED ✓")


if __name__ == "__main__":
    main()
