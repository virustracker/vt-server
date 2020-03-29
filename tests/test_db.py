from server.main import Token, session_scope, tokens, virustracker_hash, process_report, engine, Base, TOKEN_BYTES
from base64 import b64encode, b64decode
from collections import namedtuple
import json
import sqlalchemy
import pytest
from sqlalchemy.orm import sessionmaker
import hashlib
from server import main


@pytest.fixture(autouse=True)
def db():
    """Temporarily swap out the engine for an in-memory DB

    This fixture is automatically called before each test. It swaps out the DB
    for an in-memory one, so tests can run in isolation.

    """
    old_engine = main.engine
    main.engine = sqlalchemy.create_engine('sqlite://')
    Base.metadata.create_all(main.engine)
    main.Session = sessionmaker(bind=main.engine)

    yield main.engine

    main.engine = old_engine
    main.Session = sessionmaker(bind=main.engine)


def test_crud():
    with session_scope() as session:
        t = Token(
            value=b'A'*32,
            type=0,
            result=0,
            location_lat=None,
            location_lon=None
        )
        session.add(t)
        session.commit()

        toks = list(session.query(Token).all())
        assert(len(toks) == 1)
        assert(t.value == toks[0].value)


Request = namedtuple('Request', ['method'])


def test_token_add():
    num_tokens = 10
    preimages = [bytes([i])*32 for i in range(0, num_tokens)]
    assert(len(preimages) == num_tokens)

    hashes = set([b64encode(virustracker_hash(p)[:TOKEN_BYTES]).decode('ASCII') for p in preimages])
    assert(len(hashes) == num_tokens)

    report = {
        'tokens': [{'preimage': b64encode(t).decode('ASCII')} for t in preimages],
        'type': 'SELF_REPORT',
        'result': 'POSITIVE',
    }

    process_report(report)

    request = Request(method='GET')
    result = json.loads(tokens(request))
    assert('tokens' in result)
    assert(len(result['tokens']) == num_tokens)
    assert(set([t['value'] for t in result['tokens']]) == hashes)


def test_token_update():
    preimage = b'A'*32
    report = {
        'tokens': [{'preimage': b64encode(preimage).decode('ASCII')}],
        'type': 'SELF_REPORT',
        'result': 'NEGATIVE',
    }
    process_report(report)
    with session_scope() as session:
        t = session.query(Token).first()
        print(t.__dict__)
        assert(t.type == main.types['SELF_REPORT'])
        assert(t.result == main.results['NEGATIVE'])

    # Now update and see if it worked
    report['type'] = 'VERIFIED'
    report['result'] = 'POSITIVE'
    process_report(report)

    with session_scope() as session:
        t = session.query(Token).first()
        print(t.__dict__)
        assert(t.type == main.types['VERIFIED'])
        assert(t.result == main.results['POSITIVE'])


def test_process_report():
    token = json.loads("""{
     	 "type": "VERIFIED",
     	 "result": "POSITIVE",
     	 "tokens": [{
     			 "preimage": "0000000000000000000000==",
     			 "lat": 47.3588359,
     			 "long": 8.5433576
     		 }
     	 ]
    }""")
    main.process_report(token)
    preimage = "0000000000000000000000=="
    token_value = hashlib.sha256(b"VIRUSTRACKER"+b64decode(preimage)).digest()
    with session_scope() as session:
        t = session.query(Token).first()
        assert(token_value == t.value)


def test_process_report_preimage_formaterror():
    token = json.loads("""{
     	 "type": "VERIFIED",
     	 "result": "POSITIVE",
     	 "tokens": [{
     			 "preimage": "000000000000000000==",
     			 "lat": 47.3588359,
     			 "long": 8.5433576
     		 }
     	 ]
      }""")
    with pytest.raises(Exception):
        main.process_report(token)
