import sys
import os
import asyncio
import aiocoap
import aiocoap.credentials
from pathlib import Path
import cbor2
import cbor_diag

os.chdir("security")
cred_path = "./client.cred.diag"

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

async def send_rest_request(method_verb, payload_str=None):
    target_uri = sys.argv[1]

    oscore_credentials = load_security_credentials(cred_path)
    context = await aiocoap.Context.create_client_context()
    context.client_credentials = oscore_credentials

    payload_bytes = payload_str.encode() if payload_str else b""
    req = aiocoap.Message(
        code=method_verb,
        uri=target_uri,
        payload=payload_bytes
    )

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
