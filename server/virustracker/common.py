import os
import sqlalchemy

AHP_MIN_BYTES = 8
AHP_MAX_BYTES = 64

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

def db_execute(conn, stmt, *args, **kwargs):
  return conn.execute(stmt, *args, **kwargs)
