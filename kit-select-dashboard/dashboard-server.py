#!/usr/bin/env python3
"""
Kit Select IA — Dashboard Server
Fórum Negócios Select

Servidor local Flask que expõe os dados gravados pelo Claude
para o dashboard.html via API REST simples.
Porta padrão: 5432
"""

import io
import json
import os
import re
import sys
import unicodedata
import uuid
import webbrowser
import threading
import time
from collections import Counter, defaultdict
from pathlib import Path
from datetime import datetime, timedelta

# ---------------------------------------------------------------------------
# Verificar dependências antes de importar Flask
# ---------------------------------------------------------------------------
try:
    from flask import Flask, jsonify, request, send_from_directory, abort, Response
    from flask_cors import CORS
except ImportError:
    print("\n" + "="*60)
    print("  ATENÇÃO: dependências não instaladas.")
    print("  Execute o seguinte comando e tente novamente:\n")
    print("  pip install flask flask-cors reportlab")
    print("="*60 + "\n")
    sys.exit(1)

# reportlab é opcional: sem ele o dashboard cai no modo "imprimir → salvar em PDF"
try:
    from reportlab.lib import colors
    from reportlab.lib.enums import TA_LEFT
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
    from reportlab.lib.units import mm
    from reportlab.platypus import (BaseDocTemplate, Frame, PageTemplate, Paragraph,
                                    Spacer, Table, TableStyle)
    PDF_OK = True
except ImportError:
    PDF_OK = False

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent.resolve()
DADOS_DIR  = BASE_DIR / "dados"
OUTPUT_DIR = DADOS_DIR / "outputs"
PERFIL_FILE = DADOS_DIR / "perfil-do-negocio.json"
AGENDA_FILE = DADOS_DIR / "agenda.json"
PORT = 5432

DADOS_DIR.mkdir(exist_ok=True)
OUTPUT_DIR.mkdir(exist_ok=True)

app = Flask(__name__, static_folder=str(BASE_DIR))
CORS(app)

# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def load_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return default if default is not None else {}

def save_json(path: Path, data):
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

# ---------------------------------------------------------------------------
# Perfil do negócio — JSON (dashboard) + fallback no .md (skill do plugin)
# ---------------------------------------------------------------------------
# A skill "configurar-negocio" grava um `perfil-do-negocio.md` na pasta de
# trabalho do Claude, enquanto o dashboard grava o JSON aqui em dados/. Para o
# perfil aparecer nos dois caminhos, o .md é lido como preenchimento das
# lacunas do JSON (o que foi editado no dashboard sempre tem prioridade).
PERFIL_MD_CANDIDATES = (
    DADOS_DIR / "perfil-do-negocio.md",
    BASE_DIR / "perfil-do-negocio.md",
    BASE_DIR.parent / "perfil-do-negocio.md",
)

# Seção do .md (sem acento, minúscula) -> campo do JSON do dashboard
PERFIL_MD_MAP = {
    "negocio":             "segmento",
    "cliente ideal":       "cliente",
    "produtos e servicos": "produtos",
    "diferencial":         "diferencial",
    "tom de voz":          "tom",
    "nunca fazer":         "vetos",
    "referencias":         "referencias",
}


def _sem_acento(texto: str) -> str:
    return unicodedata.normalize("NFKD", texto or "").encode("ascii", "ignore").decode()


def _valor_preenchido(texto: str) -> str:
    """Descarta os placeholders do gabarito da skill (ex.: "[o que faz]")."""
    t = (texto or "").strip()
    if not t or re.fullmatch(r"\[.*\]", t, flags=re.DOTALL):
        return ""
    # listas do gabarito viram uma linha só, sem os itens não preenchidos
    linhas = [l.strip().lstrip("-•* ").strip() for l in t.split("\n")]
    linhas = [l for l in linhas if l and not re.fullmatch(r".*\[[^\]]*\]\s*$", l)]
    return "\n".join(linhas).strip()


