"""Regras de negocio de autenticacao.

Regras de ouro: §2.1, §4.1
Fase do roadmap: Fase 2
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.core.security import hash_password, verify_password
from app.modules.auth.dependencies import CurrentUser
from app.modules.auth.exceptions import EmailDuplicado, SenhaAtualIncorreta
from app.modules.auth.models import Usuario
from app.modules.auth.schemas import PerfilUpdate, SenhaUpdate

_UNIQUE_VIOLATION = "23505"  # Postgres: unique_violation (UNIQUE em usuarios.email)


def autenticar(db: Session, email: str, senha: str) -> Usuario | None:
    """Retorna o usuario se email+senha conferem e a conta esta ativa; senao None.

    Comparacao de senha sempre executada quando o usuario existe, para reduzir
    o sinal de tempo (nao e defesa forte, mas evita o vazamento obvio).
    """
    # Case-insensitive: o e-mail e identificador, nao texto. Cobre contas
    # legadas gravadas com maiusculas E a normalizacao do PerfilUpdate (que
    # grava minusculo). Tabela minuscula (<=5 psicologas): func.lower e barato.
    usuario = db.execute(
        select(Usuario).where(
            func.lower(Usuario.email) == email.lower(), Usuario.ativo.is_(True)
        )
    ).scalar_one_or_none()
    if usuario is None:
        return None
    if not verify_password(senha, usuario.senha_hash):
        return None
    return usuario


def atualizar_perfil(db: Session, user: CurrentUser, dados: PerfilUpdate) -> Usuario | None:
    """Atualiza nome/e-mail do PROPRIO usuario (id vem do JWT, nunca do cliente).

    `usuarios` e control-plane SEM RLS (§2.1.1) -> o escopo de seguranca e buscar
    a linha pela PK do usuario autenticado. E-mail e globalmente UNIQUE: colisao
    vira erro de dominio (409), nao 500.

    Trocar o E-MAIL e trocar o identificador de login: exige `senha_atual`
    (re-autenticacao — um cookie sequestrado nao rotaciona a conta sozinho) e
    grava evento indelevel em `auditoria` na MESMA transacao (§2.2). Requer
    sessao com contexto de tenant (a auditoria vive sob RLS).
    """
    usuario = db.get(Usuario, user.id)
    if usuario is None:
        return None
    campos = dados.model_dump(exclude_unset=True)
    campos.pop("senha_atual", None)  # credencial de re-auth, nunca um campo gravavel

    email_anterior = usuario.email
    troca_email = "email" in campos and campos["email"] != email_anterior
    if troca_email:
        if not dados.senha_atual or not verify_password(dados.senha_atual, usuario.senha_hash):
            raise SenhaAtualIncorreta()

    for campo, valor in campos.items():
        setattr(usuario, campo, valor)
    if campos:
        usuario.atualizado_em = datetime.now(timezone.utc)
    try:
        db.flush()
    except IntegrityError as exc:
        if getattr(exc.orig, "sqlstate", None) == _UNIQUE_VIOLATION:
            raise EmailDuplicado(campos.get("email", "")) from exc
        raise

    if troca_email:
        # Import local: evita ciclo auth <-> audit no import dos modulos.
        from app.modules.audit import service as audit_service
        from app.modules.audit.models import TIPO_PERFIL_EMAIL_ALTERADO

        audit_service.registrar_evento(
            db,
            tenant_id=user.tenant_id,
            tipo_evento=TIPO_PERFIL_EMAIL_ALTERADO,
            entidade="usuario",
            entidade_id=usuario.id,
            ator_usuario_id=user.id,
            payload={"email_anterior": email_anterior, "email_novo": usuario.email},
        )
    return usuario


def trocar_senha(db: Session, user_id: uuid.UUID, dados: SenhaUpdate) -> Usuario | None:
    """Troca a senha do proprio usuario apos conferir a senha atual (§4.1)."""
    usuario = db.get(Usuario, user_id)
    if usuario is None:
        return None
    if not verify_password(dados.senha_atual, usuario.senha_hash):
        raise SenhaAtualIncorreta()
    usuario.senha_hash = hash_password(dados.senha_nova)
    usuario.atualizado_em = datetime.now(timezone.utc)
    db.flush()
    return usuario
