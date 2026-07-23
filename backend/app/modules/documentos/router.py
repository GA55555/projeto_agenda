import uuid

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.db.deps import get_tenant_session
from app.modules.auth.dependencies import CurrentUser, get_current_user
from app.modules.documentos import service
from app.modules.documentos.exceptions import (
    ArmazenamentoIndisponivel,
    CotaDocumentosExcedida,
    DocumentoInvalido,
    DocumentoMuitoGrande,
)
from app.modules.documentos.schemas import DocumentoOut, DocumentosPagina

router = APIRouter(tags=["documentos"])


@router.post(
    "/pacientes/{paciente_id}/documentos",
    response_model=DocumentoOut,
    status_code=status.HTTP_201_CREATED,
)
def enviar_documento(
    paciente_id: uuid.UUID,
    arquivo: UploadFile = File(...),
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> DocumentoOut:
    try:
        documento = service.enviar(db, user, paciente_id, arquivo)
    except DocumentoMuitoGrande as exc:
        raise HTTPException(status_code=status.HTTP_413_CONTENT_TOO_LARGE, detail=str(exc))
    except CotaDocumentosExcedida as exc:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))
    except DocumentoInvalido:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Arquivo recusado: formato, conteudo ativo ou estrutura insegura.",
        )
    except ArmazenamentoIndisponivel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Armazenamento privado indisponivel.",
        )
    if documento is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
    return DocumentoOut.model_validate(documento)


@router.get("/pacientes/{paciente_id}/documentos", response_model=DocumentosPagina)
def listar_documentos(
    paciente_id: uuid.UUID,
    limite: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_tenant_session),
) -> DocumentosPagina:
    resultado = service.listar(db, paciente_id, limite=limite, offset=offset)
    if resultado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Paciente nao encontrado")
    itens, total = resultado
    return DocumentosPagina(itens=itens, total=total, limite=limite, offset=offset)


@router.get("/documentos/{documento_id}/download", response_class=FileResponse)
def baixar_documento(
    documento_id: uuid.UUID,
    db: Session = Depends(get_tenant_session),
    user: CurrentUser = Depends(get_current_user),
) -> FileResponse:
    try:
        resultado = service.preparar_download(db, user, documento_id)
    except ArmazenamentoIndisponivel:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Documento temporariamente indisponivel.",
        )
    if resultado is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Documento nao encontrado")
    documento, caminho = resultado
    return FileResponse(
        caminho,
        media_type=documento.tipo_mime,
        filename=documento.nome_original,
        content_disposition_type="attachment",
        headers={
            "X-Content-Type-Options": "nosniff",
            "Cache-Control": "no-store, private",
            "Content-Security-Policy": "sandbox; default-src 'none'",
            "Cross-Origin-Resource-Policy": "same-origin",
        },
    )
