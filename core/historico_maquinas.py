"""Operações de CRUD para o histórico de máquinas.

As funções usam a tabela 'historico' (id, id_maquina, data, hora, tecnico, descricao)
e retornam/recebem dados compatíveis com as rotas em webapp/main.py.
"""

from typing import Optional, List, Dict
from core.db import run_query


def listar_historico(maquina_id: Optional[int] = None) -> List[Dict]:
    """Retorna uma lista de registros do histórico. Se maquina_id for fornecido,
    filtra apenas os registros dessa máquina."""
    base_query = (
        "SELECT h.id, h.id_maquina, h.data, h.hora, h.tecnico, h.descricao, h.foto, m.nome AS maquina "
        "FROM historico h LEFT JOIN maquinas m ON m.id = h.id_maquina"
    )
    params = None
    if maquina_id is not None:
        base_query += " WHERE h.id_maquina = %s"
        params = (maquina_id,)

    base_query += " ORDER BY h.data DESC, h.hora DESC"
    return run_query(base_query, params, fetch=True)


def adicionar_historico(id_maquina: int, data: str, hora: str, tecnico: str, descricao: str, foto_bytes: bytes | None) -> None:
    """Insere um novo item no histórico."""
    run_query(
        "INSERT INTO historico (id_maquina, data, hora, tecnico, descricao, foto) VALUES (%s,%s,%s,%s,%s,%s)",
        (id_maquina, data, hora, tecnico, descricao, foto_bytes),
    )


def remover_historico(id_: int) -> None:
    """Remove um registro do histórico pelo id."""
    run_query("DELETE FROM historico WHERE id = %s", (id_,))


def atualizar_historico(id_: int, data=None, hora=None, tecnico=None, descricao=None, foto: bytes | None = None):
    sets, params = [], []
    if data is not None:
        sets.append("data=%s"); params.append(data)
    if hora is not None:
        sets.append("hora=%s"); params.append(hora)
    if tecnico is not None:
        sets.append("tecnico=%s"); params.append(tecnico)
    if descricao is not None:
        sets.append("descricao=%s"); params.append(descricao)
    if foto is not None:
        if isinstance(foto, memoryview):
            foto = bytes(foto)
        sets.append("foto=%s"); params.append(foto)
    if not sets:
        return
    params.append(id_)
    run_query(f"UPDATE historico SET {', '.join(sets)} WHERE id=%s", params)

def obter_foto_historico(id_: int) -> bytes | None:
    rows = run_query("SELECT foto FROM historico WHERE id=%s", (id_,), fetch=True)
    if not rows:
        return None
    raw = rows[0].get("foto")
    if raw is None:
        return None
    return bytes(raw)
