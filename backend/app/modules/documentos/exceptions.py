class DocumentoInvalido(Exception):
    """Arquivo recusado antes de entrar no prontuario."""


class DocumentoMuitoGrande(DocumentoInvalido):
    pass


class CotaDocumentosExcedida(DocumentoInvalido):
    pass


class SanitizacaoFalhou(DocumentoInvalido):
    pass


class ArmazenamentoIndisponivel(Exception):
    pass
