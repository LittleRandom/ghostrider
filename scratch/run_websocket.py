import asyncio
import subprocess
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
import threading
from typing import List

app = FastAPI()

# Buffer to hold the latest line of ping output
buffer = deque(maxlen=1000)

# Middleware for Cross-Origin Resource Sharing (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Thread for running the ping command
def run_ping(buffer):
    count = 0
    try:
        process = subprocess.Popen(
            ["ping", "8.8.8.8"],
            # ['pytest', "--log-cli-level=10"],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )
        for line in process.stdout:
            count += 1
            buffer.append(line.strip() + str(count))  # Store the latest line in the buffer
            print(line)
            # print(buffer)
    except Exception as e:
        print(f"Error in subprocess: {e}")

# WebSocket manager
async def websocket_broadcast(buffer, websocket: WebSocket):
    try:
        await websocket.accept()
        last_sent = None  # Track the last line sent to this client
        while True:
            # if buffer and buffer[-1] != last_sent:
            #     last_sent = buffer[-1]  # Update the last sent line
            #     await websocket.send_text(last_sent)
            while buffer:
                await websocket.send_text(buffer.popleft())
            await asyncio.sleep(3)  # Prevent tight-looping
    except WebSocketDisconnect:
        pass
    except Exception as e:
        print(f"WebSocket error: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_broadcast(buffer, websocket)

@app.get("/start_ping")
async def start_ping():
    # Start the ping process in a separate thread
    if not any(thread.name == "ping_thread" for thread in threading.enumerate()):
        thread = threading.Thread(target=run_ping, args=(buffer,), name="ping_thread", daemon=True)
        thread.start()
        return JSONResponse({"status": "Ping started"})
    else:
        return JSONResponse({"status": "Ping already running"})

@app.get("/")
async def root():
    return {"message": "WebSocket server is running. Connect to /ws for live ping updates."}