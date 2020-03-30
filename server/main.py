def token(request):
  from virustracker.token import endpoint
  return endpoint(request)
def lab_certificate(request):
  from virustracker.lab_certificate import endpoint
  return endpoint(request)
