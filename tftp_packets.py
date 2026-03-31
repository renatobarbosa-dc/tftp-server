import struct
from enum import IntEnum

class Opcode(IntEnum):
    RRQ = 1
    WRQ = 2
    DATA = 3
    ACK = 4
    ERROR = 5

class ErrorCode(IntEnum):
    NOT_DEFINED = 0
    FILE_NOT_FOUND = 1
    ACCESS_VIOLATION = 2
    DISK_FULL = 3
    ILLEGAL_OPERATION = 4
    UNKNOWN_TID = 5
    FILE_EXISTS = 6
    NO_SUCH_USER = 7

class TFTPPacket:
    MAX_DATA_SIZE = 512

    @staticmethod
    def encode_ack(block_num: int) -> bytes:
        return struct.pack("!HH", Opcode.ACK, block_num)

    @staticmethod
    def encode_error(error_code: int, msg: str) -> bytes:
        encoded_msg = msg.encode('ascii', errors='ignore')
        return struct.pack(f"!HH{len(encoded_msg)}sx", Opcode.ERROR, error_code, encoded_msg)

    @staticmethod
    def encode_data(block_num: int, data: bytes) -> bytes:
        return struct.pack(f"!HH{len(data)}s", Opcode.DATA, block_num, data)

    @staticmethod
    def decode(packet: bytes):
        opcode = struct.unpack("!H", packet[:2])[0]
        
        if opcode in (Opcode.RRQ, Opcode.WRQ):
            parts = packet[2:].split(b'\x00')
            filename = parts[0].decode('ascii', errors='ignore')
            return opcode, filename
            
        elif opcode == Opcode.DATA:
            block_num = struct.unpack("!H", packet[2:4])[0]
            data = packet[4:]
            return opcode, (block_num, data)
            
        elif opcode == Opcode.ACK:
            block_num = struct.unpack("!H", packet[2:4])[0]
            return opcode, block_num
            
        elif opcode == Opcode.ERROR:
            error_code = struct.unpack("!H", packet[2:4])[0]
            msg = packet[4:-1].decode('ascii', errors='ignore')
            return opcode, (error_code, msg)
            
        raise ValueError(f"Opcode desconhecido: {opcode}")