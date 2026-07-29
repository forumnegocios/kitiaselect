#!/usr/bin/env python3
"""
Kit Select IA - Dashboard Server
Forum Negocios Select

Servidor local Flask que expoe os dados gravados pelo Claude
para o dashboard.html via API REST simples.
Porta padrao: 5680
"""

import json
import os
import sys
import io
import webbrowser
import threading
import time
from pathlib import Path
from datetime import datetime, timedelta, date

# ---------------------------------------------------------------------------
# Verificar dependencias antes de importar Flask
# ---------------------------------------------------------------------------
try:
    from flask import Flask, jsonify, request, send_from_directory, abort, Response
    from flask_cors import CORS
except ImportError:
    print("\n" + "="*60)
    print("  ATENCAO: dependencias nao instaladas.")
    print("  Execute o seguinte comando e tente novamente:\n")
    print("  pip install flask flask-cors")
    print("="*60 + "\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuracao
# ---------------------------------------------------------------------------
BASE_DIR    = Path(__file__).parent.resolve()
DADOS_DIR   = BASE_DIR / "dados"
OUTPUT_DIR  = DADOS_DIR / "outputs"
IMG_DIR     = BASE_DIR / "img"
PERFIL_FILE = DADOS_DIR / "perfil-do-negocio.json"
AGENDA_FILE = DADOS_DIR / "agenda.json"
PORT = 5680

DADOS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(BASE_DIR))
CORS(app)

# ---------------------------------------------------------------------------
# Metadados das ferramentas (categoria + minutos economizados por entregavel)
# ---------------------------------------------------------------------------
TOOLS = {
    "configurar-negocio":  {"label": "Configurar negocio",   "cat": "base",     "min": 15},
    "mes-de-conteudo":     {"label": "Mes de conteudo",      "cat": "conteudo", "min": 120},
    "legenda-no-tom":      {"label": "Legenda no meu tom",   "cat": "conteudo", "min": 20},
    "roteiro-de-reels":    {"label": "Roteiro de Reels",     "cat": "conteudo", "min": 30},
    "descricao-de-design": {"label": "Descricao de design",  "cat": "conteudo", "min": 25},
    "criar-anuncio":       {"label": "Criar anuncio",        "cat": "vender",   "min": 40},
    "proposta-comercial":  {"label": "Proposta comercial",   "cat": "vender",   "min": 90},
    "respostas-cliente":   {"label": "Respostas de cliente", "cat": "atender",  "min": 30},
    "pesquisa-de-mercado": {"label": "Pesquisa de mercado",  "cat": "mercado",  "min": 120},
    "resumir-documento":   {"label": "Resumir documento",    "cat": "docs",     "min": 30},
}
# Ferramentas que contam para o painel de progresso (exclui a de configuracao)
TOOLS_PROGRESSO = [t for t in TOOLS if t != "configurar-negocio"]

# ---------------------------------------------------------------------------
# Utilitarios
# ---------------------------------------------------------------------------
def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

def _parse_dt(s):
    if not s:
        return None
    s = str(s).strip().replace("Z", "")
    for fmt in ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%dT%H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(s[:len(datetime.now().strftime(fmt))] if False else s, fmt)
        except Exception:
            continue
    try:
        return datetime.fromisoformat(s)
    except Exception:
        return None

def _all_outputs():
    items = []
    for f in OUTPUT_DIR.glob("*.json"):
        o = load_json(f)
        if o and o.get("id"):
            items.append(o)
    return items

# ---------------------------------------------------------------------------
# Rotas - Dashboard HTML
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "dashboard.html")

@app.route("/img/<path:filename>")
def imagens(filename):
    """Serve as fotos das ferramentas usadas nos cards do dashboard."""
    return send_from_directory(str(IMG_DIR), filename)

# ---------------------------------------------------------------------------
# Rotas - Perfil do negocio
# ---------------------------------------------------------------------------
@app.route("/api/perfil", methods=["GET"])
def get_perfil():
    return jsonify(load_json(PERFIL_FILE, {}))

