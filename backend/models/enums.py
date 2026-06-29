from enum import Enum


class MetalType(str, Enum):
    OURO_18K = "ouro_18k"
    OURO_24K = "ouro_24k"
    PRATA_925 = "prata_925"
    PLATINA = "platina"
    RODIO = "rodio"
    PALADIO = "paladio"
    OUTRO = "outro"


class GemType(str, Enum):
    DIAMANTE = "diamante"
    ESMERALDA = "esmeralda"
    SAFIRA = "safira"
    RUBI = "rubi"
    AMETISTA = "ametista"
    TOPAZIO = "topazio"
    AGUA_MARINHA = "agua_marinha"
    TURMALINA = "turmalina"
    CITRINO = "citrino"
    OPALA = "opala"
    PEROLA = "perola"
    OUTRO = "outro"


class JewelStatus(str, Enum):
    CADASTRADA = "cadastrada"
    EM_PRODUCAO = "em_producao"
    DISPONIVEL = "disponivel"
    VENDIDA = "vendida"
    BAIXADA = "baixada"
