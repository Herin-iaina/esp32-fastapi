from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import json
import os
from typing import Optional

router = APIRouter()

DATA_FILE = "parameters.json"

class ParameterModel(BaseModel):
    temperature: float
    humidity: float
    start_date: str
    stat_stepper: bool
    number_stepper: int
    espece: str
    timetoclose: Optional[int] = None

def get_current_parameters():
    if not os.path.exists(DATA_FILE):
        # Default values
        return {
            "temperature": 25.0,
            "humidity": 60.0,
            "start_date": "2024-01-01T00:00",
            "stat_stepper": False,
            "number_stepper": 3,
            "espece": "option1",
            "timetoclose": None
        }
    try:
        with open(DATA_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

@router.get("/api/parameter", response_model=ParameterModel)
async def read_parameters():
    return get_current_parameters()

@router.post("/parameter")
async def update_parameters(params: ParameterModel):
    try:
        with open(DATA_FILE, "w") as f:
            json.dump(params.model_dump(), f, indent=4)
        return {"message": "Parameters updated successfully", "data": params}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
