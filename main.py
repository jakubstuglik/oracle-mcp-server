"""Backward-compatible entry: ``python main.py`` from a source checkout.

Installed deployments should use the console script or::

    python -m oracle_mcp_server
"""

from oracle_mcp_server.server import main, mcp

__all__ = ["main", "mcp"]

if __name__ == "__main__":
    main()
