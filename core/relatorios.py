from dataclasses import dataclass
from typing import List, Optional
from core.db import run_query

@dataclass
class Relatorio:
    id: Optional[int]
    data: Optional[str]  # YYYY-MM-DD
    hora: Optional[str]  # HH:MM:SS
    comentario: Optional[str]
    imagem: Optional[bytes]
    autor: Optional[str]

def listar_relatorios() -> List[Relatorio]:
    rows = run_query("SELECT * FROM relatorios ORDER BY data DESC, hora DESC", fetch=True)
    if not rows:
        return []
    return [Relatorio(**r) for r in rows]

def adicionar_relatorio(data, hora, comentario, imagem_bytes=None, autor=None):
    run_query(
        """
        INSERT INTO relatorios (data, hora, comentario, imagem, autor)
        VALUES (%s, %s, %s, %s, %s)
        """,
        (data, hora, comentario, imagem_bytes, autor)
    )

def remover_relatorio(id_):
    run_query("DELETE FROM relatorios WHERE id = %s", (id_,))

def atualizar_relatorio(id_, data, hora, comentario, imagem_bytes=None, autor=None):
    run_query(
        """
        UPDATE relatorios
        SET data = %s,
            hora = %s,
            comentario = %s,
            imagem = COALESCE(%s, imagem),  -- mantém a antiga se None
            autor = %s
        WHERE id = %s
        """,
        (data, hora, comentario, imagem_bytes, autor, id_)
    )
