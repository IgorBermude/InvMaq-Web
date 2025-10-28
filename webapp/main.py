from fastapi import FastAPI, Request, Form, File, UploadFile
from typing import Optional
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException
from fastapi.responses import Response

from core.db import init_db, run_query
from core.maquinas import listar_maquinas, adicionar_maquina, remover_maquina, atualizar_maquina
from core.historico_maquinas import listar_historico, adicionar_historico, obter_foto_historico, remover_historico, atualizar_historico
from core.relatorios import adicionar_relatorio, atualizar_relatorio, remover_relatorio, listar_relatorios
from core.reports import gerar_pdf_maquinas, gerar_pdf_historico, gerar_pdf_componentes, gerar_pdf_relatorios

from core.componentes import (
    listar_componentes_por_maquina,
    adicionar_componente,
    atualizar_componente,
    remover_componente,
    get_componente,
    listar_componentes_expirando,
)
import json
from markupsafe import Markup
from flask import request, render_template
from core.db import run_query


app = FastAPI()
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
templates = Jinja2Templates(directory="webapp/templates")
# Adiciona filtro 'tojson' ao ambiente Jinja, pois FastAPI/Starlette não o fornece por padrão
def _tojson_filter(value):
    def _default(o):
        # Converte tipos não serializáveis (date, datetime, Decimal, etc.) para string
        try:
            return o.isoformat()
        except Exception:
            return str(o)
    try:
        return Markup(json.dumps(value, ensure_ascii=False, default=_default))
    except Exception:
        return "[]"
templates.env.filters["tojson"] = _tojson_filter

@app.on_event("startup")
def startup():
    init_db()


def _get_alertas_componentes():
    """Busca componentes que expiram em até 10 dias para exibir alertas no topo das páginas."""
    try:
        return listar_componentes_expirando(10)
    except Exception:
        return []

# -------------------- MÁQUINAS --------------------
@app.get("/maquinas/add", response_class=HTMLResponse)
def add_maquina_page(request: Request):
    return templates.TemplateResponse("add/add_maquina.html", {"request": request})

@app.post("/maquinas/add")
def add_maquina(
    nome: str = Form(...),
    usuario: str = Form(...),
    setor: str = Form(None),
    andar: str = Form(None),
    ip: str = Form(None),
    mac: str = Form(...),
    ponto: str = Form(None),
    comentario: Optional[str] = Form(None),
    componentes: str = Form("[]"),
):
    # cria a máquina
    created = adicionar_maquina(nome=nome, mac=mac, usuario=usuario, setor=setor, andar=andar, ip=ip, ponto=ponto, comentario=comentario)

    # tenta obter o id da máquina criada
    new_id = None
    if created is not None:
        new_id = getattr(created, "id", None)
        if new_id is None:
            try:
                new_id = created.get("id")
            except Exception:
                pass
    if new_id is None:
        # fallback: localizar pela MAC (assumindo única)
        try:
            maquinas = listar_maquinas()
            found = next((m for m in maquinas if (getattr(m, "mac", None) or (m.get("mac") if hasattr(m, "get") else None)) == mac), None)
            if found:
                new_id = getattr(found, "id", None)
                if new_id is None:
                    try:
                        new_id = found["id"]
                    except Exception:
                        new_id = None
        except Exception:
            new_id = None

    # persiste componentes filhos (se houver id)
    try:
        comps = json.loads(componentes or "[]")
    except Exception:
        comps = []
    if new_id:
        for c in comps or []:
            nome_c = (c.get("nome") if isinstance(c, dict) else getattr(c, "nome", None)) or ""
            if not nome_c.strip():
                continue
            adicionar_componente(
                new_id,
                nome_c.strip(),
                (c.get("data_aquisicao") if isinstance(c, dict) else getattr(c, "data_aquisicao", None)) or None,
                (c.get("data_expiracao") if isinstance(c, dict) else getattr(c, "data_expiracao", None)) or None,
                (c.get("observacao") if isinstance(c, dict) else getattr(c, "observacao", None)) or None,
            )

    return RedirectResponse("/", status_code=303)


@app.get("/maquinas/delete/{id_}")
def delete_maquina(id_: int):
    remover_maquina(id_)
    return RedirectResponse("/", status_code=303)

@app.get("/report/maquinas")
def report_maquinas():
    pdf_path = gerar_pdf_maquinas()
    return FileResponse(pdf_path, filename="maquinas.pdf")

