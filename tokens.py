import hashlib
from binascii import hexlify, unhexlify
from collections import namedtuple
import secrets

token_len = 32
salt = b"virustracker"
rotate_interval = 5*60  # Rotate token every 5 minutes


class Token(object):
    def __init__(self, preimage: bytes, slot: int) -> None:
        assert(len(preimage) == 32)
        self.preimage = preimage
        self.slot = slot

    def hash(self) -> str:
        m = hashlib.sha256()
        m.update(salt)
        m.update(self.preimage)
        return m.hexdigest()

    def timestamp(self) -> int:
        return self.slot * rotate_interval


def generate(timestamp: int) -> Token:
    preimage = secrets.token_bytes(32)
    slot = timestamp // rotate_interval
    return Token(preimage, slot)
