from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import sor, drawing, quantity

app = FastAPI(title="BOQ AI Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(sor.router, prefix="/sor", tags=["SOR"])
app.include_router(drawing.router, prefix="/drawing", tags=["Drawing"])
app.include_router(quantity.router, prefix="/quantity", tags=["Quantity"])

@app.get("/")
def root():
    return {"status": "BOQ AI Service running"}