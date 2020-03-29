import unittest
import hashlib
import json
import mock
import server

from base64 import b64encode, b64decode

DB=[]

def mock_execute(conn, stmt, values):
  DB.append(values) 

class TestTokens(unittest.TestCase):

  @mock.patch('server.main.db_execute', side_effect=mock_execute)
  @mock.patch('server.main.db_connect')
  def test_process_report(self, _, __):
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
    server.main.process_report(token)
    preimage = "0000000000000000000000=="
    token_value = hashlib.sha256(b"VIRUSTRACKER"+b64decode(preimage)).digest()
    self.assertEqual(token_value, DB[0]['token_value'])


  def test_process_report_preimage_formaterror(self):
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
    with self.assertRaises(Exception):
      server.main.process_report(token)

if __name__ == "__main__":
  unittest.main()


