"""
Notre Assistant — l'appli partagée du quotidien de Lucas & Alex.

Streamlit + Google Sheets, un seul fichier organisé en sections :
  1. Configuration      5. Composants d'interface
  2. Style              6. Connexion
  3. État de session    7. Navigation
  4. Couche données     8. Pages
"""

import io
import re
import json
import calendar
import unicodedata
import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
from datetime import datetime, date, timedelta

# ==========================================================
# 1. CONFIGURATION
# ==========================================================
VERSION = "2.5"
DOC_NAME = "MonAssistantData"

SHEETS = {
    "Taches":   ["Tache", "Statut"],
    "Agenda":   ["Date", "Heure", "Titre", "Description"],
    "Courses":  ["Article", "Quantite", "Categorie"],
    "Notes":    ["Titre", "Contenu", "Epingle"],
    "Recettes": ["Titre", "Ingredients", "Instructions"],
    "Budget":   ["Date", "Paye Par", "Intitule", "Montant", "Categorie"],
    "Repas":    ["Jour", "Repas", "Plat"],
    "Listes":   ["Categorie", "Element", "Notes"],
}

RAYONS = ["Fruits & Légumes", "Frais", "Boulangerie", "Supermarché", "Boissons", "Entretien", "Autre"]
RAYON_COULEURS = {
    "Fruits & Légumes": "#16a34a",
    "Frais": "#0891b2",
    "Boulangerie": "#d97706",
    "Supermarché": "#7c3aed",
    "Boissons": "#2563eb",
    "Entretien": "#db2777",
    "Autre": "#6b7280",
}
CAT_BUDGET = ["Alimentation", "Maison/Bricolage", "Sorties", "Fixe/Admin"]
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_COURT = ["L", "M", "M", "J", "V", "S", "D"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
PERSONNES = ["Lucas", "Alex"]

ONGLETS_M = ["🛒 Courses", "🍲 Recettes", "📝 Notes"]

PAGES = {
    "accueil": "🏠 Accueil",
    "budget": "📊 Budget",
    "maison": "🐾 Maison",
}

st.set_page_config(page_title="Notre Assistant", page_icon="🌸",
                   layout="centered", initial_sidebar_state="collapsed")

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

INDICES_RAYON = [
    ("Fruits & Légumes", ["tomate", "salade", "roquette", "pomme", "banane", "carotte", "oignon",
                         "citron", "courgette", "avocat", "concombre", "ail", "poivron", "champignon",
                         "épinard", "basilic", "persil", "fraise", "brocoli", "patate", "pomme de terre"]),
    ("Frais", ["lait", "yaourt", "fromage", "beurre", "œuf", "oeuf", "crème", "creme", "jambon",
               "poulet", "saumon", "mozzarella", "feta", "parmesan", "thon", "escalope", "tofu"]),
    ("Boulangerie", ["pain", "baguette", "panini", "brioche", "wrap", "tortilla"]),
    ("Boissons", ["jus", "eau", "soda", "sirop", "vin", "bière", "biere", "limonade"]),
    ("Entretien", ["papier", "lessive", "éponge", "eponge", "savon", "poubelle", "vaisselle"]),
    ("Supermarché", ["pâtes", "pates", "riz", "farine", "sucre", "huile", "café", "cafe", "sel",
                     "poivre", "épice", "epice", "conserve", "sauce", "bouillon", "lentille", "semoule"]),
]

UNITES = ["g", "kg", "ml", "cl", "l", "cs", "cc", "c.s", "c.c", "pincée", "pincee", "tranche",
         "tranches", "gousse", "gousses", "boîte", "boite", "sachet", "sachets", "pot", "pots",
         "botte", "brique", "briques", "paquet", "paquets", "bouquet", "brin", "brins", "verre",
         "verres", "cuillère", "cuillere", "cuillères", "cuilleres", "filet", "barquette",
         "rouleau", "bocal", "boule", "boules", "part", "parts", "portion", "portions"]

# ==========================================================
# 2. STYLE (Design épuré, aéré & cartes flottantes)
# ==========================================================
def slug(texte):
    plat = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plat.lower()).strip("-")


CSS_CATEGORIES = "".join(
    f".st-key-grp-{slug(rayon)}{{border-left:3px solid {couleur};"
    f"padding-left:14px; margin:16px 0 4px;}}"
    f".st-key-grp-{slug(rayon)} .rayon{{color:{couleur};}}"
    for rayon, couleur in RAYON_COULEURS.items()
)

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

:root{
  --rose:#ec4899; --rose-fonce:#db2777; --violet:#a855f7;
  --prune:#4a044e; --prune-clair:#831843; --bord:#fbcfe8;
}

