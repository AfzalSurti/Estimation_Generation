from fastapi import APIRouter, UploadFile, File, Form
from services.drawing_analyzer import analyze_drawing

router = APIRouter()

@router.post("/analyze")
async def analyze(file: UploadFile = File(...), estimation_type: str = Form(...)): 
    contents = await file.read()
    result = analyze_drawing(contents, file.filename, estimation_type)
    return result