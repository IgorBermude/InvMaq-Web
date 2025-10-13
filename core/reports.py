from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from core.db import run_query
from tempfile import NamedTemporaryFile

def gerar_pdf_maquinas():
    rows = run_query("SELECT linha, nome, usuario, setor, andar, ip, mac, ponto, comentario FROM maquinas ORDER BY linha", fetch=True)
    data = [["Linha", "Nome", "Usuário", "Setor", "Andar", "IP", "MAC", "Ponto", "Comentário"]] + [
        [r["linha"], r["nome"], r["usuario"], r["setor"], r["andar"], r["ip"], r["mac"], r["ponto"], r["comentario"]] for r in rows
    ]
    tmp = NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A4)
    style = getSampleStyleSheet()["Normal"]
    table = Table(data)
    doc.build([Paragraph("Relatório de Máquinas", style), table])
    return tmp.name

def gerar_pdf_historico():
    # join historico with maquinas to include machine name
    rows = run_query(
        "SELECT h.data, h.hora, m.nome AS maquina, h.tecnico, h.descricao "
        "FROM historico h LEFT JOIN maquinas m ON h.id_maquina = m.id "
        "ORDER BY h.data DESC, h.hora DESC",
        fetch=True,
    )
    data = [["Data", "Hora", "Máquina", "Técnico", "Descrição"]]
    for r in rows:
        # format date/time if they are date/time objects
        data.append([
            str(r.get("data", "")),
            str(r.get("hora", "")),
            r.get("maquina", ""),
            r.get("tecnico", ""),
            r.get("descricao", ""),
        ])

    tmp = NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=A4)
    style = getSampleStyleSheet()["Normal"]
    table = Table(data)
    doc.build([Paragraph("Relatório de Histórico", style), table])
    return tmp.name
