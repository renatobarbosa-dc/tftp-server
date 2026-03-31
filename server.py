import argparse
import logging
import os
import socket
import sys
import threading
from dataclasses import dataclass
from typing import Optional, Tuple
from tftp_packets import TFTPPacket, Opcode, ErrorCode

logger = logging.getLogger(__name__)

@dataclass
class ServerConfig:
    host: str
    port: int
    directory: str
    timeout: float
    retries: int
    read_only: bool

class TFTPServer:
    def __init__(self, config: ServerConfig):
        self.config = config
        self.socket: Optional[socket.socket] = None
        self.running = True

    def _safe_path(self, filename: str) -> Optional[str]:
        base = os.path.abspath(self.config.directory)
        target = os.path.abspath(os.path.join(base, filename))
        if not target.startswith(base + os.sep) and target != base:
            return None
        return target

    def _send_error(self, sock: socket.socket, addr: Tuple[str, int], code: ErrorCode, message: str) -> None:
        sock.sendto(TFTPPacket.encode_error(int(code), message), addr)

    def _handle_wrq(self, filename: str, addr: Tuple[str, int]) -> None:
        if self.config.read_only:
            logger.warning(f"Upload negado (Read-Only) para {addr}")
            temp_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self._send_error(temp_sock, addr, ErrorCode.ACCESS_VIOLATION, "Server is in read-only mode")
            temp_sock.close()
            return

        path = self._safe_path(filename)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.config.timeout)

        if not path:
            self._send_error(sock, addr, ErrorCode.ACCESS_VIOLATION, "Invalid path")
            sock.close()
            return

        if os.path.exists(path):
            self._send_error(sock, addr, ErrorCode.FILE_EXISTS, "File exists")
            sock.close()
            return

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
                            logger.error(f"Upload timeout: {filename}")
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
                            
                            expected = (expected + 1) % 65536
                            retries = 0
                    elif opcode == Opcode.ERROR:
                        logger.error(f"Cliente abortou upload: {data}")
                        return

        finally:
            sock.close()

    def _handle_rrq(self, filename: str, addr: Tuple[str, int]) -> None:
        path = self._safe_path(filename)
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.settimeout(self.config.timeout)

        if not path or not os.path.exists(path):
            self._send_error(sock, addr, ErrorCode.FILE_NOT_FOUND, "File not found")
            sock.close()
            return

        try:
            with open(path, "rb") as f:
                block = 1
                retries = 0
                data = f.read(TFTPPacket.MAX_DATA_SIZE)

                while True:
                    packet = TFTPPacket.encode_data(block, data)
                    sock.sendto(packet, addr)

                    try:
                        resp, _ = sock.recvfrom(516)
                    except socket.timeout:
                        retries += 1
                        if retries > self.config.retries:
                            logger.error(f"Download timeout: {filename}")
                            return
                        continue

                    opcode, ack = TFTPPacket.decode(resp)

                    if opcode == Opcode.ACK and ack == block:
                        if len(data) < TFTPPacket.MAX_DATA_SIZE:
                            logger.info("Download complete: %s", filename)
                            return
                        
                        block = (block + 1) % 65536
                        data = f.read(TFTPPacket.MAX_DATA_SIZE)
                        retries = 0
                    elif opcode == Opcode.ERROR:
                        logger.error(f"Cliente abortou download: {ack}")
                        return

        finally:
            sock.close()
            
    def stop(self) -> None:
        self.running = False
        if self.socket:
            self.socket.close()

    def start(self) -> None:
        self.socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.socket.bind((self.config.host, self.config.port))
        self.socket.settimeout(1.0) 

        logger.info(f"TFTP Server rodando em {self.config.host}:{self.config.port}")
        logger.info(f"Diretorio base: {os.path.abspath(self.config.directory)}")

        while self.running:
            try:
                packet, client_addr = self.socket.recvfrom(516)
            except socket.timeout:
                continue
            except OSError:
                break

            try:
                opcode, data = TFTPPacket.decode(packet)
            except ValueError as e:
                logger.error(f"Pacote invalido recebido: {e}")
                continue

            if opcode == Opcode.RRQ:
                threading.Thread(target=self._handle_rrq, args=(data, client_addr), daemon=True).start()
            elif opcode == Opcode.WRQ:
                threading.Thread(target=self._handle_wrq, args=(data, client_addr), daemon=True).start()

# ---------------------------
# CLI
# ---------------------------

def parse_args() -> Tuple[ServerConfig, bool]:
    parser = argparse.ArgumentParser(description="TFTP Server em Python")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=69)
    parser.add_argument("--directory", default="storage")
    parser.add_argument("--timeout", type=float, default=3.0)
    parser.add_argument("--retries", type=int, default=3)
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
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s - %(levelname)s - %(message)s"
    )

def main() -> None:
    config, verbose = parse_args()
    setup_logging(verbose)
    os.makedirs(config.directory, exist_ok=True)

    server = TFTPServer(config)
    try:
        server.start()
    except KeyboardInterrupt:
        logger.info("Encerrando servidor...")
        server.stop()
        sys.exit(0)

if __name__ == "__main__":
    main()