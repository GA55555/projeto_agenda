"""Orquestra o parser em subprocesso isolado, com ambiente minimo e timeout."""
import os
from pathlib import Path
import subprocess
import sys
import time
from contextlib import contextmanager

from app.core.config import settings
from app.modules.documentos.exceptions import SanitizacaoFalhou


@contextmanager
def _trava_global(caminho: Path):
    """Serializa sanitizadores entre os 2 workers para respeitar o teto de RAM."""
    caminho.parent.mkdir(parents=True, exist_ok=True)
    with caminho.open("a+b") as arquivo:
        if arquivo.tell() == 0:
            arquivo.write(b"0")
            arquivo.flush()
        limite = time.monotonic() + settings.documentos_sanitizacao_timeout_seconds
        while True:
            try:
                arquivo.seek(0)
                if os.name == "nt":
                    import msvcrt

                    msvcrt.locking(arquivo.fileno(), msvcrt.LK_NBLCK, 1)
                else:
                    import fcntl

                    fcntl.flock(arquivo.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
                break
            except OSError:
                if time.monotonic() >= limite:
                    raise SanitizacaoFalhou("Fila de sanitizacao excedeu o limite.") from None
                time.sleep(0.1)
        try:
            yield
        finally:
            arquivo.seek(0)
            if os.name == "nt":
                import msvcrt

                msvcrt.locking(arquivo.fileno(), msvcrt.LK_UNLCK, 1)
            else:
                import fcntl

                fcntl.flock(arquivo.fileno(), fcntl.LOCK_UN)


def sanitizar_arquivo(
    entrada: Path, saida: Path, formato: str, *, trava: Path | None = None
) -> None:
    worker = Path(__file__).with_name("sanitizer_worker.py")
    ambiente = {
        "PATH": os.environ.get("PATH", ""),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", "C.UTF-8"),
        # Necessario para localizar DLLs do Python em desenvolvimento no Windows.
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", ""),
    }
    try:
        with _trava_global(trava or entrada.parent / ".sanitizacao.lock"):
            resultado = subprocess.run(
                [sys.executable, "-I", str(worker), str(entrada), str(saida), formato],
                cwd=entrada.parent,
                env=ambiente,
                stdin=subprocess.DEVNULL,
                capture_output=True,
                text=True,
                timeout=settings.documentos_sanitizacao_timeout_seconds,
                check=False,
            )
    except subprocess.TimeoutExpired as exc:
        raise SanitizacaoFalhou("Sanitizacao excedeu o limite de tempo.") from exc
    if resultado.returncode != 0 or not saida.is_file():
        detalhe = (resultado.stderr or resultado.stdout).strip()[:300]
        raise SanitizacaoFalhou(
            "O arquivo nao pode ser reconstruido com seguranca."
            + (f" Detalhe tecnico: {detalhe}" if detalhe else "")
        )
