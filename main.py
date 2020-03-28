import math
import os
import sqlalchemy
from flask import jsonify
from base64 import b64encode, b64decode
from binascii import Error as BinasciiError

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

def tokens(request):
	if request.method == 'GET':
		with db_connect() as conn:
			all_tokens = conn.execute('SELECT token, report_type FROM token WHERE report_result = "POSITIVE"').fetchall()
			return jsonify({'tokens': [{'value': b64encode(row[0]).decode('ascii'), 'type': row[1]} for row in all_tokens]})
	elif request.method == 'POST':
		# Validate input
		try:
			request_json = request.get_json()
			if not request_json or not isinstance(request_json, dict) or 'report' not in request_json:
				raise BadInputException()
			report = request_json['report']
			if not isinstance(report, dict) or not all(field in report for field in ('tokens', 'type', 'result')):
				raise BadInputException()
			tokens = report['tokens']
			type   = report['type']
			result = report['result']
			if not isinstance(tokens, list):
				raise BadInputException()
			for token in tokens:
				if not isinstance(token, dict) or 'value' not in token or not isinstance(token['value'], str):
					raise BadInputException()
				if len(token['value']) != math.ceil(TOKEN_BYTES / 3) * 4 or len(b64decode(token['value'], validate=True)) != TOKEN_BYTES:
					raise BadInputException()
				if any(latlong in token and not isinstance(token[latlong], (float, int)) for latlong in ('lat', 'long')):
					raise BadInputException()
			if not isinstance(type, str) or type not in ('SELF_REPORT', 'VERIFIED'):
				raise BadInputException()
			if not isinstance(result, str) or result not in ('UNKNOWN', 'POSITIVE', 'NEGATIVE'):
				raise BadInputException()
		except (BadInputException, BinasciiError):
			return ('Bad Request', 400)
		
		# Commit input to database
		stmt = sqlalchemy.text('INSERT INTO token (token, report_type, report_result, location_lat, location_long) VALUES (:token, :report_type, :report_result, :location_lat, :location_long) ON CONFLICT (token) DO UPDATE SET report_type = :report_type, report_result = :report_result, location_lat = :location_lat, location_long = :location_long')
		with db_connect() as conn:
			for token in tokens:
				new_row = {}
				new_row['token'] = b64decode(token['value'])
				new_row['report_type'] = type
				new_row['report_result'] = result
				if 'lat' in token and 'long' in token:
					new_row['location_lat' ] = token['lat' ]
					new_row['location_long'] = token['long']
				else:
					new_row['location_lat' ] = None
					new_row['location_long'] = None
				conn.execute(stmt, **new_row)
		
		return 'Success!'
	else:
		return ('Method Not Allowed', 405)
