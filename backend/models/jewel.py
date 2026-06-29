from pydantic import BaseModel, Field
from datetime import datetime
from typing import List, Optional
from uuid import UUID

from .enums import MetalType, GemType, JewelStatus


class ProvenanceStep(BaseModel):
    step_name: str
    description: str
    timestamp: datetime
    document_hash: Optional[str] = None


class JewelCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    metal: MetalType
    gemstones: List[GemType] = []
    weight_grams: float = Field(..., gt=0)
    origin: Optional[str] = None
    status: JewelStatus = JewelStatus.CADASTRADA
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    image_url: Optional[str] = None


class JewelUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=1, max_length=200)
    metal: Optional[MetalType] = None
    gemstones: Optional[List[GemType]] = None
    weight_grams: Optional[float] = Field(None, gt=0)
    origin: Optional[str] = None
    status: Optional[JewelStatus] = None
    description: Optional[str] = None
    price: Optional[float] = Field(None, ge=0)
    image_url: Optional[str] = None


class JewelOut(BaseModel):
    id: str
    name: str
    metal: MetalType
    gemstones: List[GemType]
    weight_grams: float
    origin: Optional[str] = None
    status: JewelStatus
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    hash_chain_entry_hash: str
    qr_code_url: str
    certificate_worm_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    provenance: List[ProvenanceStep] = []