html, body, [class*="css"], .stApp{
  font-family:'Plus Jakarta Sans', sans-serif !important;
  color:var(--prune); -webkit-tap-highlight-color:transparent;
}
.stApp{background:linear-gradient(180deg,#fff1f2 0%,#fdf2f8 45%,#faf5ff 100%) fixed !important;}
#MainMenu, footer, header{visibility:hidden;}
.block-container{padding-top:1.2rem !important; padding-bottom:5rem !important; max-width:540px !important;}

[data-testid="stHorizontalBlock"]{flex-wrap:nowrap !important; gap:8px !important;}
[data-testid="stHorizontalBlock"] > div{min-width:0 !important;}

.topbar{
  display:flex; justify-content:space-between; align-items:center; gap:10px;
  background:linear-gradient(135deg,#ec4899 0%,#a855f7 100%); color:#fff;
  border-radius:18px; padding:11px 18px; margin-bottom:14px;
  font-weight:800; font-size:14px; letter-spacing:-.2px;
  box-shadow:0 10px 22px -8px rgba(219,39,119,.5);
}
.topbar .d{font-weight:700; font-size:12.5px; opacity:.94; white-space:nowrap;}

.st-key-navrow{margin-bottom:8px;}
.st-key-navrow [data-testid="stHorizontalBlock"]{gap:6px !important;}
.st-key-navrow button{font-size:12.5px !important; padding:10px 4px !important; border-radius:16px !important;}
.st-key-navrow button p{font-size:12.5px !important; font-weight:800 !important;}

.bloc-head{
  display:flex; justify-content:space-between; align-items:center; gap:8px;
  padding:2px 0 8px; font-size:15.5px; font-weight:800; color:var(--prune-clair);
}
.bloc-head .n{background:#fce7f3; color:var(--rose-fonce); border-radius:14px;
  padding:3px 12px; font-size:12px; font-weight:800;}

.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:16px !important; font-weight:700 !important; font-size:14px !important;
  padding:12px 14px !important; width:100%; border:1.5px solid var(--bord) !important;
  transition:transform .12s ease;
}
.stButton>button:active, .stFormSubmitButton>button:active{transform:scale(.97);}
button[kind="secondary"], button[data-testid="stBaseButton-secondary"],
button[kind="secondaryFormSubmit"], button[data-testid="stBaseButton-secondaryFormSubmit"],
.stDownloadButton>button{
  background:#fff !important; color:var(--rose-fonce) !important;
  box-shadow:0 3px 10px rgba(236,72,153,.06) !important;
}
button[kind="primary"], button[data-testid="stBaseButton-primary"],
button[kind="primaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"]{
  background:linear-gradient(135deg,#ec4899 0%,#db2777 100%) !important;
  color:#fff !important; border:none !important;
  box-shadow:0 8px 18px -6px rgba(219,39,119,.55) !important;
}
button:focus-visible{outline:3px solid #f9a8d4 !important; outline-offset:2px;}

/* Cartes flottantes aux contours doux */
[data-testid="stVerticalBlockBorderWrapper"]{
  background:#ffffff; border:1.5px solid #fbcfe8 !important; border-radius:24px !important;
  padding:12px 18px 10px !important; box-shadow:0 12px 28px rgba(236,72,153,.07); margin-bottom:14px;
}

.jour-titre{font-size:13.5px; font-weight:800; color:#a21caf; padding:8px 0 4px;}
.section{font-weight:800; font-size:15.5px; color:var(--prune-clair); margin:18px 0 8px;}

/* Lignes aérées et confortables pour le pouce */
.line{font-size:15px; font-weight:600; color:var(--prune); padding:10px 0;}
.line.done{color:#a3a3a3; text-decoration:line-through;}
.line .q{font-weight:600; color:#a21caf; font-size:13px;}

.tag{display:inline-block; padding:3px 10px; border-radius:12px; font-size:11px; font-weight:700;
     background:#fce7f3; color:var(--rose-fonce); margin-left:6px; vertical-align:middle;}
.rayon{font-size:12.5px; font-weight:800; color:#a21caf; background:#fae8ff;
       display:inline-block; padding:5px 12px; border-radius:12px; margin:14px 0 4px;}
.empty{text-align:center; padding:22px 16px; border-radius:20px; background:#fff;
       border:1.5px dashed var(--bord); color:#9d174d; font-weight:600; font-size:14px;}
.today-none{font-size:14px; color:#9d174d; font-weight:600; opacity:.75; padding:8px 0;}

.note-box{background:linear-gradient(135deg,#fdf4ff 0%,#fae8ff 100%); border:2px dashed #e879f9;
          border-radius:22px; padding:15px 20px; margin-bottom:14px;}
.note-box .t{font-size:13.5px; font-weight:700; color:#9333ea; margin-bottom:5px;}
.note-box .c{font-size:15px; color:#581c87; font-weight:600;}

.solde{border-radius:20px; padding:15px 18px; margin:12px 0; font-weight:700; font-size:14.5px;
       background:linear-gradient(135deg,#fdf4ff,#fae8ff); border:1.5px solid #f0abfc; color:#701a75;
       display:flex; justify-content:space-between; align-items:center; gap:10px;
       box-shadow:0 8px 20px rgba(168,85,247,.08);}
.solde .m{font-size:17.5px; font-weight:800; color:var(--rose-fonce); white-space:nowrap;}

.bandeau{border-radius:16px; padding:11px 15px; font-size:13.5px; font-weight:700; margin-bottom:10px;}
.bandeau.info{background:#f5f3ff; border:1.5px solid #ddd6fe; color:#5b21b6;}
.bandeau.warn{background:#fff7ed; border:1.5px solid #fed7aa; color:#c2410c;}

.stTextInput input, .stTextArea textarea, .stNumberInput input, .stDateInput input, .stTimeInput input{
  color:var(--prune) !important; background:#fff !important; -webkit-text-fill-color:var(--prune) !important;
  border-radius:16px !important; border:1.5px solid #f9a8d4 !important;
  padding:12px 16px !important; font-size:15px !important;
}
[data-baseweb="select"]>div{border-radius:16px !important; border:1.5px solid #f9a8d4 !important; background:#fff !important;}
label p{font-weight:700 !important; font-size:13.5px !important; color:var(--prune-clair) !important;}

.stTabs [data-baseweb="tab-list"]{gap:6px; background:rgba(255,255,255,.8); padding:6px;
  border-radius:20px; border:1.5px solid var(--bord);}
.stTabs [data-baseweb="tab"]{border-radius:14px; padding:8px 14px; font-weight:700; font-size:13.5px; color:var(--rose-fonce);}
.stTabs [aria-selected="true"]{background:linear-gradient(135deg,#ec4899,#db2777); color:#fff !important;}
.stTabs [data-baseweb="tab-highlight"], .stTabs [data-baseweb="tab-border"]{display:none;}

.cal-week{display:grid; grid-template-columns:repeat(7,1fr); gap:4px; margin:0 -4px 8px;}
.cal-week span{text-align:center; font-size:11.5px; font-weight:800; color:#c026d3;}
.cal-title{text-align:center; font-size:16.5px; font-weight:800; color:var(--prune-clair); padding-top:10px;}
.st-key-cal-grid{margin:0 -4px;}
.st-key-cal-grid [data-testid="stHorizontalBlock"],
[data-testid="stHorizontalBlock"]:has([class*="st-key-cal_"]){gap:4px !important;}
.st-key-cal-grid [data-testid="stHorizontalBlock"] > div,
[data-testid="stHorizontalBlock"]:has([class*="st-key-cal_"]) > div{
  flex:1 1 0 !important; width:auto !important; min-width:0 !important; padding:0 !important;
}
[class*="st-key-cal_"] button{
  min-height:0 !important; padding:9px 0 !important; border-radius:12px !important;
  font-size:12.5px !important; font-weight:700 !important; background:#fdf2f8 !important;
  color:var(--prune) !important; border:1.5px solid transparent !important; box-shadow:none !important;
}
[class*="st-key-cal_"] button p{font-size:12.5px !important; font-weight:700 !important; line-height:1.1 !important;}
[class*="st-key-cal_"] button:disabled{background:transparent !important; color:#ecd9f5 !important; opacity:1 !important;}
[class*="st-key-cal_"] button[kind="primary"], [class*="st-key-cal_"] button[data-testid="stBaseButton-primary"]{
  background:linear-gradient(135deg,#ec4899,#a855f7) !important; color:#fff !important;
  box-shadow:0 5px 14px -3px rgba(219,39,119,.55) !important;
}

[class*="st-key-goto-"] button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  border-bottom:1.5px solid #fce7f3 !important; border-radius:0 !important;
  color:var(--prune-clair) !important; font-size:15.5px !important; font-weight:800 !important;
  padding:4px 0 10px !important; display:flex !important; align-items:center !important;
  justify-content:flex-start !important; text-align:left !important;
}
[class*="st-key-goto-"] button p{font-size:15.5px !important; font-weight:800 !important;}
[class*="st-key-goto-"] button::after{content:"›"; margin-left:auto; font-size:21px; opacity:.45;}
[class*="st-key-goto-"] button:hover::after{opacity:.9;}

.st-key-mtabs{margin-bottom:8px;}
.st-key-mtabs [data-testid="stHorizontalBlock"]{gap:6px !important;}
.st-key-mtabs button{font-size:12.5px !important; padding:10px 4px !important; border-radius:16px !important;}
.st-key-mtabs button p{font-size:12.5px !important; font-weight:800 !important;
}

.bloc-head{border-bottom:1.5px solid #fce7f3; margin-bottom:4px; padding-bottom:10px;}

[data-testid="stHorizontalBlock"]:has(.line){
  border-bottom:1px solid #fef2f8; align-items:center !important; gap:4px !important;
}
[data-testid="stHorizontalBlock"]:has(.line) button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  color:#be185d !important; padding:8px 0 !important; font-size:15px !important;
  opacity:.5; transition:opacity .15s ease;
}
[data-testid="stHorizontalBlock"]:has(.line) button:hover{opacity:1;}
.line{padding:12px 0; line-height:1.4;}
.line .q{font-variant-numeric:tabular-nums; opacity:.85;}
.solde .m{font-variant-numeric:tabular-nums;}

.rayon{background:transparent; padding:0 0 4px; margin:0; font-size:13px; letter-spacing:-.1px;}
.rayon .c{opacity:.55; font-weight:700;}

.today-none{padding:12px 0;}
.empty{padding:26px 16px;}
</style>
""", unsafe_allow_html=True)

st.markdown(f"<style>{CSS_CATEGORIES}</style>", unsafe_allow_html=True)

# ==========================================================
# 3. ÉTAT DE SESSION
# ==========================================================
DEFAULTS = {
    "creds_json": None,
    "ops": [],
    "erreur_synchro": None,
    "derniere_synchro": None,
    "annulation": None,
    "_reset": {},
}
for cle, val in DEFAULTS.items():
    if cle not in st.session_state:
        st.session_state[cle] = val

for cle, val in st.session_state["_reset"].items():
    st.session_state[cle] = val
st.session_state["_reset"] = {}

def reset_after(**champs):
    st.session_state["_reset"] = champs

if not st.session_state["creds_json"]:
    try:
        if "gcp_service_account" in st.secrets:
            st.session_state["creds_json"] = json.dumps(dict(st.secrets["gcp_service_account"]))
    except Exception:
        pass

# ==========================================================
# 4. COUCHE DONNÉES
# ==========================================================
@st.cache_resource(show_spinner=False)
def get_client(json_str):
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    return gspread.authorize(Credentials.from_service_account_info(json.loads(json_str), scopes=scope))

@st.cache_resource(show_spinner=False)
def get_doc(json_str):
    client = get_client(json_str)
    try:
        doc = client.open(DOC_NAME)
    except gspread.SpreadsheetNotFound:
        doc = client.create(DOC_NAME)
    titres = {ws.title: ws for ws in doc.worksheets()}
    for nom, entetes in SHEETS.items():
        if nom not in titres:
            ws = doc.add_worksheet(title=nom, rows=1000, cols=max(8, len(entetes)))
            ws.append_row(entetes)
    if "Sheet1" in titres and len(titres) > 1:
        try:
            doc.del_worksheet(titres["Sheet1"])
        except Exception:
            pass
    return doc

@st.cache_resource(show_spinner=False)
def get_ws(json_str, feuille):
    return get_doc(json_str).worksheet(feuille)

@st.cache_data(ttl=300, show_spinner=False)
def fetch_all(json_str):
    doc = get_doc(json_str)
    donnees = {}
    try:
        res = doc.values_batch_get([f"'{n}'!A1:Z2000" for n in SHEETS])
        for nom, vr in zip(SHEETS.keys(), res.get("valueRanges", [])):
            donnees[nom] = vr.get("values", []) or []
    except Exception:
        for nom in SHEETS:
            try:
                donnees[nom] = doc.worksheet(nom).get_all_values()
            except Exception:
                donnees[nom] = []
    for nom, entetes in SHEETS.items():
        if not donnees.get(nom):
            donnees[nom] = [entetes]
    return donnees

def db():
    if "db" not in st.session_state:
        creds = st.session_state["creds_json"]
        if creds:
            with st.spinner("Chargement de vos données…"):
                st.session_state["db"] = fetch_all(creds)
                st.session_state["derniere_synchro"] = datetime.now()
        else:
            st.session_state["db"] = {n: [e] for n, e in SHEETS.items()}
    return st.session_state["db"]

def rows(feuille):
    brut = db().get(feuille, [])
    return [(i + 1, r) for i, r in enumerate(brut[1:])]

def pad(ligne_, n):
    return (list(ligne_) + [""] * n)[:n]

def _executer(op):
    creds = st.session_state["creds_json"]
    genre = op[0]
    if genre == "append":
        get_ws(creds, op[1]).append_row(op[2], value_input_option="USER_ENTERED")
    elif genre == "insert":
        get_ws(creds, op[1]).insert_row(op[2], op[3] + 1, value_input_option="USER_ENTERED")
    elif genre == "delete":
        get_ws(creds, op[1]).delete_rows(op[2] + 1)
    elif genre == "update":
        get_ws(creds, op[1]).update_cell(op[2] + 1, op[3], op[4])
    elif genre == "clear":
        get_ws(creds, op[1]).batch_clear(["A2:Z2000"])

def vider_file():
    if not st.session_state.get("creds_json"):
        return True
    file = st.session_state["ops"]
    while file:
        try:
            _executer(file[0])
            file.pop(0)
            st.session_state["derniere_synchro"] = datetime.now()
        except Exception as err:
            st.session_state["erreur_synchro"] = str(err)[:140]
            return False
    st.session_state["erreur_synchro"] = None
    return True

def pousser(op):
    st.session_state["ops"].append(op)
    vider_file()

def add_row(feuille, ligne_):
    db()[feuille].append(ligne_)
    pousser(("append", feuille, ligne_))

def insert_row(feuille, index, ligne_):
    db()[feuille].insert(index, ligne_)
    pousser(("insert", feuille, ligne_, index))

def delete_row(feuille, index, annulable=True, libelle="Élément supprimé"):
    donnees = db()[feuille]
    if not 0 < index < len(donnees):
        return
    ancienne = list(donnees[index])
    donnees.pop(index)
    pousser(("delete", feuille, index))
    if annulable:
        st.session_state["annulation"] = {"type": "restaurer", "feuille": feuille,
                                         "index": index, "ligne": ancienne, "libelle": libelle}

def set_cell(feuille, index, colonne, valeur, annulable=False, libelle=""):
    donnees = db()[feuille]
    if not 0 < index < len(donnees):
        return
    ligne_ = pad(donnees[index], max(colonne, len(donnees[index])))
    ancienne = ligne_[colonne - 1]
    ligne_[colonne - 1] = valeur
    donnees[index] = ligne_
    pousser(("update", feuille, index, colonne, valeur))
    if annulable:
        st.session_state["annulation"] = {"type": "cellule", "feuille": feuille, "index": index,
                                         "colonne": colonne, "valeur": ancienne, "libelle": libelle}

def clear_sheet(feuille):
    db()[feuille] = [SHEETS[feuille]]
    pousser(("clear", feuille))

def annuler():
    action = st.session_state.get("annulation")
    if not action:
        return
    if action["type"] == "restaurer":
        insert_row(action["feuille"], action["index"], action["ligne"])
    elif action["type"] == "cellule":
        set_cell(action["feuille"], action["index"], action["colonne"], action["valeur"])
    st.session_state["annulation"] = None

def to_float(valeur):
    try:
        return float(str(valeur).replace(",", ".").replace("€", "").strip())
    except (ValueError, AttributeError):
        return 0.0

def parse_date(texte):
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%Y-%m-%d %H:%M:%S"):
        try:
            return datetime.strptime(str(texte).strip(), fmt).date()
        except ValueError:
            continue
    return None

def merge_qte(a, b):
    motif = r"^\s*(\d+(?:[.,]\d+)?)\s*(.*)$"
    ma, mb = re.match(motif, str(a or "")), re.match(motif, str(b or ""))
    if ma and mb and ma.group(2).strip().lower() == mb.group(2).strip().lower():
        total = float(ma.group(1).replace(",", ".")) + float(mb.group(1).replace(",", "."))
        nombre = int(total) if total.is_integer() else round(total, 2)
        return f"{nombre} {ma.group(2).strip()}".strip()
    return f"{a} + {b}"

def deviner_rayon(nom):
    minus = nom.lower()
    for memo in MEMOIRE_COURSES:
        base = memo["article"].lower().split(" /")[0].strip()
        if base and (base in minus or minus in memo["article"].lower()):
            return memo["rayon"]
    for rayon, mots in INDICES_RAYON:
        if any(mot in minus for mot in mots):
            return rayon
    return "Autre"

def separer_quantite(ligne_texte):
    texte = re.sub(r"^\s*[-•*·]\s*", "", str(ligne_texte)).strip()
    m = re.match(r"^(\d+(?:[.,]\d+)?)\s*([a-zA-Zàâçéèêëîïôûùüÿœ.]*)\s+(?:de\s+|d')?(.+)$", texte)
    if m:
        unite = m.group(2).lower().strip()
        if unite in UNITES or unite == "":
            return m.group(3).strip(), f"{m.group(1)} {unite}".strip()
    return texte, "1"

def add_course(article, qte, rayon=None):
    article = str(article).strip()
    if not article:
        return
    nom = article.lower()
    for idx, r in rows("Courses"):
        if pad(r, 3)[0].strip().lower() == nom:
            set_cell("Courses", idx, 2, merge_qte(pad(r, 3)[1] or "1", qte))
            return
    add_row("Courses", [article, qte, rayon or deviner_rayon(article)])

def evenements_tries():
    sortie = []
    for idx, r in rows("Agenda"):
        d, h, ti, desc = pad(r, 4)
        jour = parse_date(d)
        if jour:
            sortie.append((jour, h, ti, desc, idx))
    return sorted(sortie, key=lambda e: (e[0], e[1] or "99:99"))

def taches_actives():
    resultat = []
    for idx, r in rows("Taches"):
        nom, statut = pad(r, 2)
        if statut == "Fait":
            continue
        resultat.append((idx, nom))
    return resultat

def depuis(instant):
    if not instant:
        return "jamais"
    secondes = (datetime.now() - instant).total_seconds()
    if secondes < 60:
        return "à l'instant"
    if secondes < 3600:
        return f"il y a {int(secondes // 60)} min"
    return f"il y a {int(secondes // 3600)} h"

# ==========================================================
# 5. COMPOSANTS D'INTERFACE
# ==========================================================
def conteneur(cle=None, bordure=False):
    try:
        return st.container(border=bordure, key=cle) if cle else st.container(border=bordure)
    except TypeError:
        return st.container(border=bordure)

def titre(texte):
    st.markdown(f"<div class='section'>{texte}</div>", unsafe_allow_html=True)

def vide(texte):
    st.markdown(f"<div class='empty'>{texte}</div>", unsafe_allow_html=True)

def ligne(html, done=False):
    st.markdown(f"<div class='line{' done' if done else ''}'>{html}</div>", unsafe_allow_html=True)

def ligne_action(html, boutons, done=False):
    cols = st.columns([4] + [1] * len(boutons))
    with cols[0]:
        ligne(html, done)
    clique = None
    for col, (icone, cle) in zip(cols[1:], boutons):
        with col:
            if st.button(icone, key=cle):
                clique = cle
    return clique

def pills(cle, options, defaut=None, cols=3):
    if cle not in st.session_state or st.session_state[cle] not in options:
        st.session_state[cle] = defaut if defaut in options else options[0]
    for debut in range(0, len(options), cols):
        groupe = options[debut:debut + cols]
        colonnes = st.columns(cols)
        for col, opt in zip(colonnes, groupe):
            with col:
                actif = st.session_state[cle] == opt
                if st.button(opt, key=f"pill_{cle}_{opt}", type="primary" if actif else "secondary"):
                    st.session_state[cle] = opt
                    st.rerun()
    return st.session_state[cle]

def grille_mois(annee, mois, par_jour, aujourd, selection=None, prefixe="cal"):
    st.markdown("<div class='cal-week'>" + "".join(f"<span>{j}</span>" for j in JOURS_COURT) + "</div>",
                unsafe_allow_html=True)
    choisi, styles = None, []
    with conteneur("cal-grid"):
        for semaine in calendar.Calendar(firstweekday=0).monthdatescalendar(annee, mois):
            colonnes = st.columns(7)
            for col, jour in zip(colonnes, semaine):
                with col:
                    cle = f"{prefixe}_{jour.isoformat()}"
                    if jour.month != mois:
                        st.button(str(jour.day), key=cle, disabled=True)
                        continue
                    nb = len(par_jour.get(jour, []))
                    if st.button(f"{jour.day}•" if nb else str(jour.day), key=cle,
                                 type="primary" if jour == selection else "secondary"):
                        choisi = jour
                    if jour == selection:
                        continue
                    if nb:
                        styles.append(f".st-key-{cle} button{{background:linear-gradient("
                                      f"135deg,#fce7f3,#fae8ff) !important;color:#9d174d !important;}}")
                    if jour == aujourd:
                        styles.append(f".st-key-{cle} button{{border:2px solid #db2777 !important;"
                                      f"color:#db2777 !important;}}")
    if styles:
        st.markdown("<style>" + "".join(styles) + "</style>", unsafe_allow_html=True)
    return choisi

def navigateur_mois(cle_etat, aujourd, prefixe):
    if cle_etat not in st.session_state:
        st.session_state[cle_etat] = (aujourd.year, aujourd.month)
    annee, mois = st.session_state[cle_etat]
    c1, c2, c3 = st.columns([1, 3, 1])
    with c1:
        if st.button("◀", key=f"{prefixe}_prev"):
            st.session_state[cle_etat] = (annee - 1, 12) if mois == 1 else (annee, mois - 1)
            st.rerun()
    with c2:
        st.markdown(f"<div class='cal-title'>{MOIS[mois - 1].capitalize()} {annee}</div>",
                    unsafe_allow_html=True)
    with c3:
        if st.button("▶", key=f"{prefixe}_next"):
            st.session_state[cle_etat] = (annee + 1, 1) if mois == 12 else (annee, mois + 1)
            st.rerun()
    return st.session_state[cle_etat]

def bandeaux():
    en_attente = len(st.session_state.get("ops", []))
    if en_attente:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"<div class='bandeau warn'>⏳ {en_attente} modification(s) en attente "
                        f"d'envoi vers Google</div>", unsafe_allow_html=True)
        with c2:
            if st.button("Réessayer", key="retry_sync"):
                vider_file()
                st.rerun()
    action = st.session_state.get("annulation")
    if action:
        c1, c2 = st.columns([3, 1])
        with c1:
            st.markdown(f"<div class='bandeau info'>{action['libelle']}</div>", unsafe_allow_html=True)
        with c2:
            if st.button("↩️ Annuler", key="undo_btn"):
                annuler()
                st.rerun()

def entete_bloc(texte, compteur=None):
    pastille = f"<span class='n'>{compteur}</span>" if compteur is not None else ""
    st.markdown(f"<div class='bloc-head'><span>{texte}</span>{pastille}</div>", unsafe_allow_html=True)

def entete_lien(cle, texte, compteur, onglet):
    with conteneur(f"goto-{cle}"):
        if st.button(f"{texte}   ·   {compteur}", key=f"goto_{cle}"):
            st.session_state["m_tab"] = onglet
            st.query_params["p"] = "maison"
            st.rerun()

# ==========================================================
# 6. EN-TÊTE ET CONNEXION
# ==========================================================
ajd = date.today()
st.markdown(f"""
<div class="topbar">
  <span>🌸 Lucas &amp; Alex</span>
  <span class="d">{JOURS[ajd.weekday()]} {ajd.day} {MOIS[ajd.month - 1]}</span>
</div>
""", unsafe_allow_html=True)

if not st.session_state["creds_json"]:
    titre("Connexion à Google Sheets")
    st.caption("Déposez le fichier JSON du compte de service. Pour ne plus jamais le redemander, "
               "copiez son contenu dans `.streamlit/secrets.toml` sous `[gcp_service_account]`.")
    fichier = st.file_uploader("Configuration", type=["json"], label_visibility="collapsed")
    if fichier is not None:
        brut = fichier.read().decode("utf-8")
        try:
            with st.spinner("Préparation du classeur…"):
                st.session_state["creds_json"] = brut
                get_doc(brut)
            st.session_state.pop("db", None)
            st.toast("Connexion réussie 💖", icon="✨")
            st.rerun()
        except Exception as err:
            st.session_state["creds_json"] = None
            st.error(f"Connexion impossible : {err}")
    st.stop()

if st.session_state["ops"]:
    vider_file()

# ==========================================================
# 7. NAVIGATION
# ==========================================================
params = st.query_params
page_cle = params.get("p", "accueil")
if page_cle not in PAGES:
    page_cle = "accueil"

with conteneur("navrow"):
    cols = st.columns(3)
    for col, (cle, libelle) in zip(cols, PAGES.items()):
        with col:
            if st.button(libelle, key=f"nav_{cle}", type="primary" if page_cle == cle else "secondary"):
                st.query_params["p"] = cle
                st.rerun()

bandeaux()

evenements = evenements_tries()
par_jour = {}
for ev in evenements:
    par_jour.setdefault(ev[0], []).append(ev)

# ==========================================================
# 8a. ACCUEIL (Dashboard aéré et chaleureux)
# ==========================================================
if page_cle == "accueil":
    courses = rows("Courses")
    budget = rows("Budget")
    notes = rows("Notes")
    repas = rows("Repas")
    actives = taches_actives()

    evts_jour = par_jour.get(ajd, [])
    a_venir = [e for e in evenements if e[0] > ajd]
    repas_jour = [(i, pad(r, 3)) for i, r in repas if pad(r, 3)[0] == JOURS[ajd.weekday()]]

    # ================= 1. COURSES =================
    with conteneur(bordure=True):
        entete_lien("courses", "🛒 Courses", len(courses), ONGLETS_M[0])
        if courses:
            montre = 0
            for rayon in RAYONS:
                du_rayon = [(i, r) for i, r in courses if (pad(r, 3)[2] or "Autre") == rayon]
                if not du_rayon or montre >= 10:
                    continue
                with conteneur(f"grp-{slug(rayon)}"):
                    st.markdown(f"<div class='rayon'>{rayon} <span class='c'>· {len(du_rayon)}</span></div>",
                                unsafe_allow_html=True)
                    for idx, r in du_rayon[:10 - montre]:
                        art, qte, _ = pad(r, 3)
                        if ligne_action(f"{art} <span class='q'>· {qte}</span>", [("✔️", f"acc_co_{idx}")]):
                            delete_row("Courses", idx, libelle=f"« {art} » retiré du panier")
                            st.rerun()
                montre += len(du_rayon[:10 - montre])
            if len(courses) > montre:
                st.caption(f"+ {len(courses) - montre} autres articles · touchez le titre pour tout voir")
        else:
            st.markdown("<div class='today-none'>Le panier est vide.</div>", unsafe_allow_html=True)

    # ================= 2. À FAIRE =================
    with conteneur(bordure=True):
        entete_bloc("🌸 À faire", len(actives) or None)
        if actives:
            for idx, nom in actives[:6]:
                clique = ligne_action(nom, [("✔️", f"acc_tk_{idx}"), ("🗑️", f"acc_td_{idx}")])
                if clique == f"acc_tk_{idx}":
                    set_cell("Taches", idx, 2, "Fait", annulable=True, libelle=f"« {nom} » cochée")
                    st.rerun()
                elif clique == f"acc_td_{idx}":
                    delete_row("Taches", idx, libelle=f"« {nom} » supprimée")
                    st.rerun()
            if len(actives) > 6:
                st.caption(f"+ {len(actives) - 6} autres tâches")
        else:
            st.markdown("<div class='today-none'>🎉 Tout est fait.</div>", unsafe_allow_html=True)

        na_t, nc_t = st.columns([3, 1])
        with na_t:
            dash_t_txt = st.text_input("Tâche", key="dash_t_txt", placeholder="Nouvelle tâche…", label_visibility="collapsed")
        with nc_t:
            if st.button("＋", key="dash_add_t", type="primary") and dash_t_txt.strip():
                add_row("Taches", [dash_t_txt.strip(), "À faire"])
                reset_after(dash_t_txt="")
                st.toast("Tâche ajoutée 🌸", icon="✅")
                st.rerun()

    # ================= 3. AUJOURD'HUI =================
    with conteneur(bordure=True):
        entete_bloc("📅 Aujourd'hui", len(evts_jour) + len(repas_jour) or None)
        if not evts_jour and not repas_jour:
            if a_venir:
                jd, h, ti, _, _ = a_venir[0]
                quand = "demain" if jd == ajd + timedelta(days=1) else f"le {jd.day} {MOIS[jd.month - 1]}"
                st.markdown(f"<div class='today-none'>Rien aujourd'hui. Ensuite : {ti}, {quand}.</div>",
                            unsafe_allow_html=True)
            else:
                st.markdown("<div class='today-none'>Journée libre 🌸</div>", unsafe_allow_html=True)
        for jd, h, ti, desc, idx in evts_jour:
            detail = f"<br><span class='q'>{desc}</span>" if desc else ""
            if ligne_action(f"<span class='tag'>{h or '—'}</span> {ti}{detail}", [("🗑️", f"acc_ev_{idx}")]):
                delete_row("Agenda", idx, libelle=f"« {ti} » supprimé")
                st.rerun()
        for idx, (_, typ, plat) in repas_jour:
            if ligne_action(f"<span class='tag'>{typ}</span> 🍽️ {plat}", [("🗑️", f"acc_rp_{idx}")]):
                delete_row("Repas", idx, libelle=f"« {plat} » retiré du planning")
                st.rerun()

    # ================= 4. NOTE ÉPINGLÉE =================
    epingle = next((pad(r, 3) for _, r in notes
                    if pad(r, 3)[2] == "1" or "important" in pad(r, 3)[0].lower()), None)
    if epingle:
        st.markdown(f"""
        <div class="note-box">
          <div class="t">📌 {epingle[0]}</div>
          <div class="c">{epingle[1]}</div>
        </div>""", unsafe_allow_html=True)

    # ================= 5. LE MOIS =================
    if "dash_jour" not in st.session_state:
        st.session_state["dash_jour"] = ajd
    jour_sel = st.session_state["dash_jour"]

    with conteneur("dash-cal", bordure=True):
        entete_bloc("🗓️ Notre mois", len(a_venir) or None)
        d_annee, d_mois = navigateur_mois("dash_ym", ajd, "dash")
        clic = grille_mois(d_annee, d_mois, par_jour, ajd, jour_sel)
        if clic:
            st.session_state["dash_jour"] = clic
            st.rerun()

        if (d_annee, d_mois) != (ajd.year, ajd.month):
            if st.button("↩️ Revenir à ce mois-ci", key="dash_cal_today"):
                st.session_state["dash_ym"] = (ajd.year, ajd.month)
                st.session_state["dash_jour"] = ajd
                st.rerun()

        marque = " · aujourd'hui" if jour_sel == ajd else ""
        st.markdown(f"<div class='jour-titre'>{JOURS[jour_sel.weekday()]} {jour_sel.day} "
                    f"{MOIS[jour_sel.month - 1]}{marque}</div>", unsafe_allow_html=True)

        du_jour = par_jour.get(jour_sel, [])
        for jd, h, ti, desc, idx in du_jour:
            detail = f"<br><span class='q'>{desc}</span>" if desc else ""
            if ligne_action(f"<span class='tag'>{h or '—'}</span> {ti}{detail}", [("🗑️", f"cal_ev_{idx}")]):
                delete_row("Agenda", idx, libelle=f"« {ti} » supprimé")
                st.rerun()
        if not du_jour:
            st.markdown("<div class='today-none'>Rien de prévu ce jour-là.</div>", unsafe_allow_html=True)

        na, nb, nc = st.columns([1.2, 3, 1])
        with na:
            n_heure = st.text_input("Heure", key="dash_eheure", placeholder="19:30", label_visibility="collapsed")
        with nb:
            n_titre = st.text_input("Événement", key="dash_etitre", placeholder="Ajouter ici…",
                                    label_visibility="collapsed")
        with nc:
            if st.button("＋", key="dash_add_ev", type="primary") and n_titre.strip():
                add_row("Agenda", [str(jour_sel), n_heure.strip(), n_titre.strip(), ""])
                reset_after(dash_etitre="", dash_eheure="")
                st.toast("Événement ajouté 💖", icon="📅")
                st.rerun()

    # ================= 6. BUDGET PARTAGÉ =================
    total_l = sum(to_float(pad(r, 5)[3]) for _, r in budget if pad(r, 5)[1] == "Lucas")
    total_a = sum(to_float(pad(r, 5)[3]) for _, r in budget if pad(r, 5)[1] == "Alex")
    ecart = (total_l - total_a) / 2
    if ecart > 0.005:
        debiteur, qui, combien = "Alex", "Alex doit à Lucas", f"{ecart:.2f} €"
    elif ecart < -0.005:
        debiteur, qui, combien = "Lucas", "Lucas doit à Alex", f"{abs(ecart):.2f} €"
    else:
        debiteur, qui, combien = None, "Comptes équilibrés", "💖"

    st.markdown(f"<div class='solde'><span>{qui}</span><span class='m'>{combien}</span></div>",
                unsafe_allow_html=True)

    if debiteur:
        if st.session_state.get("confirm_solde"):
            s1, s2 = st.columns(2)
            with s1:
                if st.button("Oui, c'est remboursé", type="primary", key="solde_ok"):
                    crediteur = "Lucas" if debiteur == "Alex" else "Alex"
                    add_row("Budget", [str(ajd), debiteur, f"Remboursement à {crediteur}",
                                       f"{abs(total_l - total_a):.2f}", "Fixe/Admin"])
                    st.session_state["confirm_solde"] = False
                    st.rerun()
            with s2:
                if st.button("Annuler", key="solde_non"):
                    st.session_state["confirm_solde"] = False
                    st.rerun()
        elif st.button(f"💸 {debiteur} a remboursé", key="solde_go"):
            st.session_state["confirm_solde"] = True
            st.rerun()

    with st.expander("⚙️ Réglages"):
        d1, d2 = st.columns(2)
        with d1:
            if st.button("🔄 Actualiser", key="refresh"):
                st.cache_data.clear()
                st.session_state.pop("db", None)
                st.rerun()
        with d2:
            if st.button("🚪 Déconnexion", key="logout"):
                st.cache_data.clear()
                st.cache_resource.clear()
                for k in ["creds_json", "db", "ops", "annulation"]:
                    st.session_state.pop(k, None)
                st.rerun()
        st.caption(f"Synchronisé {depuis(st.session_state['derniere_synchro'])} · version {VERSION}")

# ==========================================================
# 8b. BUDGET
# ==========================================================
elif page_cle == "budget":
    budget = rows("Budget")

    if budget:
        lignes = []
        for idx, r in budget:
            d, pyr, lbl, mnt, cat = pad(r, 5)
            jour = parse_date(d)
            lignes.append({"idx": idx, "Date": jour, "Payeur": pyr, "Intitulé": lbl,
                           "Montant": to_float(mnt), "Catégorie": cat or "Alimentation"})
        df = pd.DataFrame(lignes)

        total_l = df[df["Payeur"] == "Lucas"]["Montant"].sum()
        total_a = df[df["Payeur"] == "Alex"]["Montant"].sum()
        ecart = (total_l - total_a) / 2

        m1, m2 = st.columns(2)
        m1.metric("Payé par Lucas", f"{total_l:.2f} €")
        m2.metric("Payé par Alex", f"{total_a:.2f} €")

        if ecart > 0.005:
            st.success(f"👉 Alex doit **{ecart:.2f} €** à Lucas")
        elif ecart < -0.005:
            st.success(f"👉 Lucas doit **{abs(ecart):.2f} €** à Alex")
        else:
            st.info("💖 Comptes parfaitement équilibrés")

        periode = pills("f_periode", ["Ce mois-ci", "Tout"], cols=2)
        if periode == "Ce mois-ci":
            masque = df["Date"].apply(lambda d: bool(d) and (d.year, d.month) == (ajd.year, ajd.month))
            filtre_df = df[masque]
            st.caption(f"Total de {MOIS[ajd.month - 1]} : {filtre_df['Montant'].sum():.2f} €")
        else:
            filtre_df = df

        titre("Dépenses")
        cat_filtre = pills("f_budget", ["Toutes"] + CAT_BUDGET, cols=3)
        visibles = filtre_df if cat_filtre == "Toutes" else filtre_df[filtre_df["Catégorie"] == cat_filtre]

        for _, r in visibles.iloc[::-1].iterrows():
            quand = r["Date"].strftime("%d/%m") if r["Date"] else "—"
            if ligne_action(f"{r['Intitulé']} <span class='tag'>{r['Catégorie']}</span>"
                            f"<br><span class='q'>{r['Montant']:.2f} € · {r['Payeur']} · {quand}</span>",
                            [("🗑️", f"bu_{r['idx']}")]):
                delete_row("Budget", int(r["idx"]), libelle=f"« {r['Intitulé']} » supprimée")
                st.rerun()
        if visibles.empty:
            vide("Aucune dépense sur cette sélection.")
        else:
            export = visibles.drop(columns=["idx"]).to_csv(index=False).encode("utf-8")
            st.download_button("📤 Exporter en CSV", export, file_name="depenses.csv",
                               mime="text/csv", key="dl_budget")
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
        b_date = st.date_input("Date", value=ajd, key="new_bud_date")
    if st.button("Enregistrer la dépense", type="primary", key="add_budget") \
            and b_label.strip() and b_montant > 0:
        add_row("Budget", [str(b_date), b_payeur, b_label.strip(), f"{b_montant:.2f}", b_cat])
        reset_after(new_bud_label="", new_bud_montant=0.0)
        st.toast("Dépense enregistrée 💶", icon="✅")
        st.rerun()

# ==========================================================
# 8c. MAISON (Regroupe Courses, Recettes, Notes)
# ==========================================================
elif page_cle == "maison":
    with conteneur("mtabs"):
        onglet_m = pills("m_tab", ONGLETS_M, cols=3)

    # ---------- COURSES ----------
    if onglet_m == ONGLETS_M[0]:
        courses = rows("Courses")

        titre("💖 Nos articles habituels")
        rayon_memo = pills("memo_rayon", RAYONS[:-1], cols=2)
        deja = {pad(r, 3)[0].strip().lower() for _, r in courses}
        propositions = [m for m in MEMOIRE_COURSES if m["rayon"] == rayon_memo]
        mc1, mc2 = st.columns(2)
        for i, memo in enumerate(propositions):
            with (mc1 if i % 2 == 0 else mc2):
                dedans = memo["article"].strip().lower() in deja
                if st.button(("✅ " if dedans else "＋ ") + memo["article"], key=f"memo_{memo['article']}"):
                    add_course(memo["article"], memo["qte"], memo["rayon"])
                    st.toast(f"{memo['article']} au panier", icon="🛒")
                    st.rerun()

        st.divider()
        titre(f"🛒 Panier ({len(courses)})")
        if courses:
            for rayon in RAYONS:
                du_rayon = [(i, r) for i, r in courses if (pad(r, 3)[2] or "Autre") == rayon]
                if not du_rayon:
                    continue
                with conteneur(f"grp-{slug(rayon)}"):
                    st.markdown(f"<div class='rayon'>{rayon} <span class='c'>· {len(du_rayon)}</span></div>",
                                unsafe_allow_html=True)
                    for idx, r in du_rayon:
                        art, qte, _ = pad(r, 3)
                        if ligne_action(f"{art} <span class='q'>· {qte}</span>", [("✔️", f"co_{idx}")]):
                            delete_row("Courses", idx, libelle=f"« {art} » retiré du panier")
                            st.rerun()

            texte = "🛒 Liste de courses\n\n"
            for rayon in RAYONS:
                du_rayon = [pad(r, 3) for _, r in courses if (pad(r, 3)[2] or "Autre") == rayon]
                if du_rayon:
                    texte += f"— {rayon} —\n" + "".join(f"  • {a} ({q})\n" for a, q, _ in du_rayon) + "\n"
            e1, e2 = st.columns(2)
            with e1:
                st.download_button("📤 Exporter", texte, file_name="liste-de-courses.txt",
                                   mime="text/plain", key="dl_courses")
            with e2:
                if st.session_state.get("confirm_vider"):
                    if st.button("Confirmer", type="primary", key="vider_ok"):
                        clear_sheet("Courses")
                        st.session_state["confirm_vider"] = False
                        st.rerun()
                elif st.button("🧹 Vider", key="vider_go"):
                    st.session_state["confirm_vider"] = True
                    st.rerun()
        else:
            vide("Le panier est vide. Piochez dans les habituels ci-dessus.")

        st.divider()
        titre("Ajouter autre chose")
        st.caption("Le rayon est deviné automatiquement, ajustez-le si besoin.")
        c_rayon = pills("new_course_rayon", RAYONS, cols=2)
        ca, cb = st.columns([3, 1])
        with ca:
            c_art = st.text_input("Article", key="new_course_art", placeholder="Fraises…")
        with cb:
            c_qte = st.text_input("Qté", key="new_course_qte", value="1")
        if st.button("Ajouter au panier", type="primary", key="add_course") and c_art.strip():
            add_course(c_art, c_qte or "1", c_rayon)
            reset_after(new_course_art="", new_course_qte="1")
            st.rerun()

    # ---------- RECETTES ----------
    elif onglet_m == ONGLETS_M[1]:
        recettes = rows("Recettes")
        recherche = st.text_input("Rechercher", key="rec_search", placeholder="🔎 Chercher une recette…",
                                  label_visibility="collapsed")
        trouvees = [(i, r) for i, r in recettes if recherche.lower() in " ".join(pad(r, 3)).lower()]
        for idx, r in trouvees:
            t, ing, inst = pad(r, 3)
            with st.expander(f"🍲 {t}"):
                if ing:
                    st.markdown(f"**Ingrédients**\n\n{ing}")
                if inst:
                    st.markdown(f"**Préparation**\n\n{inst}")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("🛒 Au panier", key=f"rec_panier_{idx}") and ing:
                        ajoutes = 0
                        for brut in ing.splitlines():
                            if brut.strip():
                                article, qte = separer_quantite(brut)
                                add_course(article, qte)
                                ajoutes += 1
                        st.toast(f"{ajoutes} ingrédient(s) ajouté(s) 🛒", icon="✅")
                        st.rerun()
                with b2:
                    if st.button("🗑️ Supprimer", key=f"re_{idx}"):
                        delete_row("Recettes", idx, libelle=f"Recette « {t} » supprimée")
                        st.rerun()
        if not trouvees:
            vide("Aucune recette pour l'instant.")

        st.divider()
        with st.form("form_recette", clear_on_submit=True):
            titre("Nouvelle recette")
            st.caption("Un ingrédient par ligne : « 200 g de farine ». Le panier saura les relire.")
            r_titre = st.text_input("Nom")
            r_ing = st.text_area("Ingrédients", height=90)
            r_inst = st.text_area("Préparation", height=110)
            if st.form_submit_button("Enregistrer la recette", type="primary") and r_titre.strip():
                add_row("Recettes", [r_titre.strip(), r_ing, r_inst])
                st.rerun()

    # ---------- NOTES ----------
    elif onglet_m == ONGLETS_M[2]:
        notes = rows("Notes")
        for idx, r in reversed(notes):
            t, c, ep = pad(r, 3)
            est_epinglee = ep == "1" or "important" in t.lower()
            with st.expander(f"{'📌' if est_epinglee else '📝'} {t}"):
                st.write(c or "_Vide_")
                b1, b2 = st.columns(2)
                with b1:
                    if st.button("📌 Détacher" if est_epinglee else "📌 Épingler", key=f"np_{idx}"):
                        set_cell("Notes", idx, 3, "" if est_epinglee else "1")
                        st.rerun()
                with b2:
                    if st.button("🗑️ Supprimer", key=f"no_{idx}"):
                        delete_row("Notes", idx, libelle=f"Note « {t} » supprimée")
                        st.rerun()
        if not notes:
            vide("Aucune note partagée.")

        st.divider()
        with st.form("form_note", clear_on_submit=True):
            titre("Nouvelle note")
            st.caption("Une note épinglée s'affiche sur l'accueil.")
            n_titre = st.text_input("Titre")
            n_contenu = st.text_area("Contenu", height=110)
            n_pin = st.toggle("Épingler sur l'accueil")
            if st.form_submit_button("Enregistrer la note", type="primary") and n_titre.strip():
                add_row("Notes", [n_titre.strip(), n_contenu, "1" if n_pin else ""])
                st.rerun()
