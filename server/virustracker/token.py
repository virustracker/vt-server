from . import common
from .common import db_connect, db_execute

import hashlib
import hmac
import math
import sqlalchemy
from flask import jsonify
from base64 import b64encode, b64decode
from binascii import Error as BinasciiError

PREIMAGE_BYTES = 32
TOKEN_VALUE_BYTES = 32

def compute_token_value(preimage):
  return hashlib.sha256(b"VIRUSTRACKER" + preimage).digest()

def verify_ahp(preimages, ahp):
  m = hashlib.sha256()
  for pi in preimages:
    m.update(pi)
  return hmac.compare_digest(ahp, m.digest()[:len(ahp)])

# Add to or update token table
def store_tokens(token_values, report_result, report_type):
  # Disallow overwriting verified results with self-reported results.
  update_condition = " WHERE token.report_type <> 'VERIFIED'" if report_type != "VERIFIED" else ""
  
  stmt = sqlalchemy.text(
    "INSERT INTO token (token_value, report_type, report_result) "
    "VALUES (:value, :type, :result) "
    "ON CONFLICT (token_value) DO UPDATE "
    "SET report_type = :type, report_result = :result"
    + update_condition
  )
  
  with db_connect() as conn:
    db_execute(conn, stmt, *[{'type': report_type, 'result': report_result, 'value': value} for value in token_values])

class BadInputException(Exception):
  pass
class VerificationFailedException(Exception):
  pass

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
    if not common.AHP_MIN_BYTES <= len(ahp) <= common.AHP_MAX_BYTES:
      raise BadInputException("bad attestation_hash_prefix length.")
    
    # Verify attestation_hash_prefix is correct and has an attestation
    if not verify_ahp(preimages, ahp):
      raise VerificationFailedException()
    with db_connect() as conn:
      rows = db_execute(conn, sqlalchemy.text("SELECT result FROM certificate WHERE attestation_hash_prefix = :ahp"), {'ahp': ahp}).fetchall()
      if not rows:
        raise VerificationFailedException()
      report_result = rows[0][0]
  assert report_result
  
  store_tokens((compute_token_value(pi) for pi in preimages), report_result, report_type)

def endpoint(request):
  if request.path != '/':
    return ('Invalid Path', 404)
  if request.method == 'GET':
    with db_connect() as conn:
      all_tokens = db_execute(conn, "SELECT token_value, report_type FROM token WHERE report_result = 'POSITIVE'").fetchall()
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
    except (VerificationFailedException):
      return ('Verification Failed', 403)
    return 'Success!'
  else:
    return ('Method Not Allowed', 405)
