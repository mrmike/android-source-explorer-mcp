import asyncio
import json
import os
from pathlib import Path

class LSPClient:
    def __init__(self, command: list[str], root_uri: str):
        self.command = command
        self.root_uri = root_uri
        self.process = None
        self.id_counter = 0
        self.requests = {}
        self.reader_task = None

    async def start(self):
        self.process = await asyncio.create_subprocess_exec(
            *self.command,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.DEVNULL
        )
        self.reader_task = asyncio.create_task(self._read_stdout())
        
        # Initialize the LSP
        await self.send_request("initialize", {
            "processId": os.getpid(),
            "rootUri": self.root_uri,
            "capabilities": {
                "textDocument": {
                    "definition": {"dynamicRegistration": True},
                    "references": {"dynamicRegistration": True},
                    "hover": {"dynamicRegistration": True}
                }
            }
        })
        await self.send_notification("initialized", {})

    async def stop(self):
        if self.process:
            self.process.terminate()
            await self.process.wait()
        if self.reader_task:
            self.reader_task.cancel()

    async def _read_stdout(self):
        try:
            while not self.process.stdout.at_eof():
                line = await self.process.stdout.readline()
                if line.startswith(b"Content-Length:"):
                    length = int(line.split(b":")[1].strip())
                    await self.process.stdout.readline()  # skip empty line
                    body = await self.process.stdout.readexactly(length)
                    response = json.loads(body)
                    
                    if "id" in response:
                        req_id = response["id"]
                        if req_id in self.requests:
                            self.requests[req_id].set_result(response)
        except asyncio.CancelledError:
            pass
        except Exception as e:
            print(f"LSP reader error: {e}")

    async def send_request(self, method: str, params: dict):
        self.id_counter += 1
        req_id = self.id_counter
        request = {
            "jsonrpc": "2.0",
            "id": req_id,
            "method": method,
            "params": params
        }
        
        future = asyncio.get_event_loop().create_future()
        self.requests[req_id] = future
        
        body = json.dumps(request).encode('utf-8')
        header = f"Content-Length: {len(body)}\r\n\r\n".encode('ascii')
        self.process.stdin.write(header + body)
        await self.process.stdin.drain()
        
        return await future

    async def send_notification(self, method: str, params: dict):
        notification = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params
        }
        body = json.dumps(notification).encode('utf-8')
        header = f"Content-Length: {len(body)}\r\n\r\n".encode('ascii')
        self.process.stdin.write(header + body)
        await self.process.stdin.drain()
