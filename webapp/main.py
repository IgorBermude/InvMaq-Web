from fastapi import FastAPI, Request, Form
from typing import Optional
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.db import init_db
from core.maquinas import listar_maquinas, adicionar_maquina, remover_maquina, atualizar_maquina
from core.historico_maquinas import listar_historico, adicionar_historico, remover_historico, atualizar_historico
from core.reports import gerar_pdf_maquinas, gerar_pdf_historico

from core.componentes import (
    listar_componentes_por_maquina,
    adicionar_componente,
    atualizar_componente,
    remover_componente,
    get_componente,
)
import json
from markupsafe import Markup


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

# -------------------- MÁQUINAS --------------------
@app.get("/maquinas/add", response_class=HTMLResponse)
def add_maquina_page(request: Request):
    return templates.TemplateResponse("add_maquina.html", {"request": request})

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
    return templates.TemplateResponse("edit_maquina.html", {"request": request, "maquina": maquina_view})

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

    return templates.TemplateResponse("index.html", {"request": request, "maquinas": maquinas, "ordenar_por": ordenar_por, "direcao": direcao})

# -------------------- HISTÓRICO --------------------
@app.get("/historico", response_class=HTMLResponse)
def historico_page(request: Request, maquina: int | None = None):
    historico = listar_historico(maquina)
    maquinas = listar_maquinas()
    return templates.TemplateResponse("historico.html", {"request": request, "historico": historico, "maquinas": maquinas, "maquina_filter": maquina})

@app.post("/historico/add")
def add_historico(id_maquina: int = Form(...), data: str = Form(...), hora: str = Form(...),
                  tecnico: str = Form(...), descricao: str = Form(...)):
    adicionar_historico(id_maquina, data, hora, tecnico, descricao)
    return RedirectResponse("/historico", status_code=303)

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
    return templates.TemplateResponse("edit_historico_maquina.html", {"request": request, "historico": item})

@app.post("/historico/edit/{id_}")
def edit_historico(id_: int,
                   id_maquina: int = Form(...),
                   data: str = Form(...),
                   hora: str = Form(...),
                   tecnico: str = Form(...),
                   descricao: str = Form(...)):
    atualizar_historico(id_, data=data, hora=hora, tecnico=tecnico, descricao=descricao)
    return RedirectResponse(f"/historico?maquina={id_maquina}", status_code=303)

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

