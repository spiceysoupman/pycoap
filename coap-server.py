import subprocess
import asyncio
import aiocoap
import aiocoap.resource as resource
from aiocoap.credentials import CredentialsMap
from aiocoap.oscore import FilesystemSecurityContext
from aiocoap.oscore_sitewrapper import OscoreSiteWrapper

# Inherit strictly from resource.Resource
class static_template(resource.Resource):
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

async def main():
	root = resource.Site()

	# Define your custom callback function
	# YOUR FUNCTION ALWAYS HAS TO EXPECT A REFERANCE TO THE INVOKING OBJECT
	def test_function(payload):
		result = subprocess.run(f"bash {payload}", shell=True)

		print(f"Running {payload}")
		if result.returncode == 0:
			print("Success! Proceeding with logic.")
		else:
			print(f"Error! Script failed with exit status: {result.returncode}")

	# Test resouce instances. RECONFIGURE THIS WHEN ADDING MORE RESOURCES!
	test_resource = static_template("THIS IS A TEST STRING!", test_function)
	root.add_resource(['test'], test_resource)

	# OSCORE security
	server_credentials = CredentialsMap()
	oscore_ctx = FilesystemSecurityContext("security/server_zone")
	server_credentials[':server'] = oscore_ctx

	secured_root = OscoreSiteWrapper(root, server_credentials)
	server = await aiocoap.Context.create_server_context(secured_root)

	print("Server running and waiting for secure requests...")
	await asyncio.get_running_loop().create_future()

if __name__ == "__main__":
	asyncio.run(main())
