"""Model Context Protocol (MCP) stdio server stub."""

from typing import TextIO, Optional
import sys


class MCPServer:
    """Stdio JSON-RPC 2.0 MCP Server for BenchWarmer."""

    def __init__(self, db_path: Optional[str] = None) -> None:
        raise NotImplementedError("MCPServer.__init__ not implemented in Phase 0")

    def handle_message(self, line: str) -> Optional[str]:
        raise NotImplementedError("MCPServer.handle_message not implemented in Phase 0")


def run_stdio_server(in_stream: TextIO = sys.stdin, out_stream: TextIO = sys.stdout) -> None:
    raise NotImplementedError("run_stdio_server not implemented in Phase 0")
