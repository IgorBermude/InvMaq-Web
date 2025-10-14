from typing import Optional
from core.db import run_query

def listar_componentes(fetch: bool = True):
    return run_query("SELECT * FROM componentes ORDER BY id", fetch=fetch)

def listar_componentes_por_maquina(id_maquina: int, fetch: bool = True):
    return run_query("SELECT * FROM componentes WHERE id_maquina = %s ORDER BY nome", params=(id_maquina,), fetch=fetch)

def get_componente(id_: int):
    rows = run_query("SELECT * FROM componentes WHERE id = %s", params=(id_,), fetch=True)
    return rows[0] if rows else None

def adicionar_componente(id_maquina: int, nome: str, data_aquisicao: Optional[str]=None, data_expiracao: Optional[str]=None, observacao: Optional[str]=None):
    run_query(
        "INSERT INTO componentes (id_maquina, nome, data_aquisicao, data_expiracao, observacao) VALUES (%s, %s, %s, %s, %s)",
        params=(id_maquina, nome, data_aquisicao, data_expiracao, observacao)
    )

def atualizar_componente(id_: int, nome: str, data_aquisicao: Optional[str]=None, data_expiracao: Optional[str]=None, observacao: Optional[str]=None):
    run_query(
        """
        UPDATE componentes
        SET nome = %s, data_aquisicao = %s, data_expiracao = %s, observacao = %s
        WHERE id = %s
        """,
        params=(nome, data_aquisicao, data_expiracao, observacao, id_)
    )

def remover_componente(id_: int):
    run_query("DELETE FROM componentes WHERE id = %s", params=(id_,))