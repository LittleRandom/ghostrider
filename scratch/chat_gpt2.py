from fastapi import FastAPI, HTTPException
from fastapi.responses import StreamingResponse
import asyncio
import subprocess
from typing import AsyncIterator
from threading import Thread
import uvicorn

app = FastAPI()

# Shared log queue to hold subprocess output
log_queue = asyncio.Queue()

# Store references to active SSE listeners
listeners = []

# Function to run the OS command and write output to the log queue
async def run_command():
    process = await asyncio.create_subprocess_shell(
        "pytest --log-cli-level=10",
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        bufsize=0,
        universal_newlines=False
    )

    if not process.stdout:
        raise HTTPException(status_code=500, detail="Failed to start command.")

    async for line in process.stdout:
        print(line)
        await log_queue.put(line.strip())

    # Indicate the process has ended
    await log_queue.put(None)
    await process.wait()

# Coroutine to read logs from the queue and send them to listeners
async def broadcast_logs():
    while True:
        line = await log_queue.get()
        if line is None:
            break  # Stop broadcasting if the process ends
        for listener in listeners:
            try:
                await listener.put(line)
            except Exception:
                pass

# Function to produce SSE events for a client
async def sse_log_stream() -> AsyncIterator[str]:
    queue = asyncio.Queue()
    listeners.append(queue)
    try:
        while True:
            line = await queue.get()
            yield f"data: {line}\n\n"
    finally:
        listeners.remove(queue)

# SSE endpoint to stream logs
@app.get("/")
async def stream_logs():
    return StreamingResponse(sse_log_stream(), media_type="text/event-stream")

# Endpoint to start the OS command
@app.get("/start")
async def start_command():
    if not listeners:
        thread = Thread(target=asyncio.run, args=(broadcast_logs(),))
        thread.start()

    asyncio.create_task(run_command())
    return {"message": "Command started. Connect to /logs/stream to view logs."}

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)