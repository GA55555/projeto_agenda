import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class DocumentoOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    paciente_id: uuid.UUID
    nome_original: str
    tipo_mime: str
    extensao: str
    sha256: str
    tamanho_bytes: int
    enviado_por_usuario_id: uuid.UUID
    criado_em: datetime


class DocumentosPagina(BaseModel):
    itens: list[DocumentoOut]
    total: int
    limite: int
    offset: int
