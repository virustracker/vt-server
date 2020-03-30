def token(request):
  from token import token_endpoint
  return token_endpoint(request)
def lab_certificate(request):
  from lab_certificate import lab_certificate_endpoint
  return lab_certificate_endpoint(request)
