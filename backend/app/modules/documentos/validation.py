"""Validacao barata antes do parser isolado tocar no arquivo nao confiavel."""
from pathlib import Path, PurePath
import re
import unicodedata

from app.modules.documentos.exceptions import DocumentoInvalido

TIPOS_ACEITOS = {
    "pdf": (".pdf", "application/pdf"),
    "docx": (".docx", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"),
    "jpeg": (".jpg", "image/jpeg"),
    "png": (".png", "image/png"),
}
EXTENSOES_JPEG = {".jpg", ".jpeg"}


def normalizar_nome_original(nome: str | None) -> str:
    """Mantem um nome apresentavel sem caminho, controles ou ambiguidades."""
    bruto = PurePath((nome or "").replace("\\", "/")).name
    bruto = unicodedata.normalize("NFC", bruto)
    # Cc/Cf inclui controles ASCII e marcadores bidi invisiveis (ex.: U+202E),
    # que poderiam fazer `malware.exe.pdf` parecer outro nome no download.
    limpo = "".join(ch for ch in bruto if unicodedata.category(ch) not in {"Cc", "Cf"})
    limpo = limpo.strip().strip(".")
    limpo = re.sub(r"\s+", " ", limpo)
    if not limpo or len(limpo) > 255:
        raise DocumentoInvalido("Nome de arquivo ausente ou maior que 255 caracteres.")
    return limpo


def detectar_formato(caminho: Path) -> str:
    with caminho.open("rb") as arquivo:
        inicio = arquivo.read(1024)
    if inicio.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if inicio.startswith(b"\xff\xd8\xff"):
        return "jpeg"
    if b"%PDF-" in inicio[:256] and not inicio[: inicio.index(b"%PDF-")].strip():
        return "pdf"
    if inicio.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        # Nao abrir ZIP no processo principal: uma central directory com centenas
        # de milhares de entradas consumiria RAM antes do worker limitado.
        return "docx"
    raise DocumentoInvalido("O conteudo real nao e PDF, DOCX, JPEG ou PNG.")


def validar_extensao(nome: str, formato: str) -> None:
    extensao = Path(nome).suffix.lower()
    esperadas = EXTENSOES_JPEG if formato == "jpeg" else {TIPOS_ACEITOS[formato][0]}
    if extensao not in esperadas:
        raise DocumentoInvalido(
            f"A extensao {extensao or '(ausente)'} nao corresponde ao conteudo {formato.upper()}."
        )


def extensao_canonica(formato: str) -> str:
    return TIPOS_ACEITOS[formato][0]


def mime_canonico(formato: str) -> str:
    return TIPOS_ACEITOS[formato][1]
