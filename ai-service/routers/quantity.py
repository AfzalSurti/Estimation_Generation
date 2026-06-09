from fastapi import APIRouter
from pydantic import BaseModel
from services.quantity_engine import calculate_quantities

router = APIRouter()

class ExtractionInput(BaseModel):
    estimation_type: str
    extraction_data: dict

@router.post("/calculate")
def calculate(input: ExtractionInput):
    result = calculate_quantities(input.estimation_type, input.extraction_data)
    return result