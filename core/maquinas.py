from dataclasses import dataclass
from typing import List, Optional
from core.db import run_query

@dataclass
class Maquina:
    id: Optional[int]
    linha: Optional[int]
    nome: Optional[str]
    usuario: Optional[str]
    setor: Optional[str]
    andar: Optional[str]
    ip: Optional[str]
    mac: Optional[str]
    ponto: Optional[str]
    comentario: Optional[str]


def listar_maquinas() -> List[Maquina]:
    rows = run_query("SELECT * FROM maquinas ORDER BY linha", fetch=True)
    if not rows:
        return []
    # rows are RealDictCursor rows (dict-like) -> map to Maquina dataclass for attribute access
    return [Maquina(**r) for r in rows]


def adicionar_maquina(nome, mac, usuario, linha: Optional[int] = None, setor=None, andar=None, ip=None, ponto=None, comentario=None):
    # if linha not provided, compute next available linha as max(linha)+1
    if linha is None:
        next_row = run_query("SELECT COALESCE(MAX(linha), 0) + 1 AS next FROM maquinas", fetch=True)
        if next_row and isinstance(next_row, list):
            linha = next_row[0].get("next")
        else:
            linha = 1
    run_query(
        "INSERT INTO maquinas (linha, nome, usuario, setor, andar, ip, mac, ponto, comentario) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
        (linha, nome, usuario, setor, andar, ip, mac, ponto, comentario)
    )


def remover_maquina(id_):
    # Primeiro remova registros dependentes na tabela 'historico' para
    # evitar erro de restrição de integridade caso a FK não tenha
    # ON DELETE CASCADE (isso é seguro mesmo se a constraint já for cascade).
    run_query("DELETE FROM historico WHERE id_maquina = %s", (id_,))
    run_query("DELETE FROM maquinas WHERE id = %s", (id_,))


def atualizar_maquina(id_, nome, mac, usuario, linha, setor=None, andar=None, ip=None, ponto=None, comentario=None):
    run_query(
        """
        UPDATE maquinas
        SET linha = %s, nome = %s, usuario = %s, setor = %s, andar = %s, ip = %s, mac = %s, ponto = %s, comentario = %s
        WHERE id = %s
        """,
        (linha, nome, usuario, setor, andar, ip, mac, ponto, comentario, id_),
    )