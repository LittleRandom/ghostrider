from fastapi import FastAPI
import os
import uvicorn
from app.pages.home import HomePage
from package.TestService import TestService
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# Middleware for Cross-Origin Resource Sharing (optional)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

foo = TestService("ExampleFoo")

app.include_router(foo.router)

@app.get('/root')
async def read_root():
    return {"Message": os.getcwd()}

app.mount('/', HomePage(directory='static', html=True), name='Test Console')

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)