"""Oracle MCP server package (installable entry point for tools in server.py)."""

__all__ = ["main"]


def main() -> None:
    from oracle_mcp_server.server import main as _main

    _main()
