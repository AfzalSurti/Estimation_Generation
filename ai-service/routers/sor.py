from fastapi import APIRouter, UploadFile, File
from services.sor_parser import parse_sor_pdf

router = APIRouter()

@router.post("/parse")
async def parse_sor(file: UploadFile = File(...)):
    contents = await file.read()
    result = parse_sor_pdf(contents, file.filename)
    return result