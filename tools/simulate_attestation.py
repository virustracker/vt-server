#!/usr/bin/env python3

import hashlib
import hmac
from base64 import b64encode, b64decode

import requests

def make_ahp(preimages, length=9):
  m = hashlib.sha256()
  for pi in preimages:
    m.update(pi)
  return m.digest()[:length]

def make_attestation(ahp, result, lab_key):
  m = hmac.new(lab_key, digestmod='sha256')
  m.update(ahp)
  m.update(result.encode('ASCII'))
  return m.digest()

# This step is done in the patient's app just before the test.
preimages = [b64decode('ABCDEFGHIJKLMNOPQRSTUVWXYZ+++++++++++++++++=')]
ahp = make_ahp(preimages)
print('ahp is ' + b64encode(ahp).decode('ascii'))

# This step is done by the lab personnel once the test result is available.
result = 'NEGATIVE'
lab_id = 1
lab_key = b'wubwub'
arguments = {
  'result': result,
  'lab_id': lab_id,
  'attestation': b64encode(make_attestation(ahp, result, lab_key)).decode('ascii')
}
response = requests.put('https://europe-west1-fabled-emissary-272419.cloudfunctions.net/vt-server-lab-certificate-master/' + b64encode(ahp, b'-_').decode('ascii'), json = arguments)
print(response.status_code)
print(response.text)
