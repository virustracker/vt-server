import math
import os
import sqlalchemy
from flask import jsonify
from base64 import b64encode, b64decode
from binascii import Error as BinasciiError
import hashlib
import hmac

PREIMAGE_BYTES = 32
TOKEN_VALUE_BYTES = 32

def compute_token_value(preimage):
  return hashlib.sha256(b"VIRUSTRACKER" + preimage).digest()

class BadInputException(Exception):
  pass

class ForbiddenException(Exception):
  pass

db = sqlalchemy.create_engine(
    sqlalchemy.engine.url.URL(
      drivername='postgres+pg8000',
      username=os.environ.get('DB_USER'),
      password=os.environ.get('DB_PASS'),
      database=os.environ.get('DB_NAME'),
      query={'unix_sock': '/cloudsql/{}/.s.PGSQL.5432'.format(os.environ.get('CLOUD_SQL_CONNECTION_NAME'))}
    ),
    pool_size=1,
)

def db_connect():
  return db.connect()

def db_execute(conn, stmt, values):
  conn.execute(stmt, **values)

# Add to or update token table
def store_tokens(token_values, report_result, report_type):
  # Disallow overwriting verified results with self-reported results.
  update_condition = " WHERE token.report_type <> 'VERIFIED'" if report_type != "VERIFIED" else ""
  
  stmt = sqlalchemy.text(
    "INSERT INTO token (token_value, report_type, report_result) "
    "VALUES (:token_value, :report_type, :report_result) "
    "ON CONFLICT (token_value) DO UPDATE "
    "SET report_type = :report_type, report_result = :report_result"
    + update_condition
  )
  
  with db_connect() as conn:
    new_row = {}
    new_row['report_type'  ] = report_type
    new_row['report_result'] = report_result
    for token_value in token_values:
      new_row['token_value'] = token_value
      db_execute(conn, stmt, new_row)

def process_report(report):
  # Validate input
  if not isinstance(report, dict) or not all(field in report for field in ('tokens', 'type')):
    raise BadInputException("Report must be a dict, and must contain 'tokens', and 'type'.")
  tokens = report['tokens']
  report_type = report['type']
  if not isinstance(tokens, list):
    raise BadInputException("Tokens must be a list.")
  for token in tokens:
    if not isinstance(token, dict) or 'preimage' not in token or not isinstance(token['preimage'], str):
      raise BadInputException("Submitted tokens must have a preimage.")
    try:
      if len(token['preimage']) != math.ceil(PREIMAGE_BYTES / 3) * 4 or len(b64decode(token['preimage'], validate=True)) != PREIMAGE_BYTES:
        raise BadInputException("Could not parse token preimage.")
    except (BinasciiError, ValueError) as err:
      raise BadInputException("Invalid Base64.")
  preimages = [b64decode(token['preimage']) for token in tokens]
  if not isinstance(report_type, str) or report_type not in ('SELF_REPORT', 'VERIFIED'):
    raise BadInputException("Could not parse token type.")
  if report_type == 'SELF_REPORT':
    if 'result' not in report:
      raise BadInputException("Self-reports must specify 'result'.")
    report_result = report['result']
    if not isinstance(report_result, str) or report_result not in ('UNKNOWN', 'POSITIVE', 'NEGATIVE'):
      raise BadInputException("Could not parse token result.")
  elif report_type == 'VERIFIED':
    if 'result' in report:
      raise BadInputException("Verified reports cannot specify 'result'.")
    if 'attestation_hash_prefix' not in report:
      raise BadInputException("Verified reports must specify 'attestation_hash_prefix'.")
    try:
      ahp = b64decode(report['attestation_hash_prefix'], validate=True)
    except (BinasciiError, ValueError) as err:
      raise BadInputException("Invalid Base64.")
    if len(ahp) < 8:
      raise BadInputException("attestation_hash_prefix too short.")
    
    # Verify attestation_hash_prefix is correct and has an attestation
    if not verify_ahp(preimages, ahp):
      raise ForbiddenException()
    with db_connect() as conn:
      rows = conn.execute(sqlalchemy.text("SELECT report_result FROM certificate WHERE attestation_hash_prefix = :ahp"), {'ahp': ahp}).fetchall()
      if not rows:
        raise ForbiddenException()
      report_result = rows[0][0]
  assert report_result
  
  store_tokens((compute_token_value(pi) for pi in preimages), report_result, report_type)

def verify_ahp(preimages, ahp):
  m = hashlib.sha256()
  for pi in preimages:
    m.update(pi)
  return hmac.compare_digest(ahp, m.digest()[:len(ahp)])

def tokens(request):
  if request.path != '/':
    return ('Invalid Path', 404)
  if request.method == 'GET':
    with db_connect() as conn:
      all_tokens = conn.execute("SELECT token_value, report_type FROM token WHERE report_result = 'POSITIVE'").fetchall()
      return jsonify({'tokens': [{'value': b64encode(row[0]).decode('ascii'), 'type': row[1]} for row in all_tokens]})
  elif request.method == 'POST':
    try:
      request_json = request.get_json()
      if not request_json or not isinstance(request_json, dict) or 'report' not in request_json:
        raise BadInputException("Request must contain JSON, and must have a report.")
      report = request_json['report']
      process_report(report)
    except (BadInputException) as err:
      return ('Bad Request: ' + str(err), 400)
    except (ForbiddenException):
      return ('Forbidden', 403)
    return 'Success!'
  else:
    return ('Method Not Allowed', 405)

