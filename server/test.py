import main
import unittest
import json
import mock

def mock_execute(conn, stmt, values):
  print(stmt)
  print(values)

class TestTokens(unittest.TestCase):

  @mock.patch('main.db_execute', side_effect=mock_execute)
  @mock.patch('main.db_connect')
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
    main.process_report(token)

if __name__ == "__main__":
  unittest.main()


