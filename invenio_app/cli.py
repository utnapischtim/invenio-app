# -*- coding: utf-8 -*-
#
# This file is part of Invenio.
# Copyright (C) 2017-2018 CERN.
# Copyright (C) 2025 Graz University of Technology.
#
# Invenio is free software; you can redistribute it and/or modify it
# under the terms of the MIT License; see LICENSE file for more details.

"""CLI application for Invenio flavours."""

import contextlib
import io
import pickle
import socket
import socketserver

from click import group, option, pass_context, secho
from flask.cli import with_appcontext
from invenio_base.app import create_cli

from .factory import create_app

#: Invenio CLI application.
cli = create_cli(create_app=create_app)


class RPCRequestHandler(socketserver.BaseRequestHandler):
    """RPCRequestHandler."""

    def handle(self):
        """Handles the requests to the RPCServer."""
        data = self.request.recv(4096)
        if not data:
            return

        try:
            command_parts = pickle.loads(data)

            if not isinstance(command_parts, list) or len(command_parts) == 0:
                raise ValueError("Invalid command format should be a list.")

            if command_parts[0] == "ping":
                result = "pong"
            else:
                output_buffer = io.StringIO()
                with contextlib.redirect_stdout(output_buffer):
                    cli.main(args=command_parts, standalone_mode=False)
                result = output_buffer.getvalue().strip()

            response = pickle.dumps({"success": True, "result": result})
        except Exception as e:
            response = pickle.dumps({"success": False, "error": str(e)})

        self.request.sendall(response)


class RPCServer(socketserver.TCPServer):
    """RPCServer implementation."""

    allow_reuse_address = True

    def shutdown_server(self):
        """Shutdown the server."""
        secho("Shutting down RPC Server...", fg="green")
        self.shutdown()
        self.server_close()


def send(host, port, args):
    """Send."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((host, port))
        s.sendall(pickle.dumps(list(args)))

        return pickle.loads(s.recv(4096))


@group()
@option("--port", default=5000)
@option("--host", default="localhost")
def rpc_server(port, host):
    """RPC server."""
    # TODO pass in the context


@rpc_server.command("start")
@with_appcontext
def rpc_server_start():
    """Start rpc server."""
    host = "localhost"
    port = 5000
    server = RPCServer((host, port), RPCRequestHandler)

    secho(
        f"RPC Server is running on port {host}:{port}... (Press Ctrl+C to stop)",
        fg="green",
    )

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()


@rpc_server.command(
    "send",
    context_settings={"allow_extra_args": True, "ignore_unknown_options": True},
)
@pass_context
def rpc_server_send(ctx):
    """Send."""
    host = "localhost"
    port = 5000

    response = send(host, port, ctx.args)
    if response["success"]:
        secho(f"Response: {response['result']}", fg="green")
    else:
        secho(f"Error: {response['error']}", fg="red")


@rpc_server.command("ping")
def rpc_server_ping():
    """Ping."""
    host = "localhost"
    port = 5000
    response = send(host, port, ["ping"])
    secho(response["result"])
