"""Data models for SOP stages, standard document templates, and generated materials."""
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class SOPField(BaseModel):
    key: str
    label: str
    type: str = "string"  # "string", "select", "number", "text"
    required: bool = True
    options: Optional[List[str]] = None
    default: Optional[str] = None


class SOPStage(BaseModel):
    stage: int
    name: str
    code: str
    description: str


class SOPTemplate(BaseModel):
    id: str
    stage: int
    code: str
    name: str
    category: str
    description: str
    template_content: str
    required_fields: List[SOPField] = Field(default_factory=list)
    is_active: bool = True


class SOPTemplatesResponse(BaseModel):
    stages: List[SOPStage]
    templates: List[SOPTemplate]


class SOPDocumentCreate(BaseModel):
    template_id: str
    user_id: str
    form_data: Dict[str, Any]


class SOPDocumentResponse(BaseModel):
    id: str
    template_id: str
    user_id: str
    document_title: str
    form_data: Dict[str, Any]
    rendered_content: str
    compliance_passed: bool = True
    status: str = "READY"
    created_at: str
    updated_at: str
