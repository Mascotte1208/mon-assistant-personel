import re
import json
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime

# ==========================================
# CONFIG
# ==========================================
DOC_NAME = "MonAssistantData"

SHEETS = {
    "Taches":   ["Tache", "Categorie", "Statut"],
    "Agenda":   ["Date", "Heure", "Titre", "Description"],
    "Courses":  ["Article", "Quantite", "Categorie"],
    "Notes":    ["Titre", "Contenu"],
    "Recettes": ["Titre", "Ingredients", "Instructions"],
    "Budget":   ["Date", "Paye Par", "Intitule", "Montant", "Categorie"],
    "Repas":    ["Jour", "Repas", "Plat"],
    "Listes":   ["Categorie", "Element", "Notes"],
}

RAYONS = ["Fruits & Légumes", "Frais", "Boulangerie", "Supermarché", "Boissons", "Entretien", "Autre"]
CAT_TACHES = ["Maison", "Urgent", "Autre"]
CAT_BUDGET = ["Alimentation", "Maison/Bricolage", "Sorties", "Fixe/Admin"]
CAT_LISTES = ["Idées Cadeaux", "Valise / Voyage", "Maison"]
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
PERSONNES = ["Lucas", "Alex"]

st.set_page_config(
    page_title="Notre Assistant",
    page_icon="🌸",
    layout="centered",
    initial_sidebar_state="collapsed",
)

MEMOIRE_COURSES = [
    {"article": "Tomates cerises", "qte": "1 bte", "rayon": "Fruits & Légumes"},
    {"article": "Avocats", "qte": "2", "rayon": "Fruits & Légumes"},
    {"article": "Concombre", "qte": "1", "rayon": "Fruits & Légumes"},
    {"article": "Salade / Roquette", "qte": "1 sachet", "rayon": "Fruits & Légumes"},
    {"article": "Oignons", "qte": "1 sachet", "rayon": "Fruits & Légumes"},
    {"article": "Ail", "qte": "1 tête", "rayon": "Fruits & Légumes"},
    {"article": "Courgettes", "qte": "2", "rayon": "Fruits & Légumes"},
    {"article": "Citrons", "qte": "2", "rayon": "Fruits & Légumes"},
    {"article": "Œufs frais", "qte": "1 bte", "rayon": "Frais"},
    {"article": "Lait", "qte": "1 L", "rayon": "Frais"},
    {"article": "Beurre doux", "qte": "1 plq", "rayon": "Frais"},
    {"article": "Gouda / Fromage tranché", "qte": "1 pqt", "rayon": "Frais"},
    {"article": "Feta / Mozzarella", "qte": "1", "rayon": "Frais"},
    {"article": "Escalopes ou Nuggets vegan", "qte": "1 pqt", "rayon": "Frais"},
    {"article": "Saumon fumé", "qte": "1 pqt", "rayon": "Frais"},
    {"article": "Thon en boîte", "qte": "1 bte", "rayon": "Frais"},
    {"article": "Yaourts nature / grecs", "qte": "4 pots", "rayon": "Frais"},
    {"article": "Pain / Baguette", "qte": "1", "rayon": "Boulangerie"},
    {"article": "Pains panini", "qte": "2", "rayon": "Boulangerie"},
    {"article": "Pâtes / Tortellini", "qte": "1 sachet", "rayon": "Supermarché"},
    {"article": "Riz basmati", "qte": "1 pqt", "rayon": "Supermarché"},
    {"article": "Café moulu / Capsules", "qte": "1 pqt", "rayon": "Supermarché"},
    {"article": "Huile d'olive", "qte": "1 btl", "rayon": "Supermarché"},
    {"article": "Sel & Poivre / Épices", "qte": "1", "rayon": "Supermarché"},
    {"article": "Sirop de menthe", "qte": "1 btl", "rayon": "Boissons"},
    {"article": "Jus d'orange", "qte": "1 btl", "rayon": "Boissons"},
    {"article": "Papier toilette", "qte": "1 pqt", "rayon": "Entretien"},
    {"article": "Liquide vaisselle", "qte": "1 btl", "rayon": "Entretien"},
    {"article": "Éponges", "qte": "1 pqt", "rayon": "Entretien"},
    {"article": "Sacs poubelle", "qte": "1 rlx", "rayon": "Entretien"},
]

# ==========================================
# STYLE
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root{
  --rose:#ec4899; --rose-fonce:#db2777; --violet:#a855f7;
  --prune:#4a044e; --prune-clair:#831843; --bord:#fbcfe8;
}

