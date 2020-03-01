import requests
import cbor
import time

from utils.response import Response

def download(url, config, logger=None):
    host, port = config.cache_server

    try:
        #20 second timeout added
        resp = requests.get(
            f"http://{host}:{port}/", timeout=10,
            params=[("q", f"{url}"), ("u", f"{config.user_agent}")])
        if resp:
            return Response(cbor.loads(resp.content))
        logger.error(f"Spacetime Response error {resp} with url {url}.")
        return Response({
            "error": f"Spacetime Response error {resp} with url {url}.",
            "status": resp.status_code,
            "url": url})
    except:
        return Response({
            "error": f"TIMEOUT with url {url}.",
            "status": 606,
            "url": url})