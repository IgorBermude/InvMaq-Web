from fastapi import FastAPI, Request, Form
from typing import Optional
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from core.db import init_db
from core.maquinas import listar_maquinas, adicionar_maquina, remover_maquina, atualizar_maquina
from core.historico_maquinas import listar_historico, adicionar_historico, remover_historico, atualizar_historico
from core.reports import gerar_pdf_maquinas, gerar_pdf_historico

app = FastAPI()
app.mount("/static", StaticFiles(directory="webapp/static"), name="static")
templates = Jinja2Templates(directory="webapp/templates")

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
):
    # linha will be computed automatically in adicionar_maquina
    adicionar_maquina(nome=nome, mac=mac, usuario=usuario, setor=setor, andar=andar, ip=ip, ponto=ponto, comentario=comentario)
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
    maquina = next((m for m in maquinas if m.id == id_), None)
    if maquina is None:
        return RedirectResponse("/", status_code=303)
    return templates.TemplateResponse("edit_maquina.html", {"request": request, "maquina": maquina})

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
                 comentario: Optional[str] = Form(None)):
    atualizar_maquina(id_, linha=linha, nome=nome, usuario=usuario, setor=setor, andar=andar, ip=ip, mac=mac, ponto=ponto, comentario=comentario)
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