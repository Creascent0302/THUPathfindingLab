"""One bounded HTTP exchange over docker-exec pipes; no container networking.

Only the trusted gateway calls this module. Uploaded code is never executed here.
"""

import http.client
import json
import sys


def main():
    incoming, outgoing = sys.stdin.buffer, sys.stdout.buffer
    metadata = json.loads(incoming.readline(8192))
    connection = http.client.HTTPConnection("127.0.0.1", 8000, timeout=45)
    connection.putrequest(metadata["method"], metadata["path"])
    connection.putheader("Transfer-Encoding", "chunked")
    if metadata.get("content_type"):
        connection.putheader("Content-Type", metadata["content_type"])
    connection.endheaders()
    total = 0
    while True:
        size = int(incoming.readline(16), 16)
        if not 0 <= size <= 65536:
            raise ValueError("invalid chunk")
        total += size
        if total > 130 * 1024**2:
            raise ValueError("request too large")
        chunk = incoming.read(size)
        if len(chunk) != size:
            raise ValueError("truncated request")
        connection.send(f"{size:x}\r\n".encode() + chunk + b"\r\n")
        if size == 0:
            break
    response = connection.getresponse()
    headers = {
        key.lower(): value
        for key, value in response.getheaders()
        if key.lower() in {"content-type", "content-disposition", "content-length"}
    }
    outgoing.write(
        json.dumps({"status": response.status, "headers": headers}).encode() + b"\n"
    )
    outgoing.flush()
    total = 0
    while chunk := response.read(65536):
        total += len(chunk)
        if total > 160 * 1024**2:
            raise ValueError("response too large")
        outgoing.write(chunk)
        outgoing.flush()
    connection.close()


if __name__ == "__main__":
    main()
