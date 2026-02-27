from fastapi import FastAPI, Request
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import os
import httpx

app = FastAPI(title="Servidor do Frontend Lab")

# Backend API URL
API_BASE_URL = os.getenv("API_BASE_URL", "http://backend:8000")

# Mount the static directory
app.mount("/static", StaticFiles(directory="static"), name="static")

@app.get("/", response_class=HTMLResponse)
async def read_index():
    index_path = os.path.join("static", "index.html")
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            return f.read()
    return "<h1>index.html não encontrado na pasta static</h1>"

@app.get("/api/metrics")
async def get_metrics(view: str = "total"):
    async with httpx.AsyncClient() as client:
        response = await client.get(f"{API_BASE_URL}/financial/inadiplencia", params={"view": view})
        return response.json()

@app.get("/api/details")
async def get_details(date: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE_URL}/financial/detalhes", params={"date": date})
        return response.json()

@app.get("/api/detalhes")
async def get_detalhes(date: str):
    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.get(f"{API_BASE_URL}/financial/detalhes", params={"date": date})
        return response.json()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