@app.route("/api/perfil", methods=["POST"])
def save_perfil():
    data = request.get_json(force=True)
    data["atualizado_em"] = datetime.now().isoformat()
    save_json(PERFIL_FILE, data)
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# Rotas - Outputs
# ---------------------------------------------------------------------------
@app.route("/api/outputs", methods=["GET"])
def list_outputs():
    ferramenta = request.args.get("ferramenta")
    busca      = (request.args.get("busca") or "").lower()

    items = []
    for f in sorted(OUTPUT_DIR.glob("*.json"), reverse=True):
        try:
            o = load_json(f)
            if not o:
                continue
            if ferramenta and o.get("ferramenta") != ferramenta:
                continue
            if busca and busca not in (o.get("titulo") or "").lower():
                continue
            items.append({
                "id":         o.get("id"),
                "ferramenta": o.get("ferramenta"),
                "titulo":     o.get("titulo"),
                "data":       o.get("data"),
            })
        except Exception:
            continue

    return jsonify(items)

@app.route("/api/outputs/<output_id>", methods=["GET"])
def get_output(output_id):
    path = OUTPUT_DIR / f"{output_id}.json"
    if not path.exists():
        abort(404)
    return jsonify(load_json(path))

@app.route("/api/outputs", methods=["POST"])
def save_output():
    """
    Recebe o output gerado pelo Claude e grava em arquivo.
    Chamado pelas skills do kit automaticamente ao final de cada geracao.
    """
    data = request.get_json(force=True)
    if not data.get("id"):
        abort(400)
    path = OUTPUT_DIR / f"{data['id']}.json"
    save_json(path, data)
    return jsonify({"ok": True, "id": data["id"]})

@app.route("/api/outputs/<output_id>", methods=["DELETE"])
def delete_output(output_id):
    path = OUTPUT_DIR / f"{output_id}.json"
    try:
        if path.exists():
            path.unlink()
    except OSError:
        pass
    # remove agendamentos ligados a este output
    agenda = load_json(AGENDA_FILE, [])
    if isinstance(agenda, list):
        novo = [a for a in agenda if a.get("output_id") != output_id]
        if len(novo) != len(agenda):
            save_json(AGENDA_FILE, novo)
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# Rotas - Agenda (calendario de conteudo)
# ---------------------------------------------------------------------------
@app.route("/api/agenda", methods=["GET"])
def list_agenda():
    agenda = load_json(AGENDA_FILE, [])
    if not isinstance(agenda, list):
        agenda = []
    return jsonify(agenda)

@app.route("/api/agenda", methods=["POST"])
def add_agenda():
    data = request.get_json(force=True)
    output_id = data.get("output_id")
    if not output_id:
        abort(400)
    agenda = load_json(AGENDA_FILE, [])
    if not isinstance(agenda, list):
        agenda = []
    # descobre a ferramenta a partir do output salvo
    ferramenta = data.get("ferramenta")
    if not ferramenta:
        o = load_json(OUTPUT_DIR / f"{output_id}.json", {})
        ferramenta = o.get("ferramenta", "")
    # 1 agendamento por output: substitui se ja existir
    agenda = [a for a in agenda if a.get("output_id") != output_id]
    item = {
        "id":         f"ag-{datetime.now().strftime('%Y%m%d%H%M%S%f')}",
        "output_id":  output_id,
        "data":       data.get("data"),
        "titulo":     data.get("titulo", ""),
        "ferramenta": ferramenta,
    }
    agenda.append(item)
    save_json(AGENDA_FILE, agenda)
    return jsonify({"ok": True, "id": item["id"]})

