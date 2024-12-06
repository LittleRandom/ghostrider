import asyncio
import subprocess
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import threading
from typing import List
import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
import json
from asyncio import sleep
import time

from sse_starlette.sse import EventSourceResponse


MESSAGE_STREAM_DELAY = 0.5  # second
MESSAGE_STREAM_RETRY_TIMEOUT = 15000  # milisecond

app = FastAPI()

lock = threading.Lock()

# Buffer to hold the latest line of ping output
buffer = deque()
message_buffer = deque()
on_flag = False

# Middleware for Cross-Origin Resource Sharing (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread for running the ping command
def run_ping(buffer, timeoutEvent):
    try:
        process = subprocess.Popen(
            # ["ping", "8.8.8.8"],
            ['pytest', "--log-cli-level=INFO", "./tests"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        print("on_flag set to true")
        for line in process.stdout:
            buffer.append(line.strip())  # Store the latest line in the buffer
            print(line)
            # print(buffer)

        timeoutEvent.set()

    except Exception as e:
        print(f"Error in subprocess: {e}")


def buffer_managemant(buffer, timeoutEvent):
    q = [True, True, True]
    while q:
        with lock:
            message_buffer.clear()
            if timeoutEvent.is_set():
                q.pop()
            while buffer:
                message_buffer.append(buffer.popleft())
        time.sleep(MESSAGE_STREAM_DELAY)
    print("Exiting ... ")



@app.get("/start_ping")
async def start_ping():
    # Start the ping process in a separate thread
    if not any(thread.name == "ping_thread" for thread in threading.enumerate()):
        timeoutEvent = threading.Event()
        thread = threading.Thread(target=run_ping, args=(buffer, timeoutEvent,), name="ping_thread", daemon=True)
        thread.start()
    if not any(thread.name == "buffer_mgmt" for thread in threading.enumerate()):
        thread = threading.Thread(target=buffer_managemant, args=(buffer, timeoutEvent,), name="buffer_mgmt", daemon=True)
        thread.start()
        return JSONResponse({"status": "Ping started"})
    else:
        return JSONResponse({"status": "Ping already running"})

@app.get('/')
async def message_stream(request: Request):
    def event_generator():
        while True:
            # If client was closed the connection
            if message_buffer:
                yield '\n' + '\n'.join(message_buffer)

            time.sleep(MESSAGE_STREAM_DELAY)

    with lock: return StreamingResponse(event_generator(),  media_type="text/event-stream")

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)