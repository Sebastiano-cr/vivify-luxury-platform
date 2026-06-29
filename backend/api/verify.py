from fastapi import APIRouter, HTTPException

from ..core.certificate import verify_jewel
from ..config import SOC_GATEWAY_URL

router = APIRouter(prefix="/verify", tags=["verify"])


@router.get("/{jewel_id}")
def verify_public(jewel_id: str):
    try:
        result = verify_jewel(jewel_id, SOC_GATEWAY_URL)
        return result
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
