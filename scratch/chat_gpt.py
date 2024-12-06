import asyncio
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from threading import Thread, Lock
from subprocess import Popen, PIPE
from typing import Optional
import uvicorn

app = FastAPI()

# Shared variables
ping_process: Optional[Popen] = None
latest_line = ""
# lock = Lock()

def run_ping():
    """Run the ping command and update the latest_line variable."""
    global ping_process, latest_line

    with Popen(["ping", "8.8.8.8"], stdout=PIPE, stderr=PIPE, text=True) as process:
        ping_process = process
        for line in process.stdout:
            print(line)
            # with lock:
            latest_line = line.strip()

@app.get("/start_ping")
async def start_ping():
    """Start the ping command."""
    global ping_process
    if ping_process and ping_process.poll() is None:
        return {"status": "Ping is already running."}

    thread = Thread(target=run_ping, daemon=True)
    thread.start()
    return {"status": "Ping started."}

@app.get("/stream")
async def stream():
    """Stream the latest line of the ping output using Server-Sent Events."""
    async def event_generator():
        global latest_line
        while True:
            # with lock:
            data = latest_line
            yield f"data: {data}\n\n"
            await asyncio.sleep(2)  # Adjust the delay if needed

    return StreamingResponse(event_generator(), media_type="text/event-stream")


if __name__ == "__main__":
    uvicorn.run(app, host="localhost", port=8000)