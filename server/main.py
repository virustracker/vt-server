from base64 import b64encode, b64decode
from binascii import Error as BinasciiError
from contextlib import contextmanager
from flask import jsonify
from sqlalchemy import Column, Integer, Float, LargeBinary
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import hashlib
import math
import os
import sqlalchemy
import json


TOKEN_BYTES = 16


class BadInputException(Exception):
    pass


if os.environ.get('CLOUD_SQL_CONNECTION_NAME', None) is not None:
    # We are running in productin, build the production DSN
    conn_name = os.environ.get('CLOUD_SQL_CONNECTION_NAME')
    sock_path = f'/cloudsql/{conn_name}/.s.PGSQL.5432'
    username = os.environ.get('DB_USER')
    password = os.environ.get('DB_PASS')
    dbname = os.environ.get('DB_NAME')
    driver = 'postgres+pg8000'
    DATABASE_URL = f'{driver}://{username}:{password}@/{dbname}?host={sock_path}'
else:
    # We are running locally
    DATABASE_URL = 'sqlite://'


engine = sqlalchemy.create_engine(DATABASE_URL)


Base = declarative_base()


class Token(Base):
    __tablename__ = "token"
    value = Column(LargeBinary, primary_key=True)
    type = Column(Integer)
    result = Column(Integer)
    location_lat = Column(Float)
    location_lon = Column(Float)

    def __eq__(self, other):
        return (
          self.value == other.value and
          self.type == other.value and
          self.result == other.result
        )


# Initialize the DB schema from the above description
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)


@contextmanager
def session_scope():
    """Provide a transactional scope around a series of operations."""
    session = Session()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def virustracker_hash(preimage):
    return hashlib.sha256(b"VIRUSTRACKER"+preimage)


def store_result(tokens, result, report_type):
    with session_scope() as session:
        for t in tokens:
            h = virustracker_hash(b64decode(t['preimage'])).digest()
            if 'lat' in t and 'long' in t:
                lat, lon = t['lat'], t['long']
            else:
                lat, lon = None, None

            session.add(Token(
                value=h,
                type=report_type,
                result=result,
                location_lat=lat,
                location_lon=lon
            ))
        session.commit()


def process_report(report):
    if not isinstance(report, dict) or not all(field in report for field in ('tokens', 'type', 'result')):
        raise BadInputException("Report must be a dict, and must contain 'tokens', 'type', and 'result'.")
    tokens = report['tokens']
    report_type = report['type']
    result = report['result']

    if not isinstance(tokens, list):
        raise BadInputException("Tokens must be a list.")

    for token in tokens:
        if not isinstance(token, dict) or 'preimage' not in token or not isinstance(token['preimage'], str):
            raise BadInputException("POSTed tokens must have a preimage.")

        if len(token['preimage']) != math.ceil(TOKEN_BYTES / 3) * 4 or len(b64decode(token['preimage'], validate=True)) != TOKEN_BYTES:
            raise BadInputException("Could not parse token preimage.")

        if any(latlong in token and not isinstance(token[latlong], (float, int)) for latlong in ('lat', 'long')):
            raise BadInputException("Could not parse token location.")

        if not isinstance(report_type, str) or report_type not in ('SELF_REPORT', 'VERIFIED'):
            raise BadInputException("Could not parse token type.")

        if not isinstance(result, str) or result not in ('UNKNOWN', 'POSITIVE', 'NEGATIVE'):
            raise BadInputException("Could not parse token result.")

    store_result(tokens, result, report_type)


def tokens(request):
    if request.method == 'GET':
        with session_scope() as session:
            toks = [{'value': b64encode(t.value), 'type': t.type} for t in session.query(Token).all()]
            return jsonify({'tokens': toks})
    elif request.method == 'POST':
        # Validate input
        try:
            request_json = request.get_json()
            if not request_json or not isinstance(request_json, dict) or 'report' not in request_json:
                raise BadInputException("Request must contain JSON, and must have a report.")
            report = request_json['report']
            process_report(report)
        except (BadInputException, BinasciiError, ValueError) as err:
            return ('Bad Request: ' + str(err), 400)
        return 'Success!'
    else:
        return ('Method Not Allowed', 405)
