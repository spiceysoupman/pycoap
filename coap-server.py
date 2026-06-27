import os
import subprocess
import logging
import asyncio
import cbor2
import cbor_diag
import aiocoap
import aiocoap.resource
import aiocoap.credentials
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper
from pathlib import Path
from urllib.parse import urlparse
from aiocoap.numbers.constants import TransportTuning

# Define custom radio tuning
radio_tuning = TransportTuning(
    ACK_TIMEOUT=20.0,
    ACK_RANDOM_FACTOR=2,
    MAX_RETRANSMIT=2
)

# Environment/globals, functions and classes 
os.chdir("security")
cred_path = "server.cred.diag"
logger = logging.getLogger("server-log")

def example_post_function(payload):
        return

        result = subprocess.run(f"{payload}", shell=True, capture_output=True, text=True)
        print(f"Running {payload}")
        if result.returncode == 0:
            print("Success! Proceeding with logic.")
        else:
            print(f"Error! Script failed with exit status: {result.returncode}")

# TODO: Add function for managing server/client pairs in JSON. Add function for generating/pairing/removing
def create_credentials():
    try:
        os.mkdir("security")
    except FileExistsError:
        pass

def load_credentials(file_path: str) -> aiocoap.credentials.CredentialsMap:
    """Reads the EDN configuration file, parses it via CBOR,
    and returns a populated aiocoap CredentialsMap.
    """
    # Turn EDN text into binary CBOR then load into dict
    config_path = Path(file_path)
    edn_text = config_path.read_text()
    cbor_payload = cbor_diag.diag2cbor(edn_text)
    parsed_dict = cbor2.loads(cbor_payload)

    # Populate and return the credentials mapping store
    cred_store = aiocoap.credentials.CredentialsMap()
    cred_store.load_from_dict(parsed_dict)
    return cred_store

def set_default_logging_level():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.getLogger("coap-server").setLevel(logging.INFO)
    logging.getLogger("coap-context").setLevel(logging.INFO)
    logging.getLogger("coap-security").setLevel(logging.INFO)

class StaticTemplate(aiocoap.resource.Resource):
    def __init__(self, get_data, post_function):
        super().__init__()
        if isinstance(get_data, str):
            self.get_bytes = get_data.encode()
        else:
            self.get_bytes = bytes(get_data)
        
        if not callable(post_function):
            raise TypeError("post_function must be an executable function")
        else:
            self.post_func = post_function

    async def render(self, request):
        logger.info(f"Server received {request.code.name} request for resource {"".join(urlparse(request.get_request_uri()).path)}")
        logged_payload = request.payload.decode()
        if logged_payload is not None and logged_payload != "":
            logger.info(f"Server received payload: {request.payload.decode()}")
        return await super().render(request)
    
    async def render_get(self, request):
        return aiocoap.Message(code=aiocoap.GET, payload=self.get_bytes, transport_tuning=radio_tuning)

    async def render_post(self, request):
        self.post_func(request)
        return aiocoap.Message(code=aiocoap.CREATED, payload=b"POST method called successfully!", transport_tuning=radio_tuning)

    async def render_put(self, request):
        logger.warning(f"Server received PUT request while it is disabled")
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"PUT method is disabled!", transport_tuning=radio_tuning)

    async def render_delete(self, request):
        logger.warning("Server received DELETE request while it is disabled")
        return aiocoap.Message(code=aiocoap.DELETED, payload=b"DELETE method is disabled!", transport_tuning=radio_tuning)

class VerboseSite(aiocoap.resource.Site):
    def add_resource(self, path, resource):
        logger.info(f"Created resource at /{"/".join(path)} with GET payload size of {len(resource.get_bytes)} bytes.")

        return super().add_resource(path, resource)

async def main():
    set_default_logging_level()
    site = VerboseSite()

    example_resource = StaticTemplate("Helllo world!", example_post_function)
    site.add_resource(['example'], example_resource)

    oscore_credentials = load_credentials(cred_path)
    logger.info(f"Loaded OSCORE credentials from {cred_path}")

    secure_site = OscoreSiteWrapper(site, oscore_credentials)
    context = await aiocoap.Context.create_server_context(site=secure_site, server_credentials=oscore_credentials)

    logger.info("Server started")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\nServer terminated by user.")

