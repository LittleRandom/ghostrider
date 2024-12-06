import flask
import time
import subprocess
import threading
from collections import deque

app = flask.Flask(__name__)

MESSAGE_STREAM_DELAY = 2  # second
MESSAGE_STREAM_RETRY_TIMEOUT = 15000  # milisecond


# Buffer to hold the latest line of ping output
buffer = deque(maxlen=1000)

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
            buffer.append(line.strip() )  # Store the latest line in the buffer
            print(line)
            # print(buffer)
    except Exception as e:
        print(f"Error in subprocess: {e}")

@app.route("/start_ping", methods=[ "GET" ])
async def start_ping():
    # Start the ping process in a separate thread
    if not any(thread.name == "ping_thread" for thread in threading.enumerate()):
        thread = threading.Thread(target=run_ping, args=(buffer,), name="ping_thread", daemon=True)
        thread.start()
        return {"status": "Ping started"}
    else:
        return {"status": "Ping already running"}

async def event_stream():
    output = ""
    while buffer:
       output += buffer.popleft()
    yield output
    time.sleep(2)
    # await asyncio.sleep(MESSAGE_STREAM_DELAY)

@app.route("/stream", methods=[ "GET" ])
def stream():
    return flask.Response(
        event_stream(),
        mimetype="text/event-stream"
    )
if __name__ == "__main__":
    app.run(port=8000)