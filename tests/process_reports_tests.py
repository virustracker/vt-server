import unittest
import hashlib
import json
import mock
import server.virustracker.token

from base64 import b64encode, b64decode

DB=[]

def mock_execute(conn, stmt, *args, **kwargs):
  DB.append({'args': args, 'kwargs': kwargs}) 

class TestProcessReports(unittest.TestCase):

  @mock.patch('server.virustracker.token.db_execute', side_effect=mock_execute)
  @mock.patch('server.virustracker.token.db_connect')
  def test_process_report(self, _, __):
    token = json.loads("""{
     	 "type": "SELF_REPORT",
     	 "result": "POSITIVE",
     	 "tokens": [{
     			 "preimage": "0000000000000000000000000000000000000000000="
     		 }
     	 ]
      }""")
    server.virustracker.token.process_report(token)
    preimage = "0000000000000000000000000000000000000000000="
    token_value = hashlib.sha256(b"VIRUSTRACKER"+b64decode(preimage)).digest()
    self.assertEqual(token_value, DB[0]['args'][0]['value'])


  def test_process_report_preimage_formaterror(self):
    token = json.loads("""{
     	 "type": "SELF_REPORT",
     	 "result": "POSITIVE",
     	 "tokens": [{
     			 "preimage": "0000000000000000000000="
     		 }
     	 ]
      }""")
    with self.assertRaises(Exception):
      server.virustracker.token.process_report(token)

if __name__ == "__main__":
  unittest.main()


