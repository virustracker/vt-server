import hashlib
from binascii import hexlify, unhexlify
from collections import namedtuple
import secrets
from typing import List, Type, TypeVar

T = TypeVar('T', bound='Parent')
token_len = 32
salt = b"virustracker"
rotate_interval = 5*60  # Rotate token every 5 minutes
id_len = 8


class Token(object):
  """A locally generated token, or from a device when verifying.
  The token consists of a the tuple `(preimage, hash, timeslot)` and is
  regenerated every `rotate_interval` seconds.
  """
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

  @classmethod
  def generate(cls: Type[T], timestamp: int) -> T:
    preimage = secrets.token_bytes(32)
    slot = timestamp // rotate_interval
    return Token(preimage, slot)


class Request(object):
  """A hash of multiple concatenated preimages used to identify the test instance.
  The client device generates the request from a set of tokens, then passes
  the hash to the server. Later the client also supplies the preimages and
  the server can verify that the preimages match its expectation.
  """

  def __init__(self, hash) -> None:
    self.hash = hash

  def id(self) -> str:
    return self.hash[:id_len]

  def verify(self, preimages) -> bool:
    m = hashlib.sha256()
    m.update(salt)

    for p in preimages:
      m.update(p)

    return self.hash == m.hexdigest()

  @classmethod
  def create(cls: Type[T], tokens: List[Token]) -> T:
    m = hashlib.sha256()
    m.update(salt)

    for t in tokens:
      m.update(t.preimage)

    return Request(m.hexdigest())