def parse_perfil_md(texto: str) -> dict:
    """Extrai os campos do perfil a partir do markdown gerado pela skill."""
    perfil, secao, buffer = {}, None, []

    def fechar():
        if secao and buffer:
            campo = PERFIL_MD_MAP.get(secao)
            if campo:
                valor = _valor_preenchido("\n".join(buffer))
                if valor:
                    perfil[campo] = valor

    for linha in (texto or "").replace("\r\n", "\n").split("\n"):
        m = re.match(r"^#\s+(.*)$", linha.strip())
        if m:                                   # "# Perfil do Negócio — Empresa"
            fechar()
            secao, buffer = None, []
            titulo = re.split(r"[—–-]", m.group(1), maxsplit=1)
            if len(titulo) > 1:
                empresa = _valor_preenchido(titulo[1])
                if empresa:
                    perfil["empresa"] = empresa
            continue
        m = re.match(r"^##\s+(.*)$", linha.strip())
        if m:                                   # "## Tom de voz"
            fechar()
            secao, buffer = _sem_acento(m.group(1)).strip().lower(), []
            continue
        if secao is not None:
            buffer.append(linha)

    fechar()
    return perfil


def load_perfil() -> dict:
    """Perfil efetivo: JSON do dashboard, completado pelo .md da skill."""
    perfil = load_json(PERFIL_FILE, {})
    if not isinstance(perfil, dict):
        perfil = {}

    md_path = next((p for p in PERFIL_MD_CANDIDATES if p.is_file()), None)
    if md_path is None:
        return perfil

    try:
        do_md = parse_perfil_md(md_path.read_text(encoding="utf-8"))
    except Exception:
        return perfil

    # o JSON (editado no dashboard) vence; o .md só preenche o que está vazio
    for campo, valor in do_md.items():
        if not str(perfil.get(campo) or "").strip():
            perfil[campo] = valor
    return perfil

# ---------------------------------------------------------------------------
# Rotas — Dashboard HTML
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return send_from_directory(str(BASE_DIR), "dashboard.html")

# ---------------------------------------------------------------------------
# Rotas — Perfil do negócio
# ---------------------------------------------------------------------------
@app.route("/api/perfil", methods=["GET"])
def get_perfil():
    return jsonify(load_perfil())

