import main
import unittest
import json

class TestTokens(unittest.TestCase):

  def test_process_report(self):
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
    print(token)

if __name__ == "__main__":
  unittest.main()


