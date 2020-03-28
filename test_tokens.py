from tokens import generate, Token


def test_generate():
    t = Token(b'A'*32, 0)
    assert(t.hash() == "082c1193104576b8b8bf1594b2b32aeb520abb72fc9274826e169fd85c358a53")
    assert(t.slot == 0)

    # Tokens are not timedependent
    t2 = Token(b'A'*32, 300)
    assert(t.hash() == t2.hash() and t.slot != t2.slot)