@app.get("/maquinas/edit/{id_}", response_class=HTMLResponse)
def edit_maquina_page(request: Request, id_: int):
    maquinas = listar_maquinas()
    maquina = next((m for m in maquinas if getattr(m, "id", None) == id_ or (hasattr(m, "get") and m.get("id") == id_)), None)
    if maquina is None:
        return RedirectResponse("/", status_code=303)

    # carrega componentes e injeta no objeto/dict para o template usar maquina.componentes
    comps = listar_componentes_por_maquina(id_)
    def g(key, default=None):
        v = getattr(maquina, key, None)
        if v is None:
            try:
                v = maquina[key]
            except Exception:
                v = default
        return v
    maquina_view = {
        "id": g("id"),
        "linha": g("linha"),
        "nome": g("nome"),
        "usuario": g("usuario"),
        "setor": g("setor"),
        "andar": g("andar"),
        "ip": g("ip"),
        "mac": g("mac"),
        "ponto": g("ponto"),
        "comentario": g("comentario"),
        "componentes": comps or [],
    }
    return templates.TemplateResponse("edit/edit_maquina.html", {"request": request, "maquina": maquina_view})

@app.post("/maquinas/edit/{id_}")
def edit_maquina(id_: int,
                 linha: int = Form(...),
                 nome: str = Form(...),
                 usuario: str = Form(...),
                 setor: str = Form(...),
                 andar: str = Form(...),
                 ip: str = Form(...),
                 mac: str = Form(...),
                 ponto: str = Form(...),
                 comentario: Optional[str] = Form(None),
                 componentes: str = Form("[]")):
    # atualiza os dados da máquina
    atualizar_maquina(id_, linha=linha, nome=nome, usuario=usuario, setor=setor, andar=andar, ip=ip, mac=mac, ponto=ponto, comentario=comentario)

    # substitui os componentes: remove os atuais e insere os enviados
    try:
        comps_new = json.loads(componentes or "[]")
    except Exception:
        comps_new = []

    try:
        comps_old = listar_componentes_por_maquina(id_) or []
        for c in comps_old:
            cid = getattr(c, "id", None)
            if cid is None:
                try:
                    cid = c["id"]
                except Exception:
                    cid = None
            if cid is not None:
                remover_componente(cid)
        for c in comps_new or []:
            nome_c = (c.get("nome") if isinstance(c, dict) else getattr(c, "nome", None)) or ""
            if not nome_c.strip():
                continue
            adicionar_componente(
                id_,
                nome_c.strip(),
                (c.get("data_aquisicao") if isinstance(c, dict) else getattr(c, "data_aquisicao", None)) or None,
                (c.get("data_expiracao") if isinstance(c, dict) else getattr(c, "data_expiracao", None)) or None,
                (c.get("observacao") if isinstance(c, dict) else getattr(c, "observacao", None)) or None,
            )
    except Exception:
        pass

    return RedirectResponse("/", status_code=303)

@app.get("/", response_class=HTMLResponse)
def index(request: Request, ordenar_por: str | None = None, direcao: str | None = None):
    maquinas = listar_maquinas()

    if(ordenar_por):
        try:
            def _sort_key(m):
                # tenta atributo; se não existir aceita indexação por chave (caso sejam dicts)
                v = getattr(m, ordenar_por, None)
                if v is None:
                    try:
                        v = m.get(ordenar_por)
                    except Exception:
                        v = ""
                # números ordenam naturalmente; strings em lower
                if isinstance(v, (int, float)):
                    return v
                return str(v or "").lower()
            reverse = (direcao == "desc")
            maquinas = sorted(maquinas, key=_sort_key, reverse=reverse)
        except Exception:
            pass

    return templates.TemplateResponse("index.html", {"request": request, "maquinas": maquinas, "ordenar_por": ordenar_por, "direcao": direcao, "alertas_componentes": _get_alertas_componentes()})

@app.get("/")
def index():
    ordenar_por = request.args.get("ordenar_por", "linha")
    direcao = request.args.get("direcao", "asc")
    q = request.args.get("q", "").strip()

    allowed = {"linha","nome","usuario","setor","andar","ip","mac","ponto","comentario"}
    if ordenar_por not in allowed:
        ordenar_por = "linha"
    if direcao not in {"asc","desc"}:
        direcao = "asc"

    sql = """
      SELECT id, linha, nome, usuario, setor, andar, ip, mac, ponto, comentario
      FROM maquinas
    """
    params = []
    if q:
        like = f"%{q}%"
        sql += """ 
          WHERE (nome LIKE ? OR usuario LIKE ? OR setor LIKE ?
                 OR ip LIKE ? OR mac LIKE ? OR ponto LIKE ? OR comentario LIKE ?)
          COLLATE NOCASE
        """
        params = [like]*7

    sql += f" ORDER BY {ordenar_por} {direcao}"
    maquinas = run_query(sql, params, fetch=True)
    return render_template("index.html", maquinas=maquinas, ordenar_por=ordenar_por, direcao=direcao, q=q, alertas_componentes=listar_componentes_expirando(10))