@app.route("/api/perfil", methods=["POST"])
def save_perfil():
    data = request.get_json(force=True)
    data["atualizado_em"] = datetime.now().isoformat()
    save_json(PERFIL_FILE, data)
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# Rotas — Outputs
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
            # Retorna resumo (sem conteudo completo) para a listagem
            items.append({
                "id":         o.get("id"),
                "ferramenta": o.get("ferramenta"),
                "titulo":     o.get("titulo"),
                "post_ref":   o.get("post_ref"),
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
    Recebe um output e grava em arquivo.
    As skills do kit não usam esta rota: elas gravam o JSON direto em
    dados/outputs/, que é a pasta lida por /api/outputs. Esta rota existe
    para o dashboard e para integrações externas.
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
    if path.exists():
        path.unlink()
    # o material sai também do calendário de conteúdo
    agenda = [a for a in load_agenda() if a.get("output_id") != output_id]
    save_json(AGENDA_FILE, agenda)
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# Rotas — Agenda (materiais marcados no calendário de conteúdo)
# ---------------------------------------------------------------------------
def load_agenda() -> list:
    dados = load_json(AGENDA_FILE, [])
    return dados if isinstance(dados, list) else []


def _agenda_ordenada(itens: list) -> list:
    return sorted(itens, key=lambda a: (a.get("data") or "", a.get("titulo") or ""))


@app.route("/api/agenda", methods=["GET"])
def list_agenda():
    return jsonify(_agenda_ordenada(load_agenda()))


@app.route("/api/agenda", methods=["POST"])
def save_agenda():
    """
    Marca um material salvo (anúncio, legenda, roteiro…) em uma data do
    calendário de conteúdo. Um material ocupa uma data só: reenviar o mesmo
    output_id remarca a data em vez de duplicar.
    """
    data = request.get_json(force=True) or {}
    output_id = (data.get("output_id") or "").strip()
    dia_iso   = (data.get("data") or "").strip()[:10]
    if not output_id or not dia_iso:
        abort(400)
    try:
        datetime.strptime(dia_iso, "%Y-%m-%d")
    except ValueError:
        abort(400)

    output = load_json(OUTPUT_DIR / f"{output_id}.json", {})
    if not output:
        abort(404)

    itens = [a for a in load_agenda() if a.get("output_id") != output_id]
    item = {
        "id":         "ag-" + uuid.uuid4().hex[:10],
        "output_id":  output_id,
        "ferramenta": output.get("ferramenta") or "",
        "titulo":     data.get("titulo") or output.get("titulo") or output_id,
        "data":       dia_iso,
        "criado_em":  datetime.now().isoformat(),
    }
    itens.append(item)
    save_json(AGENDA_FILE, _agenda_ordenada(itens))
    return jsonify({"ok": True, "item": item})


@app.route("/api/agenda/<agenda_id>", methods=["DELETE"])
def delete_agenda(agenda_id):
    itens = load_agenda()
    restantes = [a for a in itens
                 if a.get("id") != agenda_id and a.get("output_id") != agenda_id]
    save_json(AGENDA_FILE, _agenda_ordenada(restantes))
    return jsonify({"ok": True, "removidos": len(itens) - len(restantes)})

# ---------------------------------------------------------------------------
# Geração de PDF
# ---------------------------------------------------------------------------
NAVY = "#013B6B"
GOLD = "#C1A44F"
MID  = "#4A4A4A"
MUTED = "#8A8A8A"
LIGHT = "#EBEBEB"
OFFW  = "#F7F5F0"

FERRAMENTA_LABEL = {
    "configurar-negocio":   "Configurar negócio",
    "mes-de-conteudo":      "Mês de conteúdo",
    "legenda-no-tom":       "Legenda no meu tom",
    "roteiro-de-reels":     "Roteiro de Reels",
    "descricao-de-design":  "Descrição de design",
    "criar-anuncio":        "Criar anúncio",
    "proposta-comercial":   "Proposta comercial",
    "respostas-cliente":    "Respostas de cliente",
    "pesquisa-de-mercado":  "Pesquisa de mercado",
    "resumir-documento":    "Resumir documento",
}


def slugify(text: str, fallback: str = "output") -> str:
    """Nome de arquivo seguro, sem acentos."""
    t = unicodedata.normalize("NFKD", text or "").encode("ascii", "ignore").decode()
    t = re.sub(r"[^A-Za-z0-9]+", "-", t).strip("-").lower()
    return t[:60] or fallback


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;"))


def _inline_md(s: str) -> str:
    """Converte marcação inline simples (negrito/itálico/código) para tags do reportlab."""
    s = _xml_escape(s)
    s = re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", s)
    s = re.sub(r"(?<!\*)\*(?!\s)(.+?)(?<!\s)\*(?!\*)", r"<i>\1</i>", s)
    s = re.sub(r"`(.+?)`", r'<font face="Courier">\1</font>', s)
    return s


def _split_table_row(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _is_table_separator(line: str) -> bool:
    return bool(re.fullmatch(r"[\s|:\-]+", line.strip())) and "-" in line


def _build_styles():
    base = getSampleStyleSheet()
    return {
        "h1": ParagraphStyle("h1", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=15, leading=19, textColor=colors.HexColor(NAVY),
                             spaceBefore=12, spaceAfter=6),
        "h2": ParagraphStyle("h2", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=12.5, leading=16, textColor=colors.HexColor(NAVY),
                             spaceBefore=10, spaceAfter=4),
        "h3": ParagraphStyle("h3", parent=base["Normal"], fontName="Helvetica-Bold",
                             fontSize=11, leading=14.5, textColor=colors.HexColor("#8A6010"),
                             spaceBefore=8, spaceAfter=3),
        "body": ParagraphStyle("body", parent=base["Normal"], fontName="Helvetica",
                               fontSize=9.5, leading=14, textColor=colors.HexColor(MID),
                               alignment=TA_LEFT, spaceAfter=5),
        "bullet": ParagraphStyle("bullet", parent=base["Normal"], fontName="Helvetica",
                                 fontSize=9.5, leading=14, textColor=colors.HexColor(MID),
                                 leftIndent=12, bulletIndent=3, spaceAfter=3),
        "quote": ParagraphStyle("quote", parent=base["Normal"], fontName="Helvetica-Oblique",
                                fontSize=9.5, leading=14, textColor=colors.HexColor(MUTED),
                                leftIndent=12, spaceAfter=5),
        "cell": ParagraphStyle("cell", parent=base["Normal"], fontName="Helvetica",
                               fontSize=8.5, leading=11.5, textColor=colors.HexColor(MID)),
        "cellh": ParagraphStyle("cellh", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=8.5, leading=11.5, textColor=colors.white),
        "title": ParagraphStyle("title", parent=base["Normal"], fontName="Helvetica-Bold",
                                fontSize=20, leading=25, textColor=colors.HexColor(NAVY),
                                spaceAfter=4),
        "sub": ParagraphStyle("sub", parent=base["Normal"], fontName="Helvetica",
                              fontSize=9, leading=13, textColor=colors.HexColor(MUTED),
                              spaceAfter=2),
    }


def _make_table(rows, styles, avail_width):
    """Monta uma tabela markdown com cabeçalho na cor da marca."""
    ncols = max(len(r) for r in rows)
    rows = [r + [""] * (ncols - len(r)) for r in rows]
    header, body = rows[0], rows[1:]
    data = [[Paragraph(_inline_md(c), styles["cellh"]) for c in header]]
    data += [[Paragraph(_inline_md(c), styles["cell"]) for c in r] for r in body]

    t = Table(data, colWidths=[avail_width / ncols] * ncols, repeatRows=1, hAlign="LEFT")
    cmds = [
        ("BACKGROUND",    (0, 0), (-1, 0), colors.HexColor(NAVY)),
        ("GRID",          (0, 0), (-1, -1), 0.4, colors.HexColor(LIGHT)),
        ("VALIGN",        (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",   (0, 0), (-1, -1), 5),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 5),
        ("TOPPADDING",    (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    if body:  # zebra só quando existe corpo além do cabeçalho
        cmds.append(("ROWBACKGROUNDS", (0, 1), (-1, -1),
                     [colors.white, colors.HexColor(OFFW)]))
    t.setStyle(TableStyle(cmds))
    return t


def _rule(width, thickness, color_hex):
    """Filete horizontal (usado como régua e como linha da marca)."""
    return Table([[""]], colWidths=[width], rowHeights=[thickness],
                 style=TableStyle([
                     ("BACKGROUND",    (0, 0), (-1, -1), colors.HexColor(color_hex)),
                     ("LEFTPADDING",   (0, 0), (-1, -1), 0),
                     ("RIGHTPADDING",  (0, 0), (-1, -1), 0),
                     ("TOPPADDING",    (0, 0), (-1, -1), 0),
                     ("BOTTOMPADDING", (0, 0), (-1, -1), 0),
                 ]))


def _flow_from_text(text: str, styles, avail_width):
    """Converte o markdown leve gerado pelas skills em flowables do reportlab."""
    flow = []
    lines = (text or "").replace("\r\n", "\n").split("\n")
    i = 0
    while i < len(lines):
        raw = lines[i]
        line = raw.strip()

        if not line:
            flow.append(Spacer(1, 4))
            i += 1
            continue

        # Tabela markdown
        if line.startswith("|") and line.count("|") >= 2:
            block = []
            while i < len(lines) and lines[i].strip().startswith("|"):
                cur = lines[i].strip()
                if not _is_table_separator(cur):
                    block.append(_split_table_row(cur))
                i += 1
            if block:
                flow.append(Spacer(1, 4))
                flow.append(_make_table(block, styles, avail_width))
                flow.append(Spacer(1, 8))
            continue

        # Régua horizontal
        if re.fullmatch(r"(-{3,}|_{3,}|\*{3,})", line):
            flow.append(Spacer(1, 6))
            flow.append(_rule(avail_width, 0.6, LIGHT))
            flow.append(Spacer(1, 8))
            i += 1
            continue

        # Títulos
        m = re.match(r"^(#{1,6})\s+(.*)$", line)
        if m:
            level = len(m.group(1))
            key = "h1" if level <= 1 else ("h2" if level == 2 else "h3")
            flow.append(Paragraph(_inline_md(m.group(2)), styles[key]))
            i += 1
            continue

        # Citação
        if line.startswith(">"):
            flow.append(Paragraph(_inline_md(line.lstrip("> ").strip()), styles["quote"]))
            i += 1
            continue

        # Lista com marcador
        m = re.match(r"^[-*•]\s+(.*)$", line)
        if m:
            flow.append(Paragraph(_inline_md(m.group(1)), styles["bullet"], bulletText="•"))
            i += 1
            continue

        # Lista numerada
        m = re.match(r"^(\d+)[.)]\s+(.*)$", line)
        if m:
            flow.append(Paragraph(_inline_md(m.group(2)), styles["bullet"],
                                  bulletText=m.group(1) + "."))
            i += 1
            continue

        flow.append(Paragraph(_inline_md(line), styles["body"]))
        i += 1

    return flow


def build_pdf(output: dict, perfil: dict) -> bytes:
    """Gera o PDF de um output com a identidade do Fórum Negócios Select."""
    styles = _build_styles()
    buf = io.BytesIO()

    margin_x, margin_top, margin_bottom = 18 * mm, 22 * mm, 18 * mm
    page_w, page_h = A4
    avail_width = page_w - 2 * margin_x

    titulo     = output.get("titulo") or output.get("id") or "Output"
    ferramenta = FERRAMENTA_LABEL.get(output.get("ferramenta"), output.get("ferramenta") or "Kit Select IA")
    empresa    = (perfil or {}).get("empresa") or ""
    try:
        gerado = datetime.fromisoformat(str(output.get("data"))).strftime("%d/%m/%Y")
    except Exception:
        gerado = datetime.now().strftime("%d/%m/%Y")

    def decorate(canvas, doc):
        canvas.saveState()
        # Faixa superior da marca
        canvas.setFillColor(colors.HexColor(NAVY))
        canvas.rect(0, page_h - 8 * mm, page_w, 8 * mm, stroke=0, fill=1)
        canvas.setFillColor(colors.HexColor(GOLD))
        canvas.rect(0, page_h - 8 * mm, 45 * mm, 8 * mm, stroke=0, fill=1)
        # Rodapé
        canvas.setFillColor(colors.HexColor(MUTED))
        canvas.setFont("Helvetica", 7.5)
        canvas.drawString(margin_x, 10 * mm, "Kit Select IA · Fórum Negócios Select")
        canvas.drawRightString(page_w - margin_x, 10 * mm, f"Página {canvas.getPageNumber()}")
        canvas.setStrokeColor(colors.HexColor(LIGHT))
        canvas.setLineWidth(0.5)
        canvas.line(margin_x, 13 * mm, page_w - margin_x, 13 * mm)
        canvas.restoreState()

    doc = BaseDocTemplate(buf, pagesize=A4,
                          leftMargin=margin_x, rightMargin=margin_x,
                          topMargin=margin_top, bottomMargin=margin_bottom,
                          title=titulo, author="Kit Select IA")
    # padding zerado: as margens já estão no frame, e assim uma tabela de
    # largura total (avail_width) cabe exatamente na área útil
    frame = Frame(margin_x, margin_bottom, avail_width,
                  page_h - margin_top - margin_bottom, id="body",
                  leftPadding=0, rightPadding=0, topPadding=0, bottomPadding=0)
    doc.addPageTemplates([PageTemplate(id="main", frames=[frame], onPage=decorate)])

    linha_meta = " · ".join([p for p in [ferramenta, empresa, f"gerado em {gerado}"] if p])
    cabecalho = [
        Paragraph(_xml_escape(titulo), styles["title"]),
        Paragraph(_xml_escape(linha_meta), styles["sub"]),
        Spacer(1, 6),
        _rule(avail_width, 1.6, GOLD),
        Spacer(1, 12),
    ]

    conteudo = output.get("conteudo")
    if not isinstance(conteudo, str):
        conteudo = json.dumps(conteudo, ensure_ascii=False, indent=2) if conteudo else "(sem conteúdo)"

    doc.build(cabecalho + _flow_from_text(conteudo, styles, avail_width))
    return buf.getvalue()


@app.route("/api/outputs/<output_id>/pdf", methods=["GET"])
def output_pdf(output_id):
    path = OUTPUT_DIR / f"{output_id}.json"
    if not path.exists():
        abort(404)
    if not PDF_OK:
        return jsonify({
            "erro": "pdf_indisponivel",
            "mensagem": "Instale a biblioteca de PDF: pip install reportlab",
        }), 501

    output = load_json(path)
    try:
        pdf = build_pdf(output, load_perfil())
    except Exception as e:
        return jsonify({"erro": "falha_ao_gerar", "mensagem": str(e)}), 500

    nome = slugify(output.get("titulo") or output_id, output_id) + ".pdf"
    return Response(pdf, mimetype="application/pdf", headers={
        "Content-Disposition": f'attachment; filename="{nome}"',
        "Content-Length": str(len(pdf)),
    })


# ---------------------------------------------------------------------------
# Uso da plataforma — métricas derivadas dos outputs salvos
# ---------------------------------------------------------------------------
FERRAMENTA_CAT = {
    "configurar-negocio":  "base",
    "mes-de-conteudo":     "conteudo",
    "legenda-no-tom":      "conteudo",
    "roteiro-de-reels":    "conteudo",
    "descricao-de-design": "conteudo",
    "criar-anuncio":       "vender",
    "proposta-comercial":  "vender",
    "respostas-cliente":   "atender",
    "pesquisa-de-mercado": "mercado",
    "resumir-documento":   "docs",
}

# Minutos que cada entregável levaria para ser feito à mão (base para o
# "tempo economizado" mostrado ao mentorado). Números conservadores.
MINUTOS_POR_ENTREGAVEL = {
    "configurar-negocio":   30,
    "mes-de-conteudo":     240,
    "legenda-no-tom":       25,
    "roteiro-de-reels":     40,
    "descricao-de-design":  35,
    "criar-anuncio":        45,
    "proposta-comercial":   90,
    "respostas-cliente":    60,
    "pesquisa-de-mercado": 180,
    "resumir-documento":    45,
}
MINUTOS_PADRAO = 30

DIAS_HEATMAP = 91   # 13 semanas
SEMANAS_SERIE = 8


def _conteudo_texto(conteudo) -> str:
    if isinstance(conteudo, str):
        return conteudo
    if conteudo:
        return json.dumps(conteudo, ensure_ascii=False)
    return ""


def _parse_data(valor):
    """Aceita ISO completo ou só a data; devolve datetime ou None."""
    if not valor:
        return None
    try:
        return datetime.fromisoformat(str(valor).replace("Z", ""))
    except Exception:
        pass
    for fmt in ("%Y-%m-%d", "%d/%m/%Y"):
        try:
            return datetime.strptime(str(valor)[:10], fmt)
        except Exception:
            continue
    return None


def _coletar_outputs():
    """Lê todos os outputs uma única vez, já normalizados."""
    itens = []
    for f in OUTPUT_DIR.glob("*.json"):
        o = load_json(f)
        if not o:
            continue
        dt = _parse_data(o.get("data"))
        if dt is None:
            try:
                dt = datetime.fromtimestamp(f.stat().st_mtime)
            except Exception:
                dt = None
        texto = _conteudo_texto(o.get("conteudo"))
        itens.append({
            "id":         o.get("id") or f.stem,
            "ferramenta": o.get("ferramenta") or "",
            "titulo":     o.get("titulo") or "",
            "dt":         dt,
            "palavras":   len(texto.split()),
        })
    return itens


def _marcos(total, ferramentas_usadas, horas, semanas_seguidas, perfil_ok):
    """Conquistas simples — reforço positivo para o mentorado."""
    return [
        {"id": "perfil",     "titulo": "Base montada",
         "desc": "Perfil do negócio configurado",
         "ok": bool(perfil_ok)},
        {"id": "primeiro",   "titulo": "Primeiro entregável",
         "desc": "Você gerou seu primeiro material",
         "ok": total >= 1},
        {"id": "dez",        "titulo": "10 entregáveis",
         "desc": "Dez materiais salvos no painel",
         "ok": total >= 10, "progresso": min(total, 10), "meta": 10},
        {"id": "explorador", "titulo": "Explorador do kit",
         "desc": "Usou 5 ferramentas diferentes",
         "ok": ferramentas_usadas >= 5, "progresso": min(ferramentas_usadas, 5), "meta": 5},
        {"id": "kit-todo",   "titulo": "Kit completo",
         "desc": "Experimentou as 10 ferramentas",
         "ok": ferramentas_usadas >= 10, "progresso": ferramentas_usadas, "meta": 10},
        {"id": "constancia", "titulo": "Constância",
         "desc": "4 semanas seguidas usando o kit",
         "ok": semanas_seguidas >= 4, "progresso": min(semanas_seguidas, 4), "meta": 4},
        {"id": "dia",        "titulo": "Um dia de trabalho poupado",
         "desc": "8 horas economizadas com o kit",
         "ok": horas >= 8, "progresso": round(min(horas, 8), 1), "meta": 8},
    ]


@app.route("/api/uso")
def uso():
    itens  = _coletar_outputs()
    perfil = load_perfil()
    hoje   = datetime.now().date()

    total     = len(itens)
    palavras  = sum(i["palavras"] for i in itens)
    minutos   = sum(MINUTOS_POR_ENTREGAVEL.get(i["ferramenta"], MINUTOS_PADRAO) for i in itens)
    horas     = round(minutos / 60, 1)

    # Por ferramenta ------------------------------------------------------
    cont_fer   = Counter(i["ferramenta"] for i in itens)
    ultimo_fer = {}
    for i in itens:
        d = i["dt"]
        if d and (i["ferramenta"] not in ultimo_fer or d > ultimo_fer[i["ferramenta"]]):
            ultimo_fer[i["ferramenta"]] = d

    por_ferramenta = []
    for fid, label in FERRAMENTA_LABEL.items():
        n = cont_fer.get(fid, 0)
        por_ferramenta.append({
            "id":     fid,
            "label":  label,
            "cat":    FERRAMENTA_CAT.get(fid, "base"),
            "total":  n,
            "ultimo": ultimo_fer[fid].isoformat() if fid in ultimo_fer else None,
            "minutos":      n * MINUTOS_POR_ENTREGAVEL.get(fid, MINUTOS_PADRAO),
            "minutos_unit": MINUTOS_POR_ENTREGAVEL.get(fid, MINUTOS_PADRAO),
        })
    por_ferramenta.sort(key=lambda x: (-x["total"], x["label"]))

    usadas     = [f for f in por_ferramenta if f["total"] > 0]
    nao_usadas = [f for f in por_ferramenta if f["total"] == 0]

    # Por categoria -------------------------------------------------------
    cont_cat = Counter(FERRAMENTA_CAT.get(i["ferramenta"], "base") for i in itens)
    por_categoria = [{"cat": c, "total": n} for c, n in cont_cat.most_common()]

    # Linha do tempo ------------------------------------------------------
    por_dia = defaultdict(int)
    for i in itens:
        if i["dt"]:
            por_dia[i["dt"].date()] += 1

    inicio_heat = hoje - timedelta(days=DIAS_HEATMAP - 1)
    inicio_heat -= timedelta(days=inicio_heat.weekday())      # começa na segunda
    heatmap = []
    d = inicio_heat
    while d <= hoje:
        heatmap.append({"data": d.isoformat(), "total": por_dia.get(d, 0)})
        d += timedelta(days=1)

    seg_atual = hoje - timedelta(days=hoje.weekday())
    serie_semanas = []
    for k in range(SEMANAS_SERIE - 1, -1, -1):
        ini = seg_atual - timedelta(weeks=k)
        fim = ini + timedelta(days=6)
        n = sum(v for dia, v in por_dia.items() if ini <= dia <= fim)
        serie_semanas.append({
            "inicio": ini.isoformat(),
            "label":  ini.strftime("%d/%m"),
            "total":  n,
            "atual":  k == 0,
        })

    dias_ativos = len(por_dia)
    semanas_ativas = len({(dia - timedelta(days=dia.weekday())) for dia in por_dia})

    # Semanas seguidas com atividade, terminando na semana atual (ou anterior)
    semanas_com_uso = {(dia - timedelta(days=dia.weekday())) for dia in por_dia}
    semanas_seguidas = 0
    cursor = seg_atual if seg_atual in semanas_com_uso else seg_atual - timedelta(weeks=1)
    while cursor in semanas_com_uso:
        semanas_seguidas += 1
        cursor -= timedelta(weeks=1)

    datas = sorted(d for d in por_dia)
    primeiro = datas[0].isoformat() if datas else None
    ultimo   = datas[-1].isoformat() if datas else None
    dias_desde_inicio = (hoje - datas[0]).days + 1 if datas else 0
    media_semanal = round(total / max(1, dias_desde_inicio / 7), 1) if datas else 0

    # Recentes ------------------------------------------------------------
    recentes = sorted([i for i in itens if i["dt"]], key=lambda x: x["dt"], reverse=True)[:5]

    return jsonify({
        "resumo": {
            "total_entregaveis":  total,
            "palavras":           palavras,
            "minutos_economizados": minutos,
            "horas_economizadas": horas,
            "ferramentas_usadas": len(usadas),
            "ferramentas_total":  len(FERRAMENTA_LABEL),
            "dias_ativos":        dias_ativos,
            "semanas_ativas":     semanas_ativas,
            "semanas_seguidas":   semanas_seguidas,
            "media_semanal":      media_semanal,
            "primeiro_uso":       primeiro,
            "ultimo_uso":         ultimo,
            "dias_desde_inicio":  dias_desde_inicio,
            "perfil_ok":          bool(perfil.get("empresa")),
            "empresa":            perfil.get("empresa") or "",
        },
        "por_ferramenta": por_ferramenta,
        "nao_usadas":     nao_usadas,
        "por_categoria":  por_categoria,
        "heatmap":        heatmap,
        "serie_semanas":  serie_semanas,
        "marcos":         _marcos(total, len(usadas), horas, semanas_seguidas,
                                  bool(perfil.get("empresa"))),
        "recentes": [{
            "id": i["id"], "titulo": i["titulo"], "ferramenta": i["ferramenta"],
            "data": i["dt"].isoformat() if i["dt"] else None,
        } for i in recentes],
    })


# ---------------------------------------------------------------------------
# Rota — Status / health
# ---------------------------------------------------------------------------
@app.route("/api/status")
def status():
    outputs = list(OUTPUT_DIR.glob("*.json"))
    perfil  = load_perfil()
    return jsonify({
        "versao":          "0.6.1",
        "total_outputs":   len(outputs),
        "total_agendados": len(load_agenda()),
        "perfil_ok":       bool(perfil.get("empresa")),
        "pdf_ok":          PDF_OK,
        "timestamp":       datetime.now().isoformat(),
    })

# ---------------------------------------------------------------------------
# Abertura automática do browser
# ---------------------------------------------------------------------------
def open_browser():
    time.sleep(1.2)
    webbrowser.open(f"http://localhost:{PORT}")

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    print("\n" + "="*60)
    print("  Kit Select IA — Dashboard")
    print("  Fórum Negócios Select")
    print(f"\n  Servidor rodando em: http://localhost:{PORT}")
    if not PDF_OK:
        print("\n  [!] Download em PDF desativado (reportlab não instalado).")
        print("      Para ativar: pip install reportlab")
        print("      Sem ele, o botão abre a janela de impressão do navegador.")
    print("\n  Feche esta janela para encerrar o dashboard.")
    print("="*60 + "\n")

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    app.run(host="127.0.0.1", port=PORT, debug=False)
