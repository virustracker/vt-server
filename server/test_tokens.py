from tokens import Token, Request


def test_generate():
  t = Token(b'A'*32, 0)
  assert(t.hash() == "082c1193104576b8b8bf1594b2b32aeb520abb72fc9274826e169fd85c358a53")
  assert(t.slot == 0)

  # Tokens are not timedependent
  t2 = Token(b'A'*32, 300)
  assert(t.hash() == t2.hash() and t.slot != t2.slot)


def test_request():
  tokens = [Token(bytes([i])*32, i*300) for i in range(0, 256)]
  req = Request.create(tokens)

  assert(req.hash == "3261e3b141d03594b31d5ae7d64eca31ee664b8095c64fc04fb8bca0466d6b09")
  assert(req.verify([t.preimage for t in tokens]))

  # Omitting any secret should not work
  for i in range(0, 255):
    assert(not req.verify([t.preimage for t in tokens[i:i+1]]))

  assert(req.hash.startswith(req.id()))