# -------------------- HISTÓRICO --------------------
@app.get("/historico", response_class=HTMLResponse)
def historico_page(request: Request, maquina: int | None = None):
    historico = listar_historico(maquina)
    maquinas = listar_maquinas()
    return templates.TemplateResponse("historico.html", {"request": request, "historico": historico, "maquinas": maquinas, "maquina_filter": maquina})

@app.post("/historico/add")
async def add_historico(
    id_maquina: int = Form(...),
    data: str = Form(...),
    hora: str = Form(...),
    tecnico: str = Form(...),
    descricao: str = Form(...),
    arquivo: UploadFile | None = File(None),
):
    foto_bytes = None
    if arquivo and arquivo.filename:
        foto_bytes = await arquivo.read()
    adicionar_historico(id_maquina, data, hora, tecnico, descricao, foto_bytes)
    return RedirectResponse(f"/historico?maquina={id_maquina}", status_code=303)

@app.get("/historico/delete/{id_}")
def delete_historico(id_: int):
    remover_historico(id_)
    return RedirectResponse("/historico", status_code=303)

@app.get("/report/historico")
def report_historico():
    pdf_path = gerar_pdf_historico()
    return FileResponse(pdf_path, filename="historico.pdf")

@app.get("/historico/edit/{id_}", response_class=HTMLResponse)
def edit_historico_page(request: Request, id_: int):
    historico = listar_historico()
    # RealDictRow é um mapeamento (dict-like). Use acesso por chave para evitar AttributeError.
    item = next((h for h in historico if str(h['id']) == str(id_)), None)
    if item is None:
        return RedirectResponse("/", status_code=303)
    # usar o template existente e passar a variável esperada pelo template
    return templates.TemplateResponse("edit/edit_historico_maquina.html", {"request": request, "historico": item})

@app.post("/historico/edit/{id_}")
async def edit_historico(id_: int,
                   id_maquina: int = Form(...),
                   data: str = Form(...),
                   hora: str = Form(...),
                   tecnico: str = Form(...),
                   descricao: str = Form(...),
                   arquivo: UploadFile | None = File(None)):
    foto_bytes = None
    if arquivo and arquivo.filename:
        foto_bytes = await arquivo.read()
    atualizar_historico(id_, data=data, hora=hora, tecnico=tecnico, descricao=descricao, foto=foto_bytes)
    return RedirectResponse(f"/historico?maquina={id_maquina}", status_code=303)

def _detect_media_type(data: bytes) -> str:
    if data.startswith(b"%PDF"):
        return "application/pdf"
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if data.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if data.startswith(b"GIF87a") or data.startswith(b"GIF89a"):
        return "image/gif"
    if data.startswith(b"RIFF") and data[8:12] == b"WEBP":
        return "image/webp"
    if data.startswith(b"BM"):
        return "image/bmp"
    return "application/octet-stream"

@app.get("/historico/foto/{historico_id}")
def historico_file(historico_id: int):
    foto_bytes = obter_foto_historico(historico_id)
    if foto_bytes is None:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    # Detecta tipo
    foto_bytes = bytes(foto_bytes)  # garante bytes (pode ser memoryview)
    media_type = _detect_media_type(foto_bytes)

    return Response(foto_bytes, media_type=media_type)

# -------------------- COMPONENTES --------------------
@app.get("/componentes/maquina/{id_}", response_class=HTMLResponse)
def componentes_maquina_page(request: Request, id_: int):
    componentes = listar_componentes_por_maquina(id_)
    maquinas = listar_maquinas()
    return templates.TemplateResponse("componentes_maquina.html", {"request": request, "componentes": componentes, "maquina_id": id_, "maquinas": maquinas})

@app.post("/componentes/add")
def componentes_add(id_maquina: int = Form(...), nome: str = Form(...), data_aquisicao: Optional[str] = Form(None), data_expiracao: Optional[str] = Form(None), observacao: Optional[str] = Form(None)):
    adicionar_componente(id_maquina, nome, data_aquisicao, data_expiracao, observacao)
    return RedirectResponse(f"/componentes/maquina/{id_maquina}", status_code=303)

@app.get("/componentes/edit/{id_}")
def componentes_edit(id_: int, id_maquina: int = Form(...), nome: str = Form(...), data_aquisicao: Optional[str] = Form(None), data_expiracao: Optional[str] = Form(None), observacao: Optional[str] = Form(None)):
    atualizar_componente(id_, nome, data_aquisicao, data_expiracao, observacao)
    return RedirectResponse(f"/componentes/maquina/{id_maquina}", status_code=303)

@app.get("/componentes/delete/{id_}/{id_maquina}")
def componentes_delete(id_: int, id_maquina: int):
    remover_componente(id_)
    return RedirectResponse(f"/componentes/maquina/{id_maquina}", status_code=303)