@app.route("/api/agenda/<agenda_id>", methods=["DELETE"])
def delete_agenda(agenda_id):
    agenda = load_json(AGENDA_FILE, [])
    if isinstance(agenda, list):
        agenda = [a for a in agenda if a.get("id") != agenda_id]
        save_json(AGENDA_FILE, agenda)
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# Rota - Uso / progresso (analytics calculado a partir dos outputs)
# ---------------------------------------------------------------------------
@app.route("/api/uso")
def uso():
    outs = _all_outputs()
    perfil = load_json(PERFIL_FILE, {})

    # pares (ferramenta, datetime) validos
    regs = []
    for o in outs:
        dt = _parse_dt(o.get("data"))
        if dt is None:
            dt = datetime.now()
        regs.append((o.get("ferramenta") or "", dt))

    total = len(regs)
    datas = sorted([dt for _, dt in regs])
    primeiro = datas[0].isoformat() if datas else None
    ultimo   = datas[-1].isoformat() if datas else None

    # por ferramenta
    cont_ferr = {}
    for ferr, _ in regs:
        cont_ferr[ferr] = cont_ferr.get(ferr, 0) + 1

    ferramentas_usadas = len([t for t in TOOLS_PROGRESSO if cont_ferr.get(t, 0) > 0])
    ferramentas_total  = len(TOOLS_PROGRESSO)

    horas = sum(cont_ferr.get(t, 0) * TOOLS.get(t, {}).get("min", 30) for t in cont_ferr) / 60.0

    # dias / semanas ativas
    dias_set = set(dt.date() for _, dt in regs)
    dias_ativos = len(dias_set)
    semanas_set = set((dt.isocalendar()[0], dt.isocalendar()[1]) for _, dt in regs)
    semanas_ativas = len(semanas_set)

    # semanas seguidas ativo (a partir da semana atual, para tras)
    hoje = datetime.now()
    semanas_seguidas = 0
    cursor = hoje
    while True:
        key = (cursor.isocalendar()[0], cursor.isocalendar()[1])
        if key in semanas_set:
            semanas_seguidas += 1
            cursor = cursor - timedelta(weeks=1)
        else:
            break

    n_semanas_span = max(1, semanas_ativas)
    media_semanal = round(total / n_semanas_span, 1) if total else 0

    # serie das ultimas 8 semanas (segunda-feira como inicio)
    serie = []
    start_this_week = (hoje - timedelta(days=hoje.weekday())).date()
    for i in range(7, -1, -1):
        wk_start = start_this_week - timedelta(weeks=i)
        wk_end = wk_start + timedelta(days=7)
        tot = sum(1 for _, dt in regs if wk_start <= dt.date() < wk_end)
        serie.append({
            "label": f"{wk_start.day:02d}/{wk_start.month:02d}",
            "total": tot,
            "atual": i == 0,
        })

    # por categoria
    cont_cat = {}
    for ferr, _ in regs:
        cat = TOOLS.get(ferr, {}).get("cat", "outros")
        cont_cat[cat] = cont_cat.get(cat, 0) + 1
    por_categoria = sorted(
        [{"cat": c, "total": n} for c, n in cont_cat.items()],
        key=lambda x: x["total"], reverse=True
    )

    # por ferramenta (todas as de progresso, ordenadas por uso)
    por_ferramenta = []
    for t in TOOLS_PROGRESSO:
        meta = TOOLS[t]
        n = cont_ferr.get(t, 0)
        por_ferramenta.append({
            "id": t, "label": meta["label"], "cat": meta["cat"],
            "total": n, "minutos": n * meta["min"],
        })
    por_ferramenta.sort(key=lambda x: x["total"], reverse=True)

    # heatmap ultimos ~90 dias
    heatmap = []
    cont_dia = {}
    for _, dt in regs:
        d = dt.date()
        cont_dia[d] = cont_dia.get(d, 0) + 1
    for i in range(89, -1, -1):
        d = hoje.date() - timedelta(days=i)
        heatmap.append({"data": d.isoformat(), "total": cont_dia.get(d, 0)})

    # ferramentas nao usadas
    nao_usadas = []
    for t in TOOLS_PROGRESSO:
        if cont_ferr.get(t, 0) == 0:
            meta = TOOLS[t]
            nao_usadas.append({
                "id": t, "label": meta["label"], "cat": meta["cat"],
                "minutos_unit": meta["min"],
            })

    # marcos / conquistas
    marcos = [
        {"titulo": "Primeiro material",  "desc": "Gere seu primeiro entregavel",
         "ok": total >= 1,  "meta": 1,  "progresso": min(total, 1)},
        {"titulo": "Pegando o ritmo",    "desc": "5 entregaveis criados",
         "ok": total >= 5,  "meta": 5,  "progresso": min(total, 5)},
        {"titulo": "Em producao",        "desc": "20 entregaveis criados",
         "ok": total >= 20, "meta": 20, "progresso": min(total, 20)},
        {"titulo": "Explorador do kit",  "desc": "Use 5 ferramentas diferentes",
         "ok": ferramentas_usadas >= 5, "meta": 5, "progresso": min(ferramentas_usadas, 5)},
        {"titulo": "Kit completo",       "desc": "Experimente todas as ferramentas",
         "ok": ferramentas_usadas >= ferramentas_total, "meta": ferramentas_total,
         "progresso": ferramentas_usadas},
        {"titulo": "Constancia",         "desc": "3 semanas seguidas ativo",
         "ok": semanas_seguidas >= 3, "meta": 3, "progresso": min(semanas_seguidas, 3)},
    ]

    resumo = {
        "total_entregaveis": total,
        "horas_economizadas": round(horas, 1),
        "empresa": perfil.get("empresa", ""),
        "primeiro_uso": primeiro,
        "ultimo_uso": ultimo,
        "ferramentas_usadas": ferramentas_usadas,
        "ferramentas_total": ferramentas_total,
        "media_semanal": media_semanal,
        "dias_ativos": dias_ativos,
        "semanas_ativas": semanas_ativas,
        "semanas_seguidas": semanas_seguidas,
    }

    return jsonify({
        "resumo": resumo,
        "serie_semanas": serie,
        "por_categoria": por_categoria,
        "por_ferramenta": por_ferramenta,
        "heatmap": heatmap,
        "nao_usadas": nao_usadas,
        "marcos": marcos,
    })

