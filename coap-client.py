import sys
import asyncio
import aiocoap
import aiocoap.numbers.constants as cc
from aiocoap.oscore import FilesystemSecurityContext
from aiocoap import Context

async def send_rest_request(method_verb, payload_str=None):
    cc.TransportTuning.ACK_TIMEOUT = 25.0
    cc.TransportTuning.MAX_RETRANSMIT = 2

    target_uri = sys.argv[1]

    client_oscore_context = FilesystemSecurityContext("security/client_zone")
    context = await Context.create_client_context()
    
    context.client_credentials[target_uri] = client_oscore_context
    context.client_credentials["coap://127.0.0.1/*"] = client_oscore_context
    context.client_credentials["coap://localhost/*"] = client_oscore_context
    context.client_credentials["oscore://127.0.0.1/*"] = client_oscore_context
    context.client_credentials["oscore://localhost/*"] = client_oscore_context

    payload_bytes = payload_str.encode() if payload_str else b""
    req = aiocoap.Message(
        code=method_verb,
        uri=target_uri,
        payload=payload_bytes
    )
    
    req.remote = await context.find_remote_and_set_context(req)

    try:
        res = await context.request(req).response
        print(f" [{method_verb.name}] Response Code: {res.code} | Payload: {res.payload.decode()}")
    except Exception as e:
        print(f"Error encountered: {e}")
    finally:
        await context.shutdown()

async def main():
    if len(sys.argv) < 3:
        print("Usage: python3 coap-client.py <URI> <METHOD> [PAYLOAD]")
        return

    method = sys.argv[2].upper()
    payload = sys.argv[3] if len(sys.argv) > 3 else None
    
    if method == "GET":
        await send_rest_request(aiocoap.GET)
    elif method == "POST":
        await send_rest_request(aiocoap.POST, payload)

if __name__ == "__main__":
    asyncio.run(main())
