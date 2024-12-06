import pytest

import asyncio
import subprocess
from collections import deque
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, APIRouter
from fastapi.responses import JSONResponse
import threading
from typing import List
import uvicorn
from fastapi import FastAPI, Request
import fastapi
from fastapi.responses import StreamingResponse
import json
from asyncio import sleep
import time

from sse_starlette.sse import EventSourceResponse


# Wrapper to run function in different thread
# to not disturb main __Flask__ app.
def threaded(fn):
    def wrapper(*args, **kwargs):
        thread = threading.Thread(target=fn, args=args, kwargs=kwargs)
        thread.start()
        return thread
    return wrapper


MESSAGE_STREAM_DELAY = 0.5  # second
MESSAGE_STREAM_RETRY_TIMEOUT = 15000  # milisecond


# lock = threading.Lock()

# Buffer to hold the latest line of ping output
# buffer = deque()
# message_buffer = deque()


class TestService:

    log_cli_level = None
    buffer = deque()
    lock = threading.Lock()
    message_buffer = deque()

    def __init__(self, name: str):
        self.name = name
        self.router = APIRouter()
        # self.router.add_api_route("/tests", self., methods=["GET"])
        self.router.add_api_route("/tests/start", self.start, methods=["GET"])
        self.router.add_api_route("/tests/log", self.live_stream, methods=["GET"])
        # self.path = "tests"

    def start(self):
        # Check that none of the previous threads are running
        if all(e in threading.enumerate() for e in ["run_test", "buffer_mgnt"]) == False:
            # Clear old buffer values.
            self.message_buffer.clear()
            self.buffer.clear()
            # Create event to close buffer management thread from the run_test thread.
            timeoutEvent = threading.Event()
            run_test_thread = threading.Thread(target=self.__run_test, args=(self.buffer, timeoutEvent,), name="run_test", daemon=True)
            buffer_mgnt_thread = threading.Thread(target=self.__buffer_managemant, args=(self.buffer, timeoutEvent,), name="buffer_mgnt", daemon=True)
            run_test_thread.start()
            buffer_mgnt_thread.start()
            return JSONResponse({"status": "Ping started"})
        else:
            # If a previous thread is still running then do not start new threads.
            return JSONResponse({"status": "Ping already running"})

    async def live_stream(self, request: Request):
        def event_generator():
            while self.message_buffer:
                # If client was closed the connection
                if self.message_buffer:
                    yield '\n' + '\n'.join(self.message_buffer)

                time.sleep(MESSAGE_STREAM_DELAY)
        with self.lock: return StreamingResponse(event_generator(),  media_type="text/event-stream")


    def __buffer_managemant(self, buffer, timeoutEvent):
        q = [False, True, False]
        while q:
            with self.lock:
                self.message_buffer.clear()
                while buffer:
                    self.message_buffer.append(buffer.popleft())
                if timeoutEvent.is_set():
                    if q.pop():
                        print("Message event END")
                        self.message_buffer.append("\n")
                        self.message_buffer.append("\n")
            time.sleep(MESSAGE_STREAM_DELAY)
        print("Exiting ... ")


    # Thread for running the ping command
    def __run_test(self, buffer, timeoutEvent):
        try:
            process = subprocess.Popen(
                # ["ping", "8.8.8.8"],
                ['pytest', "--log-cli-level=INFO", "./tests"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1
            )
            for line in process.stdout:
                buffer.append(line.strip())  # Store the latest line in the buffer
                print(line)
                # print(buffer)

            print("timeoutEvent set to true")
            timeoutEvent.set()

        except Exception as e:
            print(f"Error in subprocess: {e}")


    def set_log_level(self, level):
        self.log_cli_level = level