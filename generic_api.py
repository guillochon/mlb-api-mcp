from fastapi import APIRouter, HTTPException
from datetime import datetime
router = APIRouter()


@router.get(
    "/current_date",
    operation_id="get_current_date",
    description="""
Get the current date.

Returns the current date.

Example:
- `/current_date` (returns the current date)
""",
)
async def get_current_date():
    try:
        current_date = datetime.now().strftime("%Y-%m-%d")
        return {"current_date": current_date}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    
@router.get(
    "/current_time",
    operation_id="get_current_time",
    description="""
Get the current time.

Returns the current time.

Example:
- `/current_time` (returns the current time)
""",
)
async def get_current_time():
    try:
        current_time = datetime.now().strftime("%H:%M:%S")
        return {"current_time": current_time}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))