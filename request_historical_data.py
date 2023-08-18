from pgesmd_self_access.api import SelfAccessApi
from pgesmd_self_access.server import SelfAccessServer
from pgesmd_self_access.helpers import save_espi_xml

def main():
  pge_api = SelfAccessApi.auth('/root/auth/auth.json')
  pge_api.request_historical_data(120)
 

# Using the special variable 
# __name__
if __name__=="__main__":
  main()
