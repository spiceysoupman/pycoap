import subprocess
import asyncio
import aiocoap
from pathlib import Path
import cbor2
import cbor_diag

cred_path = "security/server.cred.diag"

def test_function(payload):
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
    cred_store = credentials.CredentialsMap()
    cred_store.load_from_dict(parsed_dict)
    return cred_store

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
        print("Is Decrypted OSCORE?", hasattr(request.remote, 'security_context') and request.remote.security_context is not None)
        if not hasattr(request.remote, 'security_context') or request.remote.security_context is None:
            print("Security Refusal: Request is unencrypted plaintext! Dropping packet.")
            return aiocoap.Message(code=aiocoap.Code.UNAUTHORIZED, payload=b"OSCORE Security Required")
        
        logging_payload = request.payload.decode() if request.payload else "None"
        print(f"Server received GET payload: {logging_payload}")
        return aiocoap.Message(payload=self.get_bytes)

    async def render_post(self, request):
        if not hasattr(request.remote, 'security_context') or request.remote.security_context is None:
            print("Security Refusal: Request is unencrypted plaintext! Dropping packet.")
            return aiocoap.Message(code=aiocoap.Code.UNAUTHORIZED, payload=b"OSCORE Security Required")

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

async def main():
    root = aiocoap.resource.Site()

    test_resource = StaticTemplate("THIS IS A TEST STRING!", test_function)
    root.add_resource(['test'], test_resource)

    oscore_credentials = load_security_credentials(cred_path)
    print("Loaded OSCORE credentials:")
    print(oscore_credentials)

    print("Server running...")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
