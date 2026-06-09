import sys
import asyncio
import aiocoap
import aiocoap.numbers.constants as cc
from aiocoap.oscore import FilesystemSecurityContext

async def send_rest_request(method_verb, payload_str=None):
    # Network tuning
    cc.TransportTuning.ACK_TIMEOUT = 25.0
    cc.TransportTuning.MAX_RETRANSMIT = 2

    # Client and OSCORE setup
    client = await aiocoap.Context.create_client_context()
    oscore_ctx = FilesystemSecurityContext("security/my_zone")
    target_uri = sys.argv[1]
    client.client_credentials[target_uri] = oscore_ctx

    payload_bytes = payload_str.encode() if payload_str else b""

    req = aiocoap.Message(
        code=method_verb,
        uri=target_uri,
        payload=payload_bytes
    )

    try:
        res = await client.request(req).response
        print(f"[{method_verb.name}] Response Code: {res.code} | Payload: {res.payload.decode()}")
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await client.shutdown()

async def main():
	# METHOD CHECK
	method = sys.argv[2]
	payload = sys.argv[3]
	if method == "GET":
		await send_rest_request(aiocoap.GET)
	elif method == "POST":
		await send_rest_request(aiocoap.POST, payload) #'{"item": "sensor_1", "status": "active"}')
	elif method == "PUT":
		await send_rest_request(aiocoap.PUT, payload) #'{"status": "inactive"}')
	elif method == "DELETE":
		await send_rest_request(aiocoap.DELETE)

if __name__ == "__main__":
	asyncio.run(main())

