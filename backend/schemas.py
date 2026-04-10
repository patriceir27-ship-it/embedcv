from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime


# ── Auth ──────────────────────────────────
class UserCreate(BaseModel):
    name: str
    email: EmailStr
    password: str
    institution: Optional[str] = None


class UserLogin(BaseModel):
    email: EmailStr
    password: str


class UserOut(BaseModel):
    id: int
    name: str
    email: str
    institution: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    access_token: str
    token_type: str
    user: UserOut


# ── Projects ──────────────────────────────
class ProjectCreate(BaseModel):
    name: str
    description: Optional[str] = None
    target_mcu: str


class ProjectOut(BaseModel):
    id: int
    name: str
    description: Optional[str]
    target_mcu: str
    user_id: int
    created_at: datetime

    class Config:
        from_attributes = True


# ── Code Generation ───────────────────────
class CodeGenRequest(BaseModel):
    project_id: int
    prompt: str
    target_mcu: str
    language: str = "C"


class CodeGenOut(BaseModel):
    id: int
    project_id: int
    prompt: str
    target_mcu: str
    language: str
    generated_code: Optional[str]
    ram_estimate_kb: Optional[float]
    flash_estimate_kb: Optional[float]
    energy_estimate_mw: Optional[float]
    time_complexity: Optional[str]
    compilation_status: Optional[str]
    compilation_notes: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
