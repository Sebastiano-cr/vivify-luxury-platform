from fastapi import APIRouter, HTTPException, status
from datetime import datetime, timezone

from ..storage.db import fetchone, execute
from ..storage.hashchain import append_jewel_entry
from ..core.certificate import generate_certificate, store_certificate_worm
from ..config import SOC_GATEWAY_URL

router = APIRouter(prefix="/certificates", tags=["certificates"])


@router.post("/{jewel_id}")
def issue_certificate(jewel_id: str):
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Jewel not found")
    if row.get("certificate_worm_key"):
        raise HTTPException(status_code=409, detail="Certificate already issued")

    cert = generate_certificate(jewel_id, SOC_GATEWAY_URL)
    worm_key = store_certificate_worm(jewel_id, cert)

    execute(
        "UPDATE jewels SET certificate_worm_key = ?, updated_at = ? WHERE id = ?",
        (worm_key, datetime.now(timezone.utc).isoformat(), jewel_id),
    )

    append_jewel_entry(
        event_type="vivify.certificate.issued",
        jewel_id=jewel_id,
        metadata={
            "action": "certificado_emitido",
            "jewel_id": jewel_id,
            "worm_key": worm_key,
        },
    )

    return {
        "jewel_id": jewel_id,
        "certificate_id": cert["certificate_id"],
        "worm_key": worm_key,
        "verification_url": cert["verification_url"],
        "issued_at": cert["issued_at"],
    }


@router.get("/{jewel_id}")
def get_certificate(jewel_id: str):
    row = fetchone("SELECT * FROM jewels WHERE id = ?", (jewel_id,))
    if not row:
        raise HTTPException(status_code=404, detail="Jewel not found")
    if not row.get("certificate_worm_key"):
        raise HTTPException(status_code=404, detail="Certificate not yet issued")

    cert = generate_certificate(jewel_id, SOC_GATEWAY_URL)
    return cert
