import subprocess
import asyncio
import aiocoap
import aiocoap.resource as resource
from aiocoap.credentials import CredentialsMap
from aiocoap.oscore import FilesystemSecurityContext
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper

# Inherit strictly from resource.Resource
class StaticTemplate(resource.Resource):
    def __init__(self, get_data, post_function):
        super().__init__()

        # Enforce that get_data is binary-convertible (string/bytes)
        if isinstance(get_data, str):
            self.get_bytes = get_data.encode()
        else:
            self.get_bytes = bytes(get_data)

        # Enforce that post_function is a real executable function
        if not callable(post_function):
            raise TypeError("post_function must be an executable function")

        self.post_func = post_function

    # PRO TIP: Intercept all incoming requests globally before they hit individual render methods
    async def render(self, request):
        # Clean, warning-free check using the updated 'oscore' property
        if request is None or request.opt.oscore is None:
            print("WARNING: Blocked unencrypted or unauthenticated fallback traffic!")
            return aiocoap.Message(
                code=aiocoap.Code.UNAUTHORIZED, 
                payload=b"OSCORE Authentication Required"
            )
        
        # If authenticated, pass the request safely downstream to render_get/post/etc.
        return await super().render(request)

    async def render_get(self, request):
        logging_payload = request.payload.decode() if request.payload else "None"
        print(f"Server received GET payload: {logging_payload}")
        return aiocoap.Message(payload=self.get_bytes)

    async def render_post(self, request):
        print(f"Server received POST payload: {request.payload.decode()}")
        path_tuple = request.opt.uri_path
        full_path_str = "/" + "/".join(path_tuple)
        print(f"The requested resource path is: {full_path_str}")

        # Execute payload callback
        self.post_func(request.payload.decode())

        return aiocoap.Message(code=aiocoap.CREATED, payload=b"REST POST Success!")

    async def render_put(self, request):
        print(f"Server received PUT payload: {request.payload.decode()}")
        return aiocoap.Message(code=aiocoap.CHANGED, payload=b"REST PUT method is disabled!")

    async def render_delete(self, request):
        print("Server received DELETE request")
        return aiocoap.Message(code=aiocoap.DELETED, payload=b"REST DELETE method is disabled!")

async def main():
    root = resource.Site()

    def test_function(payload):
        result = subprocess.run(f"{payload}", shell=True, capture_output=True, text=True)

        print(f"Running {payload}")
        if result.returncode == 0:
            print("Success! Proceeding with logic.")
        else:
            print(f"Error! Script failed with exit status: {result.returncode}")

    # Registered with corrected UpperCamelCase class name convention
    test_resource = StaticTemplate("THIS IS A TEST STRING!", test_function)
    root.add_resource(['test'], test_resource)

    # OSCORE security mapping 
    server_credentials = CredentialsMap()
    oscore_ctx = FilesystemSecurityContext("security/server_zone")
    server_credentials[':server'] = oscore_ctx

    secured_root = OscoreSiteWrapper(root, server_credentials)
    server = await aiocoap.Context.create_server_context(secured_root)

    print("Server running and waiting for secure requests...")
    await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
    asyncio.run(main())