html, body, [class*="css"], .stApp{
  font-family:'Plus Jakarta Sans', sans-serif !important;
  color:var(--prune);
  -webkit-tap-highlight-color:transparent;
}
.stApp{
  background:linear-gradient(180deg,#fff1f2 0%,#fdf2f8 45%,#faf5ff 100%) fixed !important;
}
#MainMenu, footer, header {visibility:hidden;}

.block-container{
  padding-top:1.2rem !important;
  padding-bottom:4rem !important;
  max-width:540px !important;
}
[data-testid="column"]{min-width:0 !important;}

/* --- Hero --- */
.hero{
  background:linear-gradient(135deg,#ec4899 0%,#d946ef 55%,#8b5cf6 100%);
  border-radius:28px; padding:22px 22px; color:#fff; margin-bottom:16px;
  box-shadow:0 16px 30px -12px rgba(219,39,119,.45);
  position:relative; overflow:hidden;
}
.hero::after{content:"💖"; position:absolute; right:-6px; bottom:-18px; font-size:78px; opacity:.16;}
.hero h1{font-size:23px; font-weight:800; margin:0; letter-spacing:-.4px; line-height:1.2;}
.hero p{font-size:13px; opacity:.95; margin:4px 0 0; font-weight:600;}

/* --- Boutons --- */
.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:16px !important; font-weight:700 !important; font-size:14px !important;
  padding:11px 14px !important; width:100%; border:1.5px solid var(--bord) !important;
  transition:transform .12s ease, box-shadow .12s ease;
}
.stButton>button:active, .stFormSubmitButton>button:active{transform:scale(.97);}
button[kind="secondary"], button[data-testid="stBaseButton-secondary"],
button[kind="secondaryFormSubmit"], button[data-testid="stBaseButton-secondaryFormSubmit"]{
  background:#fff !important; color:var(--rose-fonce) !important; box-shadow:0 2px 8px rgba(236,72,153,.08) !important;
}
button[kind="primary"], button[data-testid="stBaseButton-primary"],
button[kind="primaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"]{
  background:linear-gradient(135deg,#ec4899 0%,#db2777 100%) !important;
  color:#fff !important; border:none !important;
  box-shadow:0 8px 18px -6px rgba(219,39,119,.55) !important;
}
button:focus-visible{outline:3px solid #f9a8d4 !important; outline-offset:2px;}

/* --- Cartes --- */
.card{
  background:#fff; border-radius:20px; padding:14px 18px; border:1.5px solid var(--bord);
  box-shadow:0 8px 18px rgba(236,72,153,.07); margin-bottom:10px;
  display:flex; align-items:center; justify-content:space-between; gap:10px;
}
.card .k{font-size:13px; font-weight:700; color:var(--rose-fonce);}
.card .v{font-size:19px; font-weight:800; color:#701a75; text-align:right;}
.card .v.small{font-size:14px; font-weight:700; color:var(--rose-fonce);}

.note-box{
  background:linear-gradient(135deg,#fdf4ff 0%,#fae8ff 100%);
  border:2px dashed #e879f9; border-radius:20px; padding:16px 18px; margin-bottom:14px;
}
.note-box .t{font-size:13px; font-weight:700; color:#9333ea; margin-bottom:4px;}
.note-box .c{font-size:15px; color:#581c87; font-weight:600;}

.section{font-weight:800; font-size:15px; color:var(--prune-clair); margin:18px 0 8px;}
.line{font-size:15px; font-weight:600; color:var(--prune); padding:9px 0;}
.line.done{color:#a3a3a3; text-decoration:line-through;}
.line .q{font-weight:600; color:#a21caf; font-size:13px;}
.tag{
  display:inline-block; padding:3px 10px; border-radius:12px; font-size:11px;
  font-weight:700; background:#fce7f3; color:var(--rose-fonce); margin-left:6px; vertical-align:middle;
}
.rayon{
  font-size:12px; font-weight:800; color:#a21caf; background:#fae8ff;
  display:inline-block; padding:5px 12px; border-radius:12px; margin:14px 0 4px;
}
.empty{
  text-align:center; padding:22px 16px; border-radius:20px; background:#fff;
  border:1.5px dashed var(--bord); color:#9d174d; font-weight:600; font-size:14px;
}

/* --- Champs --- */
.stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input, .stTimeInput input{
  color:var(--prune) !important; background:#fff !important; -webkit-text-fill-color:var(--prune) !important;
  border-radius:16px !important; border:1.5px solid #f9a8d4 !important;
  padding:11px 15px !important; font-size:15px !important;
}
[data-baseweb="select"]>div{
  border-radius:16px !important; border:1.5px solid #f9a8d4 !important; background:#fff !important;
}
label p{font-weight:700 !important; font-size:13px !important; color:var(--prune-clair) !important;}

/* --- Onglets --- */
.stTabs [data-baseweb="tab-list"]{
  gap:6px; background:rgba(255,255,255,.75); padding:6px; border-radius:18px;
  border:1.5px solid var(--bord);
}
.stTabs [data-baseweb="tab"]{
  border-radius:13px; padding:7px 12px; font-weight:700; font-size:13px; color:var(--rose-fonce);
}
.stTabs [aria-selected="true"]{
  background:linear-gradient(135deg,#ec4899,#db2777); color:#fff !important;
}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{display:none;}

/* --- Divers --- */
.stProgress > div > div > div > div{background-image:linear-gradient(90deg,#f472b6,#a855f7) !important;}
[data-testid="stExpander"]{
  border-radius:18px !important; border:1.5px solid var(--bord) !important;
  background:#fff !important; overflow:hidden;
}
hr{margin:14px 0 !important; border-color:#fbcfe8 !important;}
[data-testid="stMetricValue"]{color:#701a75; font-weight:800;}
</style>
""", unsafe_allow_html=True)

# ==========================================
# ÉTAT & RÉINITIALISATION DES CHAMPS
# ==========================================
for key, val in [("creds_json", None), ("page", "Accueil"), ("_reset", {})]:
    if key not in st.session_state:
        st.session_state[key] = val

# Vide les champs demandés au tour précédent (avant création des widgets)
for k, v in st.session_state["_reset"].items():
    st.session_state[k] = v
st.session_state["_reset"] = {}


def reset_after(**fields):
    st.session_state["_reset"] = fields


# Credentials via st.secrets (évite de réimporter le JSON à chaque visite)
if not st.session_state["creds_json"]:
    try:
        if "gcp_service_account" in st.secrets:
            st.session_state["creds_json"] = json.dumps(dict(st.secrets["gcp_service_account"]))
    except Exception:
        pass


# ==========================================
# COUCHE DONNÉES
# ==========================================
@st.cache_resource(show_spinner=False)
def get_client(json_str):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(json.loads(json_str), scopes=scope)
    return gspread.authorize(creds)


@st.cache_resource(show_spinner=False)
def get_doc(json_str):
    client = get_client(json_str)
    try:
        doc = client.open(DOC_NAME)
    except gspread.SpreadsheetNotFound:
        doc = client.create(DOC_NAME)
    titres = {ws.title: ws for ws in doc.worksheets()}
    for name, headers in SHEETS.items():
        if name not in titres:
            ws = doc.add_worksheet(title=name, rows=1000, cols=max(8, len(headers)))
            ws.append_row(headers)
    if "Sheet1" in titres and len(titres) > 1:
        try:
            doc.del_worksheet(titres["Sheet1"])
        except Exception:
            pass
    return doc


@st.cache_resource(show_spinner=False)
def get_ws(json_str, sheet):
    return get_doc(json_str).worksheet(sheet)


@st.cache_data(ttl=300, show_spinner=False)
def fetch_all(json_str):
    """Un seul appel réseau pour les 8 feuilles."""
    doc = get_doc(json_str)
    data = {}
    try:
        res = doc.values_batch_get([f"'{n}'!A1:Z2000" for n in SHEETS])
        for name, vr in zip(SHEETS.keys(), res.get("valueRanges", [])):
            data[name] = vr.get("values", []) or []
    except Exception:
        for name in SHEETS:
            try:
                data[name] = doc.worksheet(name).get_all_values()
            except Exception:
                data[name] = []
    for name, headers in SHEETS.items():
        if not data.get(name):
            data[name] = [headers]
    return data


def db():
    if "db" not in st.session_state:
        creds = st.session_state["creds_json"]
        if creds:
            with st.spinner("Chargement de vos données…"):
                st.session_state["db"] = fetch_all(creds)
        else:
            st.session_state["db"] = {n: [h] for n, h in SHEETS.items()}
    return st.session_state["db"]


def rows(sheet):
    """Lignes de données (sans l'en-tête), avec leur index réel dans la feuille."""
    raw = db().get(sheet, [])
    return [(i + 1, r) for i, r in enumerate(raw[1:])]


def pad(row, n):
    return (list(row) + [""] * n)[:n]


def _push(fn):
    creds = st.session_state.get("creds_json")
    if not creds:
        return
    try:
        fn()
    except Exception:
        st.toast("Modification enregistrée localement, synchronisation Google en échec.", icon="⚠️")


def add_row(sheet, row):
    db()[sheet].append(row)
    creds = st.session_state["creds_json"]
    _push(lambda: get_ws(creds, sheet).append_row(row, value_input_option="USER_ENTERED"))


def delete_row(sheet, idx):
    data = db()[sheet]
    if 0 < idx < len(data):
        data.pop(idx)
        creds = st.session_state["creds_json"]
        _push(lambda: get_ws(creds, sheet).delete_rows(idx + 1))


def set_cell(sheet, idx, col, value):
    data = db()[sheet]
    if 0 < idx < len(data):
        row = pad(data[idx], max(col, len(data[idx])))
        row[col - 1] = value
        data[idx] = row
        creds = st.session_state["creds_json"]
        _push(lambda: get_ws(creds, sheet).update_cell(idx + 1, col, value))


def clear_sheet(sheet):
    db()[sheet] = [SHEETS[sheet]]
    creds = st.session_state["creds_json"]
    _push(lambda: get_ws(creds, sheet).batch_clear(["A2:Z2000"]))


def merge_qte(a, b):
    """1 bte + 2 bte -> 3 bte ; sinon concaténation lisible."""
    pat = r"^\s*(\d+(?:[.,]\d+)?)\s*(.*)$"
    ma, mb = re.match(pat, str(a or "")), re.match(pat, str(b or ""))
    if ma and mb and ma.group(2).strip().lower() == mb.group(2).strip().lower():
        total = float(ma.group(1).replace(",", ".")) + float(mb.group(1).replace(",", "."))
        num = int(total) if total.is_integer() else round(total, 2)
        return f"{num} {ma.group(2).strip()}".strip()
    return f"{a} + {b}"


def add_course(article, qte, rayon):
    """Fusionne avec l'article existant s'il est déjà dans le panier."""
    nom = article.strip().lower()
    for idx, r in rows("Courses"):
        if pad(r, 3)[0].strip().lower() == nom:
            set_cell("Courses", idx, 2, merge_qte(pad(r, 3)[1] or "1", qte))
            return
    add_row("Courses", [article.strip(), qte, rayon])


def to_float(v):
    try:
        return float(str(v).replace(",", ".").replace("€", "").strip())
    except (ValueError, AttributeError):
        return 0.0


# ==========================================
# COMPOSANTS UI
# ==========================================
def pills(key, options, default=None, cols=3, prefix=""):
    """Sélecteur de catégorie en boutons. Renvoie l'option active."""
    if key not in st.session_state or st.session_state[key] not in options:
        st.session_state[key] = default if default in options else options[0]
    for start in range(0, len(options), cols):
        ligne = options[start:start + cols]
        columns = st.columns(cols)
        for c, opt in zip(columns, ligne):
            with c:
                actif = st.session_state[key] == opt
                if st.button(f"{prefix}{opt}", key=f"pill_{key}_{opt}",
                             type="primary" if actif else "secondary"):
                    st.session_state[key] = opt
                    st.rerun()
    return st.session_state[key]


def titre(txt):
    st.markdown(f"<div class='section'>{txt}</div>", unsafe_allow_html=True)


def vide(txt):
    st.markdown(f"<div class='empty'>{txt}</div>", unsafe_allow_html=True)


def ligne(html, done=False):
    st.markdown(f"<div class='line{' done' if done else ''}'>{html}</div>", unsafe_allow_html=True)


# ==========================================
# EN-TÊTE
# ==========================================
st.markdown("""
<div class="hero">
  <h1>Bonjour Lucas & Alex ✨</h1>
  <p>Notre petit espace cosy du quotidien 🌸</p>
</div>
""", unsafe_allow_html=True)

# ==========================================
# CONNEXION
# ==========================================
if not st.session_state["creds_json"]:
    st.markdown("<div class='section'>Connexion à Google Sheets</div>", unsafe_allow_html=True)
    st.caption("Déposez le fichier JSON du compte de service. Astuce : placez-le dans "
               "`.streamlit/secrets.toml` sous `[gcp_service_account]` pour ne plus jamais le redemander.")
    fichier = st.file_uploader("Fichier de configuration", type=["json"], label_visibility="collapsed")
    if fichier is not None:
        raw = fichier.read().decode("utf-8")
        try:
            with st.spinner("Préparation du classeur…"):
                st.session_state["creds_json"] = raw
                get_doc(raw)
            st.session_state.pop("db", None)
            st.toast("Connexion réussie 💖", icon="✨")
            st.rerun()
        except Exception as e:
            st.session_state["creds_json"] = None
            st.error(f"Connexion impossible : {e}")
    st.stop()

# ==========================================
# NAVIGATION
# ==========================================
PAGES = ["🏠 Accueil", "📋 Quotidien", "📊 Budget", "🐾 Maison"]
n1, n2 = st.columns(2)
for i, p in enumerate(PAGES):
    with (n1 if i % 2 == 0 else n2):
        if st.button(p, key=f"nav_{p}", type="primary" if st.session_state["page"] == p else "secondary"):
            st.session_state["page"] = p
            st.rerun()

page = st.session_state["page"]
st.divider()

# ==========================================
# 1. ACCUEIL
# ==========================================
if page == "🏠 Accueil":
    taches = rows("Taches")
    courses = rows("Courses")
    budget = rows("Budget")
    notes = rows("Notes")

    faites = len([r for _, r in taches if pad(r, 3)[2] == "Fait"])
    total_l = sum(to_float(pad(r, 5)[3]) for _, r in budget if pad(r, 5)[1] == "Lucas")
    total_a = sum(to_float(pad(r, 5)[3]) for _, r in budget if pad(r, 5)[1] == "Alex")
    diff = (total_l - total_a) / 2
    if diff > 0.005:
        bilan = f"Alex doit {diff:.2f} € à Lucas"
    elif diff < -0.005:
        bilan = f"Lucas doit {abs(diff):.2f} € à Alex"
    else:
        bilan = "Comptes équilibrés 💖"

    epingle = next((pad(r, 2)[1] for _, r in notes if "important" in pad(r, 2)[0].lower()), None)
    if not epingle:
        epingle = pad(notes[-1][1], 2)[1] if notes else "Ajoutez une note nommée « Important » pour l'afficher ici."
    st.markdown(f"""
    <div class="note-box">
      <div class="t">✨ Message épinglé</div>
      <div class="c">{epingle}</div>
    </div>""", unsafe_allow_html=True)

    st.markdown(f"""
    <div class="card"><span class="k">🌸 Tâches accomplies</span><span class="v">{faites} / {len(taches)}</span></div>
    <div class="card"><span class="k">🛒 Panier de courses</span><span class="v">{len(courses)} articles</span></div>
    <div class="card"><span class="k">💶 Équilibre du budget</span><span class="v small">{bilan}</span></div>
    """, unsafe_allow_html=True)

    titre("⚡ Ajout rapide")
    cible = pills("quick_cible", ["Tâche", "Course", "Note"], cols=3)
    q_txt = st.text_input("Quoi ?", key="quick_txt", placeholder=f"Nouvelle {cible.lower()}…",
                          label_visibility="collapsed")
    if st.button("Ajouter", key="quick_add", type="primary") and q_txt.strip():
        if cible == "Tâche":
            add_row("Taches", [q_txt.strip(), "Autre", "À faire"])
        elif cible == "Course":
            add_course(q_txt.strip(), "1", "Autre")
        else:
            add_row("Notes", [q_txt.strip(), ""])
        reset_after(quick_txt="")
        st.toast(f"{cible} ajoutée 💖", icon="✅")
        st.rerun()

    titre("✨ Tâches en cours")
    actives = [(i, r) for i, r in taches if pad(r, 3)[2] != "Fait"]
    if actives:
        for idx, r in actives[:5]:
            nom, cat, _ = pad(r, 3)
            c1, c2 = st.columns([4, 1])
            with c1:
                ligne(f"{nom}<span class='tag'>{cat or 'Général'}</span>")
            with c2:
                if st.button("✔️", key=f"acc_ok_{idx}"):
                    set_cell("Taches", idx, 3, "Fait")
                    st.rerun()
    else:
        vide("🎉 Tout est fait, profitez de votre soirée.")

    st.divider()
    d1, d2 = st.columns(2)
    with d1:
        if st.button("🔄 Actualiser"):
            st.cache_data.clear()
            st.session_state.pop("db", None)
            st.rerun()
    with d2:
        if st.button("🚪 Déconnexion"):
            st.cache_data.clear()
            st.cache_resource.clear()
            for k in ["creds_json", "db"]:
                st.session_state.pop(k, None)
            st.rerun()

# ==========================================
# 2. QUOTIDIEN
# ==========================================
elif page == "📋 Quotidien":
    t1, t2, t3, t4 = st.tabs(["✅ Tâches", "🛒 Courses", "📅 Agenda", "🍽️ Repas"])

    # ---------- TÂCHES ----------
    with t1:
        taches = rows("Taches")
        if taches:
            faites = len([r for _, r in taches if pad(r, 3)[2] == "Fait"])
            st.progress(faites / len(taches), text=f"{faites} sur {len(taches)} terminées")

        filtre = pills("f_taches", ["Toutes"] + CAT_TACHES, cols=4)
        visibles = [(i, r) for i, r in taches if filtre == "Toutes" or pad(r, 3)[1] == filtre]

        if visibles:
            for idx, r in visibles:
                nom, cat, statut = pad(r, 3)
                fait = statut == "Fait"
                c1, c2, c3 = st.columns([4, 1, 1])
                with c1:
                    ligne(f"{nom}<span class='tag'>{cat or 'Général'}</span>", done=fait)
                with c2:
                    if st.button("↩️" if fait else "✔️", key=f"tk_{idx}"):
                        set_cell("Taches", idx, 3, "À faire" if fait else "Fait")
                        st.rerun()
                with c3:
                    if st.button("🗑️", key=f"td_{idx}"):
                        delete_row("Taches", idx)
                        st.rerun()
        else:
            vide("Aucune tâche dans cette catégorie.")

        st.divider()
        titre("Nouvelle tâche")
        n_cat = pills("new_tache_cat", CAT_TACHES, cols=3)
        n_txt = st.text_input("Intitulé", key="new_tache_txt", placeholder="Sortir les poubelles…")
        if st.button("Ajouter la tâche", type="primary") and n_txt.strip():
            add_row("Taches", [n_txt.strip(), n_cat, "À faire"])
            reset_after(new_tache_txt="")
            st.rerun()

    # ---------- COURSES ----------
    with t2:
        courses = rows("Courses")

        titre("💖 Nos articles habituels")
        rayon_memo = pills("memo_rayon", RAYONS[:-1], cols=2)
        deja = {pad(r, 3)[0].strip().lower() for _, r in courses}
        propositions = [m for m in MEMOIRE_COURSES if m["rayon"] == rayon_memo]
        if propositions:
            mc1, mc2 = st.columns(2)
            for i, m in enumerate(propositions):
                with (mc1 if i % 2 == 0 else mc2):
                    dedans = m["article"].strip().lower() in deja
                    if st.button(("✅ " if dedans else "＋ ") + m["article"], key=f"memo_{m['article']}"):
                        add_course(m["article"], m["qte"], m["rayon"])
                        st.toast(f"{m['article']} au panier", icon="🛒")
                        st.rerun()
        else:
            vide("Rien de mémorisé pour ce rayon.")

        st.divider()
        titre(f"🛒 Panier ({len(courses)})")
        if courses:
            for rayon in RAYONS:
                du_rayon = [(i, r) for i, r in courses if (pad(r, 3)[2] or "Autre") == rayon]
                if not du_rayon:
                    continue
                st.markdown(f"<div class='rayon'>{rayon}</div>", unsafe_allow_html=True)
                for idx, r in du_rayon:
                    art, qte, _ = pad(r, 3)
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        ligne(f"{art} <span class='q'>· {qte}</span>")
                    with c2:
                        if st.button("✔️", key=f"co_{idx}"):
                            delete_row("Courses", idx)
                            st.rerun()
            st.write("")
            if st.session_state.get("confirm_vider"):
                cc1, cc2 = st.columns(2)
                with cc1:
                    if st.button("Oui, tout vider", type="primary"):
                        clear_sheet("Courses")
                        st.session_state["confirm_vider"] = False
                        st.rerun()
                with cc2:
                    if st.button("Annuler"):
                        st.session_state["confirm_vider"] = False
                        st.rerun()
            elif st.button("🧹 Vider le panier"):
                st.session_state["confirm_vider"] = True
                st.rerun()
        else:
            vide("Le panier est vide. Piochez dans les habituels ci-dessus.")

        st.divider()
        titre("Ajouter autre chose")
        c_rayon = pills("new_course_rayon", RAYONS, cols=2)
        ca, cb = st.columns([3, 1])
        with ca:
            c_art = st.text_input("Article", key="new_course_art", placeholder="Fraises…")
        with cb:
            c_qte = st.text_input("Qté", key="new_course_qte", value="1")
        if st.button("Ajouter au panier", type="primary") and c_art.strip():
            add_course(c_art, c_qte or "1", c_rayon)
            reset_after(new_course_art="", new_course_qte="1")
            st.rerun()

    # ---------- AGENDA ----------
    with t3:
        agenda = rows("Agenda")

        def cle_date(item):
            try:
                return (datetime.strptime(pad(item[1], 4)[0], "%Y-%m-%d").date(), pad(item[1], 4)[1])
            except ValueError:
                return (datetime.max.date(), "")

        for idx, r in sorted(agenda, key=cle_date):
            d, h, ti, desc = pad(r, 4)
            try:
                d_aff = datetime.strptime(d, "%Y-%m-%d").strftime("%d/%m/%Y")
            except ValueError:
                d_aff = d
            with st.expander(f"🗓️ {d_aff}{f' · {h}' if h else ''} — {ti}"):
                if desc:
                    st.write(desc)
                if st.button("🗑️ Supprimer", key=f"ag_{idx}"):
                    delete_row("Agenda", idx)
                    st.rerun()
        if not agenda:
            vide("Aucun événement prévu.")

        st.divider()
        with st.form("form_agenda", clear_on_submit=True):
            titre("Nouvel événement")
            fa, fb = st.columns(2)
            with fa:
                e_date = st.date_input("Date", value=datetime.today())
            with fb:
                e_heure = st.time_input("Heure", value=datetime.now().time())
            e_titre = st.text_input("Titre")
            e_desc = st.text_area("Détails", height=80)
            if st.form_submit_button("Enregistrer", type="primary") and e_titre.strip():
                add_row("Agenda", [str(e_date), e_heure.strftime("%H:%M"), e_titre.strip(), e_desc])
                st.rerun()

    # ---------- REPAS ----------
    with t4:
        repas = rows("Repas")
        jour = pills("repas_jour", JOURS, cols=4)
        du_jour = [(i, r) for i, r in repas if pad(r, 3)[0] == jour]
        if du_jour:
            for idx, r in du_jour:
                _, typ, plat = pad(r, 3)
                c1, c2 = st.columns([4, 1])
                with c1:
                    ligne(f"<span class='tag'>{typ}</span> {plat}")
                with c2:
                    if st.button("🗑️", key=f"rp_{idx}"):
                        delete_row("Repas", idx)
                        st.rerun()
        else:
            vide(f"Rien de prévu pour {jour.lower()}.")

        st.divider()
        titre(f"Ajouter un repas · {jour}")
        r_type = pills("repas_type", ["Midi", "Soir"], cols=2)
        r_plat = st.text_input("Plat", key="new_repas_plat", placeholder="Tortellini crème & épinards…")
        if st.button("Ajouter au planning", type="primary") and r_plat.strip():
            add_row("Repas", [jour, r_type, r_plat.strip()])
            reset_after(new_repas_plat="")
            st.rerun()

# ==========================================
# 3. BUDGET
# ==========================================
elif page == "📊 Budget":
    budget = rows("Budget")

    if budget:
        df = pd.DataFrame([{
            "Date": pad(r, 5)[0], "Payeur": pad(r, 5)[1], "Intitulé": pad(r, 5)[2],
            "Montant": to_float(pad(r, 5)[3]), "Catégorie": pad(r, 5)[4] or "Alimentation",
        } for _, r in budget])

        total_l = df[df["Payeur"] == "Lucas"]["Montant"].sum()
        total_a = df[df["Payeur"] == "Alex"]["Montant"].sum()
        diff = (total_l - total_a) / 2

        m1, m2 = st.columns(2)
        m1.metric("Payé par Lucas", f"{total_l:.2f} €")
        m2.metric("Payé par Alex", f"{total_a:.2f} €")

        if diff > 0.005:
            st.success(f"👉 Alex doit **{diff:.2f} €** à Lucas")
        elif diff < -0.005:
            st.success(f"👉 Lucas doit **{abs(diff):.2f} €** à Alex")
        else:
            st.info("💖 Comptes parfaitement équilibrés")

        titre("Répartition par catégorie")
        st.bar_chart(df.groupby("Catégorie")["Montant"].sum(), color="#ec4899", height=200)

        titre("Dépenses")
        filtre_b = pills("f_budget", ["Toutes"] + CAT_BUDGET, cols=3)
        visibles = [(i, r) for i, r in budget
                    if filtre_b == "Toutes" or (pad(r, 5)[4] or "Alimentation") == filtre_b]
        for idx, r in reversed(visibles):
            d, pyr, lbl, mnt, cat = pad(r, 5)
            c1, c2 = st.columns([4, 1])
            with c1:
                ligne(f"{lbl} <span class='tag'>{cat or 'Alimentation'}</span>"
                      f"<br><span class='q'>{to_float(mnt):.2f} € · {pyr} · {d}</span>")
            with c2:
                if st.button("🗑️", key=f"bu_{idx}"):
                    delete_row("Budget", idx)
                    st.rerun()
        if not visibles:
            vide("Aucune dépense dans cette catégorie.")
    else:
        vide("Aucune dépense enregistrée pour l'instant.")

    st.divider()
    titre("Nouvelle dépense")
    b_payeur = pills("new_bud_payeur", PERSONNES, cols=2)
    b_cat = pills("new_bud_cat", CAT_BUDGET, cols=2)
    b_label = st.text_input("Intitulé", key="new_bud_label", placeholder="Courses Delhaize…")
    bc1, bc2 = st.columns(2)
    with bc1:
        b_montant = st.number_input("Montant (€)", min_value=0.0, step=0.5, key="new_bud_montant")
    with bc2:
        b_date = st.date_input("Date", value=datetime.today(), key="new_bud_date")
    if st.button("Enregistrer la dépense", type="primary") and b_label.strip() and b_montant > 0:
        add_row("Budget", [str(b_date), b_payeur, b_label.strip(), f"{b_montant:.2f}", b_cat])
        reset_after(new_bud_label="", new_bud_montant=0.0)
        st.rerun()

# ==========================================
# 4. MAISON & LOISIRS
# ==========================================
elif page == "🐾 Maison":
    t1, t2, t3 = st.tabs(["🍲 Recettes", "📝 Notes", "🧳 Listes"])

    with t1:
        recettes = rows("Recettes")
        recherche = st.text_input("Rechercher une recette", key="rec_search",
                                  placeholder="🔎 Chercher…", label_visibility="collapsed")
        trouvees = [(i, r) for i, r in recettes
                    if recherche.lower() in " ".join(pad(r, 3)).lower()]
        for idx, r in trouvees:
            t, ing, inst = pad(r, 3)
            with st.expander(f"🍲 {t}"):
                if ing:
                    st.markdown(f"**Ingrédients**\n\n{ing}")
                if inst:
                    st.markdown(f"**Préparation**\n\n{inst}")
                if st.button("🗑️ Supprimer", key=f"re_{idx}"):
                    delete_row("Recettes", idx)
                    st.rerun()
        if not trouvees:
            vide("Aucune recette pour l'instant.")

        st.divider()
        with st.form("form_recette", clear_on_submit=True):
            titre("Nouvelle recette")
            r_titre = st.text_input("Nom")
            r_ing = st.text_area("Ingrédients (un par ligne)", height=90)
            r_inst = st.text_area("Préparation", height=110)
            if st.form_submit_button("Enregistrer la recette", type="primary") and r_titre.strip():
                add_row("Recettes", [r_titre.strip(), r_ing, r_inst])
                st.rerun()

    with t2:
        notes = rows("Notes")
        for idx, r in reversed(notes):
            t, c = pad(r, 2)
            epingle = "important" in t.lower()
            with st.expander(f"{'📌' if epingle else '📝'} {t}"):
                st.write(c or "_Vide_")
                if st.button("🗑️ Supprimer", key=f"no_{idx}"):
                    delete_row("Notes", idx)
                    st.rerun()
        if not notes:
            vide("Aucune note partagée.")

        st.divider()
        with st.form("form_note", clear_on_submit=True):
            titre("Nouvelle note")
            st.caption("Un titre contenant « Important » épingle la note sur l'accueil.")
            n_titre = st.text_input("Titre")
            n_contenu = st.text_area("Contenu", height=110)
            if st.form_submit_button("Enregistrer la note", type="primary") and n_titre.strip():
                add_row("Notes", [n_titre.strip(), n_contenu])
                st.rerun()

    with t3:
        listes = rows("Listes")
        cat_l = pills("f_listes", CAT_LISTES, cols=3)
        visibles = [(i, r) for i, r in listes if pad(r, 3)[0] == cat_l]
        if visibles:
            for idx, r in visibles:
                _, elm, nts = pad(r, 3)
                c1, c2 = st.columns([4, 1])
                with c1:
                    ligne(f"{elm}" + (f"<br><span class='q'>{nts}</span>" if nts else ""))
                with c2:
                    if st.button("🗑️", key=f"li_{idx}"):
                        delete_row("Listes", idx)
                        st.rerun()
        else:
            vide(f"Rien dans « {cat_l} » pour le moment.")

        st.divider()
        titre(f"Ajouter à « {cat_l} »")
        l_elem = st.text_input("Élément", key="new_liste_elem")
        l_notes = st.text_input("Note (facultatif)", key="new_liste_notes")
        if st.button("Ajouter", type="primary") and l_elem.strip():
            add_row("Listes", [cat_l, l_elem.strip(), l_notes])
            reset_after(new_liste_elem="", new_liste_notes="")
            st.rerun()