# ---------------------------------------------------------------------------
# Rota - PDF de um output (opcional; usa reportlab se disponivel)
# ---------------------------------------------------------------------------
@app.route("/api/outputs/<output_id>/pdf")
def output_pdf(output_id):
    path = OUTPUT_DIR / f"{output_id}.json"
    if not path.exists():
        abort(404)
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.lib.units import cm
        from reportlab.pdfgen import canvas
        from reportlab.lib.utils import simpleSplit
    except ImportError:
        # front-end tem fallback de impressao quando recebe 501
        return jsonify({"erro": "reportlab nao instalado"}), 501

    o = load_json(path)
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    W, H = A4
    x, y = 2*cm, H - 2*cm
    c.setFont("Helvetica-Bold", 15)
    for line in simpleSplit(o.get("titulo", output_id), "Helvetica-Bold", 15, W - 4*cm):
        c.drawString(x, y, line); y -= 20
    y -= 8
    c.setFont("Helvetica", 11)
    for para in str(o.get("conteudo", "")).split("\n"):
        for line in simpleSplit(para, "Helvetica", 11, W - 4*cm) or [""]:
            if y < 2*cm:
                c.showPage(); c.setFont("Helvetica", 11); y = H - 2*cm
            c.drawString(x, y, line); y -= 15
    c.showPage(); c.save()
    buf.seek(0)
    return Response(buf.read(), mimetype="application/pdf",
                    headers={"Content-Disposition": f'attachment; filename="{output_id}.pdf"'})

# ---------------------------------------------------------------------------
# Rota - Status / health
# ---------------------------------------------------------------------------
@app.route("/api/status")
def status():
    outputs = list(OUTPUT_DIR.glob("*.json"))
    perfil  = load_json(PERFIL_FILE, {})
    return jsonify({
        "versao":          "0.4.0",
        "total_outputs":   len(outputs),
        "perfil_ok":       bool(perfil.get("empresa")),
        "timestamp":       datetime.now().isoformat(),
    })

# ---------------------------------------------------------------------------
# Abertura automatica do browser
# ---------------------------------------------------------------------------
def open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Kit Select IA - Dashboard")
    print("  Forum Negocios Select")
    print(f"\n  Servidor rodando em: http://localhost:{PORT}")
    print("  Feche esta janela para encerrar o dashboard.")
    print("="*60 + "\n")

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    app.run(host="127.0.0.1", port=PORT, debug=False)
