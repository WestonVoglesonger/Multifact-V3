"""
Interactive REPL for SNC.
"""

import code
import sys
from typing import Dict, Any


def get_banner() -> str:
    """Get the REPL banner."""
    return """
SNC Interactive REPL
===================

Available commands:
- help() - Show this help message
- exit() - Exit the REPL
"""


def get_context() -> Dict[str, Any]:
    """Get the REPL context."""
    return {
        "help": lambda: print(get_banner()),
    }


def main() -> None:
    """Start the interactive REPL."""
    banner = get_banner()
    context = get_context()

    # Start interactive console
    try:
        code.interact(banner=banner, local=context, exitmsg="Goodbye!")
    except KeyboardInterrupt:
        print("\nGoodbye!")
        sys.exit(0)


if __name__ == "__main__":
    main()
