import server.common
from server.common import db_connect, db_execute

import hashlib
import hmac
import math
import sqlalchemy
from flask import jsonify
from base64 import b64encode, b64decode
from binascii import Error as BinasciiError

def verify_attestation(attestation, ahp, result, lab_key):
  m = hmac.new(lab_key, digestmod='sha256')
  m.update(ahp)
  m.update(result.encode('ASCII'))
  truth = m.digest()
  return hmac.compare_digest(truth, attestation)

class BadInputException(Exception):
  pass
class VerificationFailedException(Exception):
  pass

def process_attestation(attestation, ahp, result, lab_id):
  with db_connect() as conn:
    rows = db_execute(conn, "SELECT key FROM lab WHERE id = :id", {'id': lab_id}).fetchall()
    if not rows:
      raise VerificationFailedException()
    lab_key = rows[0][0]
    if not verify_attestation(attestation, ahp, result, lab_key):
      raise VerificationFailedException()
    stmt = sqlalchemy.text(
      "INSERT INTO certificate (attestation_hash_prefix, result, lab_id) "
      "VALUES (:ahp, :result, :lab_id) "
      "ON CONFLICT (attestation_hash_prefix) DO UPDATE "
      "SET result = :result, lab_id = :lab_id"
    )
    db_execute(conn, stmt, {'ahp': ahp, 'result': result, 'lab_id': lab_id})

def lab_certificate_endpoint(request):
  try:
    ahp = b64decode(request.path[1:], '-_', validate=True)
  except (BinasciiError, ValueError) as err:
    return ('Invalid Path', 404)
  if not common.AHP_MIN_BYTES <= len(ahp) <= common.AHP_MAX_BYTES:
    return ('Invalid Path', 404)
  if request.method == 'GET':
    with db_connect() as conn:
      rows = db_execute(conn, "SELECT result FROM certificate WHERE attestation_hash_prefix = :ahp", {'ahp': ahp}).fetchall()
      if not rows:
        return ('Not Found', 404)
      return jsonify({'result': rows[0][0]})
  elif request.method == 'PUT':
    try:
      request_json = request.get_json()
      if not request_json or not isinstance(request_json, dict) or not all(field in request_json for field in ('result', 'attestation', 'lab_id')):
        raise BadInputException("Request must contain JSON, and must have a 'result', 'attestation', and 'lab_id'.")
      result = request_json['result']
      if not isinstance(result, str) or result not in ('UNKNOWN', 'POSITIVE', 'NEGATIVE'):
        raise BadInputException("Could not parse result.")
      try:
        attestation = b64decode(request_json['attestation'], validate=True)
      except (BinasciiError, ValueError) as err:
        raise BadInputException("Could not parse attestation.")
      lab_id = request_json['lab_id']
      if not isinstance(lab_id, int) or lab_id <= 0:
        raise BadInputException("Invalid lab_id.")
      process_attestation(attestation, ahp, result, lab_id)
    except (BadInputException) as err:
      return ('Bad Request: ' + str(err), 400)
    except (VerificationFailedException):
      return ('Verification Failed', 403)
    return 'Success!'
  else:
    return ('Method Not Allowed', 405)
