def token(request):
  import virustracker.token
  return token.endpoint(request)
def lab_certificate(request):
  import virustracker.lab_certificate
  return lab_certificate.endpoint(request)
