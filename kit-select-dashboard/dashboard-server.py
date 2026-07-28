#!/usr/bin/env python3
"""
Kit Select IA — Dashboard Server
Fórum Negócios Select

Servidor local Flask que expõe os dados gravados pelo Claude
para o dashboard.html via API REST simples.
Porta padrão: 5680
"""

import json
import os
import sys
import webbrowser
import threading
import time
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Verificar dependências antes de importar Flask
# ---------------------------------------------------------------------------
try:
    from flask import Flask, jsonify, request, send_from_directory, abort
    from flask_cors import CORS
except ImportError:
    print("\n" + "="*60)
    print("  ATENÇÃO: dependências não instaladas.")
    print("  Execute o seguinte comando e tente novamente:\n")
    print("  pip install flask flask-cors")
    print("="*60 + "\n")
    sys.exit(1)

# ---------------------------------------------------------------------------
# Configuração
# ---------------------------------------------------------------------------
BASE_DIR   = Path(__file__).parent.resolve()
DADOS_DIR  = BASE_DIR / "dados"
OUTPUT_DIR = DADOS_DIR / "outputs"
PERFIL_FILE = DADOS_DIR / "perfil-do-negocio.json"
PORT = 5680

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
    return jsonify(load_json(PERFIL_FILE, {}))

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
    Chamado pelas skills do kit automaticamente ao final de cada geração.
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
    return jsonify({"ok": True})

# ---------------------------------------------------------------------------
# Rota — Status / health
# ---------------------------------------------------------------------------
@app.route("/api/status")
def status():
    outputs = list(OUTPUT_DIR.glob("*.json"))
    perfil  = load_json(PERFIL_FILE, {})
    return jsonify({
        "versao":          "0.3.0",
        "total_outputs":   len(outputs),
        "perfil_ok":       bool(perfil.get("empresa")),
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
    print("  Feche esta janela para encerrar o dashboard.")
    print("="*60 + "\n")

    t = threading.Thread(target=open_browser, daemon=True)
    t.start()

    app.run(host="127.0.0.1", port=PORT, debug=False)
