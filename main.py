from fastapi import FastAPI, WebSocket, WebSocketDisconnect, Request
from fastapi.middleware.cors import CORSMiddleware
from typing import List
from fastapi.responses import Response
app = FastAPI()

# CORS is only for HTTP, not WS, but fine to keep
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.middleware("http")
async def add_csp_header(request: Request, call_next):
    response: Response = await call_next(request)

    # ⚠️ For dev, you can keep this fairly relaxed:
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; "
        "connect-src 'self' ws://137.104.173.182:8081; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline'; "
        "img-src 'self' data:;"
    )

    return response

@app.get("/")
async def root():
    return {"message": "mmmmFastAPI WebSocket chat server is running"}


class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        print(f"Client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
        print(f"Client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, message: str):
        # Send the message to all connected clients
        for connection in list(self.active_connections):
            try:
                await connection.send_text(message)
            except Exception as e:
                print("Error sending to a client:", e)


manager = ConnectionManager()


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)

    try:
        while True:
            data = await websocket.receive_text()
            print(f"Received from client: {data}")

            # Broadcast whatever text we got (we'll send JSON from the frontend)
            await manager.broadcast(data)

    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        print("Unexpected error in websocket:", e)
        manager.disconnect(websocket)
        try:
            await websocket.close()
        except:
            pass
