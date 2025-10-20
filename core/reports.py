from reportlab.lib.pagesizes import A4, landscape
from reportlab.platypus import SimpleDocTemplate, Table, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from core.db import run_query
from tempfile import NamedTemporaryFile
from reportlab.lib.units import mm
from reportlab.lib import colors


def _make_table(data, col_widths=None, title="Relatório"):
    tmp = NamedTemporaryFile(delete=False, suffix=".pdf")
    doc = SimpleDocTemplate(tmp.name, pagesize=landscape(A4),
                            leftMargin=15*mm, rightMargin=15*mm, topMargin=15*mm, bottomMargin=15*mm)
    
    available_width = doc.width

    if col_widths:
        total = sum(col_widths)
        if total > available_width:
            factor = available_width / total
            col_widths = [w * factor for w in col_widths]

    styles = getSampleStyleSheet()
    title_style = styles["Heading2"]
    body_style = ParagraphStyle(
        "body",
        parent=styles["BodyText"],
        fontSize=8,
        leading=8,
        spaceAfter=0,
    )

    table_data = []
    header = data[0]
    table_data.append([Paragraph(f"<b>{c}</b>", body_style) for c in header])
    for row in data[1: ]:
        table_data.append([Paragraph(str(cell) if cell is not None else "", body_style) for cell in row])

    table = Table(table_data, colWidths=col_widths, repeatRows=1)
    table_style = [
        ("GRID", (0,0), (-1,-1), 0.4, colors.grey),
        ("BACKGROUND", (0,0), (-1,0), colors.lightgrey),
        ("VALIGN", (0,0), (-1,-1), "TOP"),
        ("ALIGN", (0,0), (-1,0), "CENTER"),
        ("LEFTPADDING", (0,0), (-1,-1), 3),
        ("RIGHTPADDING", (0,0), (-1,-1), 3),
        ("TOPPADDING", (0,0), (-1,-1), 3),
        ("BOTTOMPADDING", (0,0), (-1,-1), 3),
    ]
    table.setStyle(table_style)

    elements = [Paragraph(title, title_style), Spacer(1, 6), table]
    doc.build(elements)
    return tmp.name

def gerar_pdf_maquinas():
    rows = run_query("SELECT linha, nome, usuario, setor, andar, ip, mac, ponto, comentario FROM maquinas ORDER BY linha", fetch=True)
    data = [["Linha", "Nome", "Usuário", "Setor", "Andar", "IP", "MAC", "Ponto", "Comentário"]] + [
        [r["linha"], r["nome"], r["usuario"], r["setor"], r["andar"], r["ip"], r["mac"], r["ponto"], r["comentario"]] for r in rows
    ]
    
    col_widths = [18*mm, 55*mm, 35*mm, 35*mm, 18*mm, 30*mm, 40*mm, 20*mm, 65*mm]
    return _make_table(data, col_widths=col_widths, title="Relatório de Máquinas")

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

    col_widths = [22*mm, 18*mm, 50*mm, 35*mm, 140*mm]
    return _make_table(data, col_widths=col_widths, title="Relatório de Histórico")

def gerar_pdf_componentes():
    rows = run_query(
        "SELECT c.nome, c.data_aquisicao, c.data_expiracao, c.observacao, m.nome AS maquina, m.ip "
        "FROM componentes c LEFT JOIN maquinas m ON c.id_maquina = m.id "
        "ORDER BY m.linha, m.nome, c.data_aquisicao",
        fetch=True,
    )
    data = [["Nome", "Data de Aquisição", "Data de Expiração", "Comentário", "Máquina", "IP"]] + [
        [r["nome"], r["data_aquisicao"], r["data_expiracao"], r["observacao"], r["maquina"], r["ip"]] for r in rows
    ]
    col_widths = [10*mm, 50*mm, 30*mm, 80*mm, 50*mm, 40*mm]
    return _make_table(data, col_widths=col_widths, title="Relatório de Componentes")

def gerar_pdf_relatorios():
    rows = run_query(
        "SELECT autor, data, hora, comentario FROM relatorios ORDER BY data DESC, hora DESC",
        fetch=True,
    )
    data = [["Autor", "Data", "Hora", "Comentário"]] + [
        [r["autor"], r["data"], r["hora"], r["comentario"]] for r in rows
    ]
    col_widths = [25*mm, 25*mm, 25*mm, 180*mm]
    return _make_table(data, col_widths=col_widths, title="Relatório de Registros")