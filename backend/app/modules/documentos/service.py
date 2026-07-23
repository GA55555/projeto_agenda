"""Upload, catalogo e download de documentos privados sob RLS."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import tempfile
import uuid

from fastapi import UploadFile
from sqlalchemy import event, func, select, text
from sqlalchemy.orm import Session

from app.core.config import settings
from app.modules.audit import service as audit_service
from app.modules.audit.models import TIPO_DOCUMENTO_BAIXADO, TIPO_DOCUMENTO_ENVIADO
from app.modules.auth.dependencies import CurrentUser
from app.modules.documentos.exceptions import (
    ArmazenamentoIndisponivel,
    CotaDocumentosExcedida,
    DocumentoInvalido,
    DocumentoMuitoGrande,
)
from app.modules.documentos.models import DocumentoPaciente
from app.modules.documentos.sanitizer import sanitizar_arquivo
from app.modules.documentos.validation import (
    detectar_formato,
    extensao_canonica,
    mime_canonico,
    normalizar_nome_original,
    validar_extensao,
)
from app.modules.pacientes.models import Paciente

CHUNK_UPLOAD = 1024 * 1024
CHAVE_RE = re.compile(r"^[0-9a-f]{2}/[0-9a-f]{32}\.(pdf|docx|jpg|png)$")


def _raiz() -> Path:
    configurado = settings.documentos_dir.strip()
    if not configurado:
        raise ArmazenamentoIndisponivel("Diretorio privado nao configurado.")
    raiz = Path(configurado).resolve()
    if raiz.parent == raiz or raiz == Path.cwd().resolve():
        raise ArmazenamentoIndisponivel("Diretorio privado amplo demais.")
    try:
        raiz.mkdir(parents=True, exist_ok=True, mode=0o700)
        os.chmod(raiz, 0o700)
        temporarios = raiz / ".tmp"
        temporarios.mkdir(exist_ok=True, mode=0o700)
        os.chmod(temporarios, 0o700)
    except OSError as exc:
        raise ArmazenamentoIndisponivel("Volume privado indisponivel.") from exc
    return raiz


def _resolver_chave(chave: str) -> Path:
    if not CHAVE_RE.fullmatch(chave) or PurePosixPath(chave).is_absolute():
        raise ArmazenamentoIndisponivel("Chave de armazenamento invalida.")
    raiz = _raiz()
    destino = (raiz / Path(*PurePosixPath(chave).parts)).resolve()
    if raiz not in destino.parents:
        raise ArmazenamentoIndisponivel("Caminho fora do volume privado.")
    return destino


def _receber(upload: UploadFile, destino: Path) -> int:
    total = 0
    with destino.open("xb") as arquivo:
        os.chmod(destino, 0o600)
        while bloco := upload.file.read(CHUNK_UPLOAD):
            total += len(bloco)
            if total > settings.documentos_tamanho_max_bytes:
                raise DocumentoMuitoGrande("Arquivo excede o limite de 20 MB.")
            arquivo.write(bloco)
    if total == 0:
        raise DocumentoInvalido("Arquivo vazio.")
    return total


def _sha256(caminho: Path) -> str:
    digest = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(CHUNK_UPLOAD), b""):
            digest.update(bloco)
    return digest.hexdigest()


def _fsync_diretorio(caminho: Path) -> None:
    """Persiste a entrada do rename antes do commit dos metadados no PostgreSQL."""
    if os.name != "posix":
        return
    descritor = os.open(caminho, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descritor)
    finally:
        os.close(descritor)


def _remover_apos_rollback(caminho: Path) -> None:
    """Rollback do BD nao pode ser mascarado por falha secundaria de cleanup."""
    try:
        caminho.unlink(missing_ok=True)
        _fsync_diretorio(caminho.parent)
    except OSError:
        # Um reconciliador de volume/BD entra na Fase 8; aqui preserva o erro causal.
        pass


def enviar(
    db: Session,
    user: CurrentUser,
    paciente_id: uuid.UUID,
    upload: UploadFile,
) -> DocumentoPaciente | None:
    paciente = db.get(Paciente, paciente_id)
    if paciente is None:
        return None

    nome = normalizar_nome_original(upload.filename)
    raiz = _raiz()
    try:
        # Original e artefato intermediario vivem no /tmp (tmpfs no Docker),
        # nunca no volume persistente. So a versao reconstruida e copiada ao final.
        with tempfile.TemporaryDirectory(prefix="agenda-upload-") as tmp:
            pasta = Path(tmp)
            bruto = pasta / "entrada"
            _receber(upload, bruto)
            formato = detectar_formato(bruto)
            validar_extensao(nome, formato)
            sanitizado = pasta / f"sanitizado{extensao_canonica(formato)}"
            sanitizar_arquivo(
                bruto, sanitizado, formato, trava=raiz / ".tmp" / ".sanitizacao.lock"
            )
            tamanho = sanitizado.stat().st_size
            if tamanho <= 0 or tamanho > settings.documentos_tamanho_max_bytes:
                raise DocumentoMuitoGrande("Arquivo reconstruido excede o limite de 20 MB.")

            # Serializa com apagar/arquivar: o paciente pode ter sido removido
            # durante a sanitizacao. Revalidar sob lock evita FK/500 e arquivo orfao.
            paciente = db.execute(
                select(Paciente).where(Paciente.id == paciente_id).with_for_update()
            ).scalar_one_or_none()
            if paciente is None:
                return None

            # Serializa a verificacao de cota entre os dois workers do backend.
            db.execute(
                text("SELECT pg_advisory_xact_lock(hashtextextended(:tenant_id, 0))"),
                {"tenant_id": str(user.tenant_id)},
            )
            usado = db.execute(
                select(func.coalesce(func.sum(DocumentoPaciente.tamanho_bytes), 0))
            ).scalar_one()
            if int(usado) + tamanho > settings.documentos_cota_tenant_bytes:
                raise CotaDocumentosExcedida("Cota de documentos da clinica excedida.")

            token = uuid.uuid4().hex
            extensao = extensao_canonica(formato)
            chave = f"{token[:2]}/{token}{extensao}"
            destino = _resolver_chave(chave)
            destino.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            os.chmod(destino.parent, 0o700)
            parcial = destino.with_name(f".{destino.name}.{uuid.uuid4().hex}.partial")
            try:
                with sanitizado.open("rb") as origem, parcial.open("xb") as alvo:
                    os.chmod(parcial, 0o600)
                    shutil.copyfileobj(origem, alvo, length=CHUNK_UPLOAD)
                    alvo.flush()
                    os.fsync(alvo.fileno())
                os.replace(parcial, destino)
                try:
                    _fsync_diretorio(destino.parent)
                    event.listen(
                        db,
                        "after_rollback",
                        lambda _session: _remover_apos_rollback(destino),
                        once=True,
                    )
                except Exception:
                    _remover_apos_rollback(destino)
                    raise
            finally:
                parcial.unlink(missing_ok=True)

            # Se a transacao falhar depois da gravacao atomica, nao deixa binario orfao.
            documento = DocumentoPaciente(
                id=uuid.uuid4(),
                tenant_id=user.tenant_id,
                paciente_id=paciente_id,
                enviado_por_usuario_id=user.id,
                nome_original=nome,
                chave_armazenamento=chave,
                tipo_mime=mime_canonico(formato),
                extensao=extensao,
                sha256=_sha256(destino),
                tamanho_bytes=tamanho,
            )
            db.add(documento)
            audit_service.registrar_evento(
                db,
                tenant_id=user.tenant_id,
                tipo_evento=TIPO_DOCUMENTO_ENVIADO,
                entidade="documento_paciente",
                entidade_id=documento.id,
                ator_usuario_id=user.id,
                payload={"tipo": formato, "tamanho": tamanho},
            )
            db.flush()
            return documento
    except OSError as exc:
        raise ArmazenamentoIndisponivel("Falha ao gravar no volume privado.") from exc
    finally:
        upload.file.close()


def listar(
    db: Session,
    paciente_id: uuid.UUID,
    *,
    limite: int,
    offset: int,
) -> tuple[list[DocumentoPaciente], int] | None:
    if db.get(Paciente, paciente_id) is None:
        return None
    filtro = DocumentoPaciente.paciente_id == paciente_id
    total = db.execute(
        select(func.count()).select_from(DocumentoPaciente).where(filtro)
    ).scalar_one()
    itens = list(
        db.execute(
            select(DocumentoPaciente)
            .where(filtro)
            .order_by(DocumentoPaciente.criado_em.desc(), DocumentoPaciente.id.desc())
            .limit(limite)
            .offset(offset)
        ).scalars()
    )
    return itens, total


def preparar_download(
    db: Session, user: CurrentUser, documento_id: uuid.UUID
) -> tuple[DocumentoPaciente, Path] | None:
    documento = db.get(DocumentoPaciente, documento_id)
    if documento is None:
        return None
    caminho = _resolver_chave(documento.chave_armazenamento)
    if not caminho.is_file():
        raise ArmazenamentoIndisponivel("Documento nao encontrado no volume privado.")
    if _sha256(caminho) != documento.sha256:
        # Corrupcao/troca no volume nunca e entregue silenciosamente ao prontuario.
        raise ArmazenamentoIndisponivel("Integridade do documento nao confere.")
    audit_service.registrar_evento(
        db,
        tenant_id=user.tenant_id,
        tipo_evento=TIPO_DOCUMENTO_BAIXADO,
        entidade="documento_paciente",
        entidade_id=documento.id,
        ator_usuario_id=user.id,
    )
    return documento, caminho
