import math
import os
import sqlalchemy
from flask import jsonify
from base64 import b64encode, b64decode
from binascii import Error as BinasciiError
import hashlib

TOKEN_BYTES = 16

class BadInputException(Exception):
  pass

def db_connect():
  return sqlalchemy.create_engine(
    sqlalchemy.engine.url.URL(
      drivername='postgres+pg8000',
      username=os.environ.get('DB_USER'),
      password=os.environ.get('DB_PASS'),
      database=os.environ.get('DB_NAME'),
      query={'unix_sock': '/cloudsql/{}/.s.PGSQL.5432'.format(os.environ.get('CLOUD_SQL_CONNECTION_NAME'))}
    )
  ).connect()

def virustracker_hash(preimage):
  return hashlib.sha256(b"VIRUSTRACKER"+preimage)

def db_execute(conn, stmt, values):
  conn.execute(stmt, **values)

def store_result(tokens, result, report_type):
  # Commit input to database
  stmt = sqlalchemy.text(
    'INSERT INTO token (token_value, report_type, report_result, location_lat, location_long) '
    'VALUES (:token_value, :report_type, :report_result, :location_lat, :location_long) '
    'ON CONFLICT (token_value) DO UPDATE '
    'SET report_type = :report_type, report_result = :report_result, location_lat = :location_lat, '
    'location_long = :location_long')
  with db_connect() as conn:
    for token in tokens:
      new_row = {}
      new_row['token_value'] = virustracker_hash(b64decode(token['preimage'])).digest()
      new_row['report_type'] = type
      new_row['report_result'] = result
      if 'lat' in token and 'long' in token:
        new_row['location_lat' ] = token['lat' ]
        new_row['location_long'] = token['long']
      else:
        new_row['location_lat' ] = None
        new_row['location_long'] = None
    
      db_execute(conn, stmt, new_row)

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
    with db_connect() as conn:
      all_tokens = conn.execute("SELECT token_value, report_type FROM token WHERE report_result = 'POSITIVE'").fetchall()
      return jsonify({'tokens': [{'value': b64encode(row[0]).decode('ascii'), 'type': row[1]} for row in all_tokens]})
  elif request.method == 'POST':
    # Validate input
    try:
      request_json = request.get_json()
      if not request_json or not isinstance(request_json, dict) or 'report' not in request_json:
        raise BadInputException("Request must contain JSON, and must have a report.")
      report = request_json['report']
      process_report(report)
    except (BadInputException, BinasciiError) as err:
      return ('Bad Request: '+err, 400)
    
    return 'Success!'
  else:
    return ('Method Not Allowed', 405)

