"""CLI administrativa de bootstrap e controle de acesso.

Uso (no servidor):
    docker compose exec backend python -m app.cli criar-tenant-usuario \\
        --nome "Dra. Fulana" --email fulana@clinica.pt --senha "SENHA" [--slug fulana]

Cria um tenant (psicologa) + o seu usuario de login. Roda com o role ADMIN
(agenda_admin) — provisionar tenants/usuarios e tarefa administrativa (§2.1.1);
o role de app so tem SELECT nessas tabelas.

Fase do roadmap: Fase 2
"""
import argparse
import re
import sys

from sqlalchemy import create_engine, text

from app.core.config import settings
from app.core.security import hash_password


def _slugify(valor: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", valor.lower()).strip("-")
    return slug[:80] or "tenant"


def criar_tenant_usuario(nome: str, email: str, senha: str, slug: str | None, papel: str) -> None:
    slug = slug or _slugify(email.split("@")[0])
    engine = create_engine(settings.admin_database_url)
    with engine.begin() as conn:
        tenant_id = conn.execute(
            text("INSERT INTO tenants (nome, slug) VALUES (:nome, :slug) RETURNING id"),
            {"nome": nome, "slug": slug},
        ).scalar_one()
        conn.execute(
            text(
                "INSERT INTO usuarios (tenant_id, email, senha_hash, nome, papel) "
                "VALUES (:tid, :email, :hash, :nome, :papel)"
            ),
            {
                "tid": tenant_id,
                "email": email,
                "hash": hash_password(senha),
                "nome": nome,
                "papel": papel,
            },
        )
    print(f"OK: tenant '{slug}' ({tenant_id}) e usuario '{email}' criados.")


def definir_usuario_ativo(email: str, *, ativo: bool) -> bool:
    """Suspende/reativa login pelo control-plane usando parâmetros, nunca SQL interpolado."""
    engine = create_engine(settings.admin_database_url)
    with engine.begin() as conn:
        usuario_id = conn.execute(
            text(
                "UPDATE usuarios SET ativo = :ativo, atualizado_em = now() "
                "WHERE lower(email) = lower(:email) RETURNING id"
            ),
            {"ativo": ativo, "email": email},
        ).scalar_one_or_none()
    if usuario_id is None:
        print("ERRO: usuario nao encontrado.", file=sys.stderr)
        return False
    estado = "reativado" if ativo else "suspenso"
    print(f"OK: usuario {estado} ({usuario_id}).")
    return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("criar-tenant-usuario", help="Cria tenant (psicologa) + login")
    p.add_argument("--nome", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--senha", required=True)
    p.add_argument("--slug", default=None)
    p.add_argument("--papel", default="psicologa")

    suspender = sub.add_parser("suspender-usuario", help="Suspende login e JWTs emitidos")
    suspender.add_argument("--email", required=True)

    reativar = sub.add_parser("reativar-usuario", help="Reativa login de usuario")
    reativar.add_argument("--email", required=True)

    args = parser.parse_args(argv)
    if args.cmd == "criar-tenant-usuario":
        criar_tenant_usuario(args.nome, args.email, args.senha, args.slug, args.papel)
    elif args.cmd == "suspender-usuario":
        if not definir_usuario_ativo(args.email, ativo=False):
            return 1
    elif args.cmd == "reativar-usuario":
        if not definir_usuario_ativo(args.email, ativo=True):
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
