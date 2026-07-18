"""CLI administrativa (bootstrap).

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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="app.cli")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("criar-tenant-usuario", help="Cria tenant (psicologa) + login")
    p.add_argument("--nome", required=True)
    p.add_argument("--email", required=True)
    p.add_argument("--senha", required=True)
    p.add_argument("--slug", default=None)
    p.add_argument("--papel", default="psicologa")

    args = parser.parse_args(argv)
    if args.cmd == "criar-tenant-usuario":
        criar_tenant_usuario(args.nome, args.email, args.senha, args.slug, args.papel)
    return 0


if __name__ == "__main__":
    sys.exit(main())
