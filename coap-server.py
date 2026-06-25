import os
import subprocess
import logging
import asyncio
import aiocoap
import aiocoap.resource
import aiocoap.credentials
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper
from pathlib import Path
import cbor2
import cbor_diag

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

def load_security_credentials(file_path: str) -> aiocoap.credentials.CredentialsMap:
    """Reads the EDN configuration file, parses it via CBOR,
    and returns a populated aiocoap CredentialsMap.
    """
    config_path = Path(file_path)

    # Compile the Extended Diagnostic Notation (EDN) text into binary CBOR
    edn_text = config_path.read_text()
    cbor_payload = cbor_diag.diag2cbor(edn_text)

    # Decode binary CBOR into a native Python dictionary with correct string keys
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
        return await super().render(request)
    
    async def render_get(self, request):
        logging_payload = request.payload.decode() if request.payload else None
        if logging_payload is not None:
            logger.info(f"Server received GET payload: {logging_payload}")
        return aiocoap.Message(payload=self.get_bytes)

    async def render_post(self, request):
        path_tuple = request.opt.uri_path
        full_path_str = "/" + "/".join(path_tuple)
        logger.info(f"Server received POST payload: {request.payload.decode()}")
        logger.info(f"The requested resource path is: {full_path_str}")
        self.post_func(request.payload.decode())
        return aiocoap.Message(code=aiocoap.CREATED, payload=b"POST method called successfully!")

    async def render_put(self, request):
        logger.warning(f"Server received PUT payload: {request.payload.decode()}")
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"PUT method is disabled!")

    async def render_delete(self, request):
        logger.warning("Server received DELETE request")
        return aiocoap.Message(code=aiocoap.DELETED, payload=b"DELETE method is disabled!")

class VerboseSite(aiocoap.resource.Site):
    async def render_to_pipe(self, pipe):
        request = pipe.request
        logger.info(f"Server received request for resource at: /{"/".join(request.opt.uri_path)}")
        
        return await super().render_to_pipe(pipe)
    
    async def add_resource(self, path, resource):
        logger.info(f"Created GET resource at /{"/".join(path)} with size of {len(self.get_bytes)} bytes.")

        return super().add_resource(path, resource)

async def main():
    set_default_logging_level()
    site = VerboseSite()

    example_resource = StaticTemplate("Helllo world!", example_post_function)
    site.add_resource(['example'], example_resource)

    oscore_credentials = load_security_credentials(cred_path)
    logger.info(f"Loaded OSCORE credentials from {cred_path}")

    secure_site = OscoreSiteWrapper(site, oscore_credentials)
    context = await aiocoap.Context.create_server_context(site=secure_site, server_credentials=oscore_credentials, transports=["udp6"])

    logger.warning("Server started")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer terminated by user.")