@app.get("/report/componentes")
def report_componentes():
    pdf_path = gerar_pdf_componentes()
    return FileResponse(pdf_path, filename="componentes.pdf")

# -------------------- RELATORIOS --------------------
@app.get("/relatorios/add", response_class=HTMLResponse)
def add_relatorio_page(request: Request):
    return templates.TemplateResponse("add/add_relatorio.html", {"request": request})

def _none_if_blank(s: Optional[str]) -> Optional[str]:
    return s.strip() if isinstance(s, str) and s.strip() != "" else None

@app.post("/relatorios/add")
async def add_relatorio(
    autor: Optional[str] = Form(None),
    data: Optional[str] = Form(None),
    hora: Optional[str] = Form(None),
    comentario: Optional[str] = Form(None),
    imagem: UploadFile | None = File(None),
):
    imagem_bytes = await imagem.read() if (imagem and imagem.filename) else None

    data = _none_if_blank(data)
    hora = _none_if_blank(hora)
    if hora and len(hora) == 5:
        hora = f"{hora}:00"
    autor = _none_if_blank(autor)
    comentario = _none_if_blank(comentario)

    adicionar_relatorio(data, hora, comentario, imagem_bytes, autor)
    return RedirectResponse("/relatorios", status_code=303)

@app.get("/relatorios/delete/{id_}")
def delete_relatorio(id_: int):
    remover_relatorio(id_)
    return RedirectResponse("/relatorios", status_code=303)

@app.get("/report/relatorios")
def report_relatorios():
    pdf_path = gerar_pdf_relatorios()
    return FileResponse(pdf_path, filename="relatorios.pdf")

# Lista de relatórios com ordenação (usa os links do template)
@app.get("/relatorios", response_class=HTMLResponse)
def relatorios(request: Request, ordenar_por: str | None = None, direcao: str | None = None):
    items = listar_relatorios()
    if ordenar_por:
        try:
            def _key(r):
                v = getattr(r, ordenar_por, None)
                return (v if isinstance(v, (int, float)) else str(v or "").lower())
            items = sorted(items, key=_key, reverse=(direcao == "desc"))
        except Exception:
            pass
    return templates.TemplateResponse(
        "relatorios.html",
        {"request": request, "relatorios": items, "ordenar_por": ordenar_por, "direcao": direcao, "alertas_componentes": _get_alertas_componentes()},
    )

@app.get("/relatorios/edit/{id_}", response_class=HTMLResponse)
def edit_relatorio_page(request: Request, id_: int):
    items = listar_relatorios()
    item = next((r for r in items if getattr(r, "id", None) == id_), None)
    if item is None:
        return RedirectResponse("/relatorios", status_code=303)
    # URL do arquivo atual (se existir blob)
    has_blob = getattr(item, "imagem", None)
    imagem_url = request.url_for("relatorio_arquivo", id_=id_) if has_blob else None
    return templates.TemplateResponse("edit/edit_relatorio.html", {"request": request, "relatorio": item, "imagem_url": imagem_url})

@app.post("/relatorios/edit/{id_}")
async def edit_relatorio(id_: int,
                    autor: Optional[str] = Form(None),
                    data: Optional[str] = Form(None),
                    hora: Optional[str] = Form(None),
                    comentario: Optional[str] = Form(None),
                    imagem: UploadFile | None = File(None)):
    imagem_bytes = await imagem.read() if (imagem and imagem.filename) else None

    data = _none_if_blank(data)
    hora = _none_if_blank(hora)
    if hora and len(hora) == 5:
        hora = f"{hora}:00"
    autor = _none_if_blank(autor)
    comentario = _none_if_blank(comentario)
    
    atualizar_relatorio(
    id_,
    data=data,
    hora=hora,
    comentario=comentario,
    imagem_bytes=imagem_bytes,
    autor=autor,
    )
    return RedirectResponse("/relatorios", status_code=303)

# Arquivo atual do relatório (serve o blob armazenado)
@app.get("/relatorios/arquivo/{id_}")
def relatorio_arquivo(id_: int):
    rows = run_query("SELECT imagem FROM relatorios WHERE id = %s", (id_,), fetch=True)
    if not rows:
        raise HTTPException(status_code=404, detail="Relatório não encontrado")
    try:
        blob = rows[0]["imagem"]
    except Exception:
        try:
            blob = getattr(rows[0], "imagem", None)
        except Exception:
            blob = None
    if not blob:
        raise HTTPException(status_code=404, detail="Arquivo não encontrado")

    data = bytes(blob) if not isinstance(blob, (bytes, bytearray)) else blob
    media_type = _detect_media_type(data)
    return Response(data, media_type=media_type, headers={"Content-Disposition": f"inline; filename=relatorio_{id_}"})