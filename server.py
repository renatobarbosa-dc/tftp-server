"""
TFTP Server Implementation (Enhanced CLI Version)

RFC 1350 compliant TFTP server with improved CLI interface,
logging control, and configuration flexibility.

Usage:
    python server.py --host 0.0.0.0 --port 6969 --directory storage --verbose

Author: Team TFTP
Date: March 2026
"""

import argparse
import logging
import os
import socket
import sys
from dataclasses import dataclass
from typing import Optional, Tuple

from tftp_packets import TFTPPacket, Opcode, ErrorCode

logger = logging.getLogger(__name__)


# ---------------------------
# Configuration
# ---------------------------

@dataclass
class ServerConfig:
    """Configuration object for TFTP server."""
    host: str
    port: int
    directory: str
    timeout: float
    retries: int
    read_only: bool


# ---------------------------
# Server
# ---------------------------

class TFTPServer:
    """Main TFTP server."""

    def __init__(self, config: ServerConfig):
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.running = True

    def _safe_path(self, filename: str) -> Optional[str]:
        """Prevent directory traversal."""
        base = os.path.abspath(self.config.directory)
        target = os.path.abspath(os.path.join(base, filename))

        if not target.startswith(base + os.sep) and target != base:
            return None

        return target
    
    def _send_error(
        self,
        sock: socket.socket,
        addr: Tuple[str, int],
        code: ErrorCode,
        message: str
    ) -> None:
        """Send error packet."""
        sock.sendto(TFTPPacket.encode_error(int(code), message), addr)

    # ---------------------------
    # WRQ
    # ---------------------------

    def _handle_wrq(self, filename: str, addr: Tuple[str, int]) -> None:
        """Handle write request."""
        if self.config.read_only:
            self._send_error(
                self.socket,
                addr,
                ErrorCode.ACCESS_VIOLATION,
                "Server is in read-only mode"
            )
            return

        path = self._safe_path(filename)
        if not path:
            self._send_error(self.socket, addr, ErrorCode.ACCESS_VIOLATION, "Invalid path")
            return

        if os.path.exists(path):
            self._send_error(self.socket, addr, ErrorCode.FILE_EXISTS, "File exists")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.config.timeout)

        try:
            with open(path, "wb") as f:
                sock.sendto(TFTPPacket.encode_ack(0), addr)

                expected = 1
                retries = 0

                while True:
                    try:
                        packet, client = sock.recvfrom(516)
                    except socket.timeout:
                        retries += 1
                        if retries > self.config.retries:
                            return
                        sock.sendto(TFTPPacket.encode_ack(expected - 1), addr)
                        continue

                    opcode, data = TFTPPacket.decode(packet)

                    if opcode == Opcode.DATA:
                        block, chunk = data

                        if block == expected:
                            f.write(chunk)
                            sock.sendto(TFTPPacket.encode_ack(block), addr)

                            if len(chunk) < TFTPPacket.MAX_DATA_SIZE:
                                logger.info("Upload complete: %s", filename)
                                return

                            expected += 1

        finally:
            sock.close()

    # ---------------------------
    # RRQ
    # ---------------------------

    def _handle_rrq(self, filename: str, addr: Tuple[str, int]) -> None:
        """Handle read request."""
        path = self._safe_path(filename)

        if not path or not os.path.exists(path):
            self._send_error(self.socket, addr, ErrorCode.FILE_NOT_FOUND, "Not found")
            return

        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.config.timeout)

        try:
            with open(path, "rb") as f:
                block = 1

                while True:
                    data = f.read(TFTPPacket.MAX_DATA_SIZE)
                    packet = TFTPPacket.encode_data(block, data)

                    sock.sendto(packet, addr)

                    try:
                        resp, _ = sock.recvfrom(516)
                    except socket.timeout:
                        continue

                    opcode, ack = TFTPPacket.decode(resp)

                    if opcode == Opcode.ACK and ack == block:
                        if len(data) < TFTPPacket.MAX_DATA_SIZE:
                            logger.info("Download complete: %s", filename)
                            return
                        block += 1

        finally:
            sock.close()
    
    def stop(self) -> None:
        """Stop the TFTP server."""
        self.running = False
        if self.socket:
            self.socket.close()

    # ---------------------------
    # MAIN LOOP
    # ---------------------------

    def start(self) -> None:
        """Start server."""
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.config.host, self.config.port))
        self.socket.settimeout(1.0) 

        logger.info(f"Starting TFTP server on {self.config.host}:{self.config.port}")

        while self.running:
            try:
                packet, client_addr = self.socket.recvfrom(516)
            except socket.timeout:
                continue

            try:
                opcode, data = TFTPPacket.decode(packet)
            except ValueError:
                continue

            if opcode == Opcode.RRQ:
                self._handle_rrq(data, addr)
            elif opcode == Opcode.WRQ:
                self._handle_wrq(data, addr)


# ---------------------------
# CLI
# ---------------------------

def parse_args() -> ServerConfig:
    """Parse CLI arguments."""
    parser = argparse.ArgumentParser(description="TFTP Server")

    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=6969)
    parser.add_argument("--directory", default="storage")

    parser.add_argument("--timeout", type=float, default=5.0)
    parser.add_argument("--retries", type=int, default=5)

    parser.add_argument("--read-only", action="store_true")
    parser.add_argument("--verbose", action="store_true")

    args = parser.parse_args()

    return ServerConfig(
        host=args.host,
        port=args.port,
        directory=args.directory,
        timeout=args.timeout,
        retries=args.retries,
        read_only=args.read_only
    ), args.verbose


def setup_logging(verbose: bool) -> None:
    """Configure logging."""
    level = logging.DEBUG if verbose else logging.INFO

    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )


def main() -> None:
    """Entry point."""
    config, verbose = parse_args()

    setup_logging(verbose)

    os.makedirs(config.directory, exist_ok=True)

    server = TFTPServer(config)

    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Stopping server...")
        server.stop()
        sys.exit(0)


if __name__ == "__main__":
    main()