import json
import os
import subprocess
import sys
import tempfile
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, send_file, jsonify, flash

app = Flask(__name__)
app.secret_key = "ibiti-secret-key-2024"
app.config['JSON_AS_ASCII'] = False  # Ensure JSON responses use UTF-8
app.config['CHARSET'] = 'utf-8'  # Explicit UTF-8 charset

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")
OUTPUT_DIR = os.path.join(BASE_DIR, "output")
PDF_TEMPLATE = os.path.join(BASE_DIR, "Requerimento_Visitante_Vazio.pdf")
FILL_SCRIPT = os.path.join(BASE_DIR, "fill_pdf_form_with_annotations.py")

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

OWNER_FILE = os.path.join(DATA_DIR, "owners.json")
VISITORS_FILE = os.path.join(DATA_DIR, "visitors.json")


def load_owners():
    # Migration: if old owner.json exists, convert to owners.json
    if os.path.exists(OWNER_FILE):
        with open(OWNER_FILE, encoding="utf-8") as f:
            return json.load(f)
    elif os.path.exists(os.path.join(DATA_DIR, "owner.json")):
        # Migrate old single owner format
        with open(os.path.join(DATA_DIR, "owner.json"), encoding="utf-8") as f:
            old_owner = json.load(f)
        if old_owner and old_owner.get("nome"):
            old_owner["id"] = int(datetime.now().timestamp() * 1000)
            owners = [old_owner]
            save_owners(owners)
            # Remove old file
            os.remove(os.path.join(DATA_DIR, "owner.json"))
            return owners
    return []


def save_owners(data):
    with open(OWNER_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_visitors():
    if os.path.exists(VISITORS_FILE):
        with open(VISITORS_FILE, encoding="utf-8") as f:
            return json.load(f)
    return []


def save_visitors(data):
    with open(VISITORS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def build_fields_json(owner, visitors, date_mode, single_date, date_start, date_end):
    """Build the fields.json structure for the PDF fill script."""
    pdf_w1, pdf_h1 = 595.32, 841.92
    pdf_w2, pdf_h2 = 595.32, 841.92

    pages = [
        {"page_number": 1, "pdf_width": pdf_w1, "pdf_height": pdf_h1},
        {"page_number": 2, "pdf_width": pdf_w2, "pdf_height": pdf_h2},
    ]

    form_fields = []
    fs = 8  # font size

    def field(page, desc, label, lbb, ebb, text, font_size=None):
        f = {
            "page_number": page,
            "description": desc,
            "field_label": label,
            "label_bounding_box": lbb,
            "entry_bounding_box": ebb,
            "entry_text": {"text": text, "font_size": font_size or fs},
        }
        form_fields.append(f)

    # --- Owner name ---
    field(1, "Owner name", "Eu,", [156, 184.7, 173.5, 196.7],
          [179.4, 184.7, 524.5, 197.0], owner.get("nome", ""), font_size=10)

    # --- Quadra / Lote ---
    field(1, "Quadra", "Quadra:", [70.9, 222.8, 114.7, 234.8],
          [134.4, 222.8, 185.0, 235.0], owner.get("quadra", ""), font_size=10)
    field(1, "Lote", "Lote nº:", [175.1, 222.8, 217.2, 234.8],
          [236.8, 222.8, 287.0, 235.0], owner.get("lote", ""), font_size=10)

    # --- Owner RG / CPF ---
    field(1, "Owner RG", "RG nº", [482.6, 222.8, 524.7, 234.8],
          [70.9, 241.7, 210.0, 254.0], owner.get("rg", ""), font_size=10)
    field(1, "Owner CPF", "CPF nº", [217.5, 241.7, 253.6, 254.0],
          [256.3, 241.7, 367.0, 254.0], owner.get("cpf", ""), font_size=10)

    # --- Tipo de morador (X on the correct checkbox) ---
    tipo = owner.get("tipo", "morador")
    if tipo == "proprietario":
        field(1, "Tipo proprietário X", "proprietário", [70.9, 203.7, 91.9, 215.7],
              [76.0, 203.7, 88.0, 215.5], "X", font_size=10)
    elif tipo == "inquilino":
        field(1, "Tipo inquilino X", "inquilino", [181.8, 203.7, 202.6, 215.7],
              [186.0, 203.7, 199.0, 215.5], "X", font_size=10)
    # morador already has X pre-printed in the template

    # --- Date ---
    months_pt = ["janeiro","fevereiro","março","abril","maio","junho",
                 "julho","agosto","setembro","outubro","novembro","dezembro"]
    if date_mode == "single" and single_date:
        try:
            dt = datetime.strptime(single_date, "%Y-%m-%d")
        except:
            dt = datetime.now()
        
        # Fill day, month, year separately in header
        field(1, "Header day", "no dia", [372.0, 279.8, 395.0, 291.8],
              [407.0, 279.8, 430.0, 292.0], f"{dt.day:02d}", font_size=10)
        field(1, "Header month", "de", [422.0, 279.8, 435.0, 291.8],
              [442.0, 279.8, 475.0, 292.0], f"{dt.month:02d}", font_size=10)
        field(1, "Header year", "de", [458.0, 279.8, 471.0, 291.8],
              [471.0, 279.8, 494.3, 292.0], str(dt.year), font_size=10)
    elif date_mode == "range" and date_start and date_end:
        try:
            ds = datetime.strptime(date_start, "%Y-%m-%d").strftime("%d/%m/%Y")
            de = datetime.strptime(date_end, "%Y-%m-%d").strftime("%d/%m/%Y")
        except:
            ds, de = date_start, date_end
        field(1, "Date range start", "de", [511.3, 279.8, 524.4, 291.8],
              [70.9, 298.8, 157.0, 311.0], ds, font_size=10)
        field(1, "Date range end", "a", [163.4, 298.8, 169.4, 311.0],
              [175.3, 298.8, 261.0, 311.0], de, font_size=10)

    # --- Visitor blocks ---
    # (page, nome_top, rg_top, end_top, bairro_top, rel_top)
    visitor_positions = [
        (1, 440.3, 459.3, 478.3, 497.3, 516.3),
        (1, 564.6, 583.7, 602.6, 621.6, 640.7),
        (2, 97.0,  116.1, 135.0, 154.0, 173.1),
        (2, 221.4, 240.4, 259.4, 278.5, 297.4),
        (2, 345.8, 364.8, 383.8, 402.8, 421.8),
    ]

    for i, v in enumerate(visitors[:5]):
        pg, nt, rt, et, bt, relt = visitor_positions[i]

        field(pg, f"V{i+1} Nome", "Nome:", [76.6, nt, 112.4, nt+12],
              [115.4, nt, 517.4, nt+12], v.get("nome", ""), font_size=10)
        field(pg, f"V{i+1} RG", "RG:", [76.6, rt, 96.8, rt+12],
              [99.8, rt, 218.0, rt+12], v.get("rg", ""), font_size=10)
        field(pg, f"V{i+1} CPF", "CPF", [225.8, rt, 248.1, rt+12],
              [251.2, rt, 362.2, rt+12], v.get("cpf", ""), font_size=10)
        field(pg, f"V{i+1} Tel", "Telefone:", [365.2, rt, 413.8, rt+12],
              [416.8, rt, 518.8, rt+12], v.get("telefone", ""), font_size=10)
        field(pg, f"V{i+1} Endereço", "Endereço:", [76.6, et, 129.4, et+12],
              [132.4, et, 516.4, et+12], v.get("endereco", ""), font_size=10)
        field(pg, f"V{i+1} Bairro", "Bairro:", [76.6, bt, 112.6, bt+12],
              [115.6, bt, 218.0, bt+12], v.get("bairro", ""), font_size=10)
        field(pg, f"V{i+1} Cidade", "Cidade:", [223.4, bt, 264.9, bt+12],
              [267.9, bt, 393.9, bt+12], v.get("cidade", ""), font_size=10)
        field(pg, f"V{i+1} CEP", "CEP", [396.9, bt, 419.9, bt+12],
              [422.9, bt, 518.9, bt+12], v.get("cep", ""), font_size=10)

        # Relationship checkbox
        rel = v.get("relacionamento", "amigo")
        rel_detail = v.get("relacionamento_detalhe", "")
        if rel == "amigo":
            field(pg, f"V{i+1} Rel Amigo X", "Amigo", [76.6, relt, 92.1, relt+12],
                  [81.0, relt, 91.0, relt+11], "X", font_size=10)
        elif rel == "parente":
            field(pg, f"V{i+1} Rel Parente X", "Parente", [152.5, relt, 167.9, relt+12],
                  [157.0, relt, 168.0, relt+11], "X", font_size=10)
            if rel_detail:
                field(pg, f"V{i+1} Parente detalhe", "Parente:", [170.4, relt, 213.7, relt+12],
                      [216.2, relt, 306.2, relt+12], rel_detail, font_size=10)
        elif rel == "outro":
            field(pg, f"V{i+1} Rel Outro X", "Outro", [313.5, relt, 329.1, relt+12],
                  [318.0, relt, 329.0, relt+11], "X", font_size=10)
            if rel_detail:
                field(pg, f"V{i+1} Outro detalhe", "Outro:", [331.4, relt, 366.3, relt+12],
                      [368.8, relt, 518.7, relt+12], rel_detail, font_size=10)

    # --- Date line at bottom page 2 ---
    today = datetime.today()

    if date_mode == "single" and single_date:
        try:
            d = datetime.strptime(single_date, "%Y-%m-%d")
        except:
            d = today
    elif date_mode == "range" and date_start:
        try:
            d = datetime.strptime(date_start, "%Y-%m-%d")
        except:
            d = today
    else:
        d = today

    field(2, "Signature day", "Sorocaba,", [156.0, 533.4, 207.1, 545.4],
          [210.1, 533.4, 246.1, 545.4], str(d.day), font_size=10)
    field(2, "Signature month", "de", [249.1, 533.4, 262.2, 545.4],
          [265.2, 533.4, 355.3, 545.4], months_pt[d.month - 1], font_size=10)
    field(2, "Signature year", "de", [358.3, 533.4, 371.3, 545.4],
          [374.3, 533.4, 431.4, 545.4], str(d.year), font_size=10)

    return {"pages": pages, "form_fields": form_fields}


@app.route("/")
def index():
    owners = load_owners()
    visitors = load_visitors()
    return render_template("index.html", owners=owners, visitors=visitors,
                           today=datetime.today().strftime("%Y-%m-%d"))


@app.route("/owners")
def owners():
    return render_template("owners.html", owners=load_owners())


@app.route("/owner/add", methods=["GET", "POST"])
def add_owner():
    if request.method == "POST":
        owners = load_owners()
        new_owner = {
            "id": int(datetime.now().timestamp() * 1000),
            "nome": request.form.get("nome", "").strip(),
            "quadra": request.form.get("quadra", "").strip(),
            "lote": request.form.get("lote", "").strip(),
            "rg": request.form.get("rg", "").strip(),
            "cpf": request.form.get("cpf", "").strip(),
            "tipo": request.form.get("tipo", "morador"),
        }
        owners.append(new_owner)
        save_owners(owners)
        flash(f"Proprietário '{new_owner['nome']}' adicionado!", "success")
        return redirect(url_for("owners"))
    return render_template("owner_form.html", owner=None, action="Adicionar")


@app.route("/owner/edit/<int:oid>", methods=["GET", "POST"])
def edit_owner(oid):
    owners = load_owners()
    owner = next((x for x in owners if x["id"] == oid), None)
    if not owner:
        flash("Proprietário não encontrado.", "error")
        return redirect(url_for("owners"))
    if request.method == "POST":
        owner.update({
            "nome": request.form.get("nome", "").strip(),
            "quadra": request.form.get("quadra", "").strip(),
            "lote": request.form.get("lote", "").strip(),
            "rg": request.form.get("rg", "").strip(),
            "cpf": request.form.get("cpf", "").strip(),
            "tipo": request.form.get("tipo", "morador"),
        })
        save_owners(owners)
        flash(f"Proprietário '{owner['nome']}' atualizado!", "success")
        return redirect(url_for("owners"))
    return render_template("owner_form.html", owner=owner, action="Editar")


@app.route("/owner/delete/<int:oid>", methods=["POST"])
def delete_owner(oid):
    owners = load_owners()
    owners = [x for x in owners if x["id"] != oid]
    save_owners(owners)
    flash("Proprietário removido.", "success")
    return redirect(url_for("owners"))


@app.route("/visitors")
def visitors():
    return render_template("visitors.html", visitors=load_visitors())


@app.route("/visitor/add", methods=["GET", "POST"])
def add_visitor():
    if request.method == "POST":
        visitors = load_visitors()
        new_v = {
            "id": int(datetime.now().timestamp() * 1000),
            "nome": request.form.get("nome", "").strip(),
            "rg": request.form.get("rg", "").strip(),
            "cpf": request.form.get("cpf", "").strip(),
            "telefone": request.form.get("telefone", "").strip(),
            "endereco": request.form.get("endereco", "").strip(),
            "bairro": request.form.get("bairro", "").strip(),
            "cidade": request.form.get("cidade", "").strip(),
            "cep": request.form.get("cep", "").strip(),
            "relacionamento": request.form.get("relacionamento", "amigo"),
            "relacionamento_detalhe": request.form.get("relacionamento_detalhe", "").strip(),
        }
        visitors.append(new_v)
        save_visitors(visitors)
        flash(f"Visitante '{new_v['nome']}' adicionado!", "success")
        return redirect(url_for("visitors"))
    return render_template("visitor_form.html", visitor=None, action="Adicionar")


@app.route("/visitor/edit/<int:vid>", methods=["GET", "POST"])
def edit_visitor(vid):
    visitors = load_visitors()
    v = next((x for x in visitors if x["id"] == vid), None)
    if not v:
        flash("Visitante não encontrado.", "error")
        return redirect(url_for("visitors"))
    if request.method == "POST":
        v.update({
            "nome": request.form.get("nome", "").strip(),
            "rg": request.form.get("rg", "").strip(),
            "cpf": request.form.get("cpf", "").strip(),
            "telefone": request.form.get("telefone", "").strip(),
            "endereco": request.form.get("endereco", "").strip(),
            "bairro": request.form.get("bairro", "").strip(),
            "cidade": request.form.get("cidade", "").strip(),
            "cep": request.form.get("cep", "").strip(),
            "relacionamento": request.form.get("relacionamento", "amigo"),
            "relacionamento_detalhe": request.form.get("relacionamento_detalhe", "").strip(),
        })
        save_visitors(visitors)
        flash(f"Visitante '{v['nome']}' atualizado!", "success")
        return redirect(url_for("visitors"))
    return render_template("visitor_form.html", visitor=v, action="Editar")


@app.route("/visitor/delete/<int:vid>", methods=["POST"])
def delete_visitor(vid):
    visitors = load_visitors()
    visitors = [x for x in visitors if x["id"] != vid]
    save_visitors(visitors)
    flash("Visitante removido.", "success")
    return redirect(url_for("visitors"))


@app.route("/generate", methods=["POST"])
def generate():
    owner_id = request.form.get("owner_id")
    if not owner_id:
        flash("Selecione um proprietário.", "error")
        return redirect(url_for("index"))
    
    try:
        owner_id = int(owner_id)
    except ValueError:
        flash("ID de proprietário inválido.", "error")
        return redirect(url_for("index"))
    
    owners = load_owners()
    owner = next((o for o in owners if o["id"] == owner_id), None)
    if not owner:
        flash("Proprietário não encontrado.", "error")
        return redirect(url_for("index"))
    
    if not owner.get("nome"):
        flash("Os dados do proprietário selecionado estão incompletos.", "error")
        return redirect(url_for("index"))

    all_visitors = load_visitors()
    selected_ids = request.form.getlist("visitor_ids")
    selected_ids = [int(x) for x in selected_ids]
    selected_visitors = [v for v in all_visitors if v["id"] in selected_ids]

    if not selected_visitors:
        flash("Selecione pelo menos um visitante.", "error")
        return redirect(url_for("index"))
    if len(selected_visitors) > 5:
        flash("Máximo de 5 visitantes por requerimento.", "error")
        return redirect(url_for("index"))

    date_mode = request.form.get("date_mode", "single")
    single_date = request.form.get("single_date", "")
    date_start = request.form.get("date_start", "")
    date_end = request.form.get("date_end", "")

    fields_data = build_fields_json(owner, selected_visitors, date_mode,
                                    single_date, date_start, date_end)

    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False, encoding="utf-8") as f:
        json.dump(fields_data, f, ensure_ascii=False)
        fields_path = f.name

    out_filename = f"Requerimento_Visitante_{datetime.now().strftime('%Y%m%d')}.pdf"
    out_path = os.path.join(OUTPUT_DIR, out_filename)

    result = subprocess.run(
        [sys.executable, FILL_SCRIPT, PDF_TEMPLATE, fields_path, out_path],
        capture_output=True, text=True
    )
    os.unlink(fields_path)

    if result.returncode != 0:
        flash(f"Erro ao gerar PDF: {result.stderr}", "error")
        return redirect(url_for("index"))

    return send_file(out_path, as_attachment=True, download_name=out_filename)


if __name__ == "__main__":
    print("\n🏠 Ibiti Visitantes - Iniciando...")
    print("👉 Abra no navegador: http://localhost:5000\n")
    app.run(debug=True, port=5000)
