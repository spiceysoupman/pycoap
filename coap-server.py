import os
import subprocess
import asyncio
import aiocoap
import aiocoap.resource
import aiocoap.credentials
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper
from pathlib import Path
import cbor2
import cbor_diag
import logging

os.chdir("security")
cred_path = "server.cred.diag"

def example_function(payload):
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

def verbosify():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    logging.getLogger("coap-server").setLevel(logging.INFO)
    logging.getLogger("coap-context").setLevel(logging.INFO)
    logging.getLogger("coap-server").setLevel(logging.INFO)
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
        self.post_func = post_function

    async def render_get(self, request):
        logging_payload = request.payload.decode() if request.payload else "None"
        print(f"Server received GET payload: {logging_payload}")
        return aiocoap.Message(payload=self.get_bytes)

    async def render_post(self, request):
        print(f"Server received POST payload: {request.payload.decode()}")
        path_tuple = request.opt.uri_path
        full_path_str = "/" + "/".join(path_tuple)
        print(f"The requested resource path is: {full_path_str}")
        self.post_func(request.payload.decode())
        return aiocoap.Message(code=aiocoap.CREATED, payload=b"REST POST Success!")

    async def render_put(self, request):
        print(f"Server received PUT payload: {request.payload.decode()}")
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"REST PUT method is disabled!")

    async def render_delete(self, request):
        print("Server received DELETE request")
        return aiocoap.Message(code=aiocoap.DELETED, payload=b"REST DELETE method is disabled!")

class VerboseSite(aiocoap.resource.Site):
    async def render_to_pipe(self, pipe):
        request = pipe.request
        print(f"DEBUG: Server received raw path options array: {request.opt.uri_path}")
        
        return await super().render_to_pipe(pipe)

async def main():
    #site = aiocoap.resource.Site()
    verbosify()
    site = VerboseSite()

    example_resource = StaticTemplate("Helllo world!", example_function)
    site.add_resource(['example'], example_resource)

    oscore_credentials = load_security_credentials(cred_path)
    print("Loaded OSCORE credentials:")
    print(oscore_credentials)

    secure_site = OscoreSiteWrapper(site, oscore_credentials)
    context = await aiocoap.Context.create_server_context(site=secure_site, server_credentials=oscore_credentials, transports=["udp6"])

    print("Server running...")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\nServer terminated by user.")
