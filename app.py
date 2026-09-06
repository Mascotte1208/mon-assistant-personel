"""
Notre Assistant — l'appli partagée du quotidien de Lucas & Alex.

Streamlit + Google Sheets, un seul fichier organisé en sections :
  1. Configuration      5. Composants d'interface
  2. Style & Thèmes     6. Connexion
  3. État de session    7. Navigation
  4. Couche données     8. Pages
"""

import io
import re
import json
import hmac
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
VERSION = "3.9"
DOC_NAME = "MonAssistantData"


def code_labo():
    """Code d'accès au labo, lu dans les secrets — jamais dans le code source.

    Dans les secrets Streamlit :

        [labo]
        code = "votre-code-a-vous"
    """
    try:
        return str(st.secrets["labo"]["code"])
    except Exception:
        return "2026"         # repli si les secrets ne sont pas encore configurés


CODE_LABO = code_labo()
DUREE_LABO = timedelta(hours=2)     # au-delà, le labo se reverrouille tout seul

SHEETS = {
    "Taches":   ["Tache", "Statut"],
    "Agenda":   ["Date", "Heure", "Titre", "Description"],
    "Courses":  ["Article", "Quantite", "Categorie"],
    "Recettes": ["Titre", "Ingredients", "Instructions"],
    "Budget":   ["Date", "Paye Par", "Intitule", "Montant", "Categorie"],
    "Repas":    ["Jour", "Repas", "Plat"],
    "Listes":   ["Categorie", "Element", "Notes"],
    "IA_Lab":   ["Date", "Sujet", "Contenu", "Type"],
    "Trades":   ["Date", "Actif", "Sens", "Entree", "Objectif", "StopLoss", "Statut", "Notes"],
}

RAYONS = ["Fruits & Légumes", "Frais", "Boulangerie", "Supermarché", "Boissons", "Entretien", "Autre"]
RAYON_COULEURS = {
    "Fruits & Légumes": "#17683D",
    "Frais": "#0E7490",
    "Boulangerie": "#A65B12",
    "Supermarché": "#6D3BAF",
    "Boissons": "#164C9E",
    "Entretien": "#C2185B",
    "Autre": "#8A7C82",
}
CAT_BUDGET = ["Alimentation", "Maison/Bricolage", "Sorties", "Fixe/Admin"]
JOURS = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]
JOURS_COURT = ["L", "M", "M", "J", "V", "S", "D"]
MOIS = ["janvier", "février", "mars", "avril", "mai", "juin",
        "juillet", "août", "septembre", "octobre", "novembre", "décembre"]
PERSONNES = ["Lucas", "Alex"]

ONGLETS_M = ["🛒 Courses", "🍲 Recettes"]

# Uniquement des sigles/émojis pour un design épuré (avec le quiz route ajouté)
PAGES = {
    "accueil": "🏠",
    "budget": "📊",
    "maison": "🐾",
    "transport": "🚋",
    "route": "🚦",
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
# 2. STYLE & THÈMES
# ==========================================================
def slug(texte):
    plat = unicodedata.normalize("NFKD", texte).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", plat.lower()).strip("-")

CSS_ROSE = """
<style>
:root{
  --encre:#3A1A28; --encre-2:#6E4A5B; --gris:#9B7F8C;
  --papier:#FDE9F1; --papier-2:#FAD9E7; --surface:#FFFFFF;
  --trait:#F3C7DA; --trait-doux:#FBE7F0; --accent:#C2185B;
  --accent-fonce:#8C1444; --accent-doux:#FDF0F6; --accent-bord:#F3C7DA;
  --vert:#17683D; --ambre:#A65B12; --rouge:#B3261E;
  --r:16px; --r-s:11px;
  --ombre:0 1px 2px rgba(140,20,68,.05), 0 12px 30px -22px rgba(140,20,68,.55);
}
.stApp{background:linear-gradient(180deg,var(--papier) 0%,var(--papier-2) 100%) fixed !important;}
</style>
"""

CSS_NOIR_BLEU = """
<style>
:root{
  --encre:#F0F6FC; --encre-2:#8B949E; --gris:#6E7681;
  --papier:#0D1117; --papier-2:#161B22; --surface:#21262D;
  --trait:#30363D; --trait-doux:#30363D; --accent:#38BDF8;
  --accent-fonce:#0284C7; --accent-doux:#0369A133; --accent-bord:#0284C7;
  --vert:#34D399; --ambre:#FBBF24; --rouge:#F87171;
  --r:16px; --r-s:11px;
  --ombre:0 4px 12px rgba(0,0,0,0.5);
}
.stApp{background:var(--papier) !important;}
</style>
"""

CSS_COMMUN = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"], .stApp{
  font-family:'Plus Jakarta Sans', system-ui, sans-serif !important;
  color:var(--encre); -webkit-tap-highlight-color:transparent;
}
#MainMenu, footer, header{visibility:hidden;}
.block-container{padding-top:0.5rem !important; padding-bottom:5rem !important;
  max-width:560px !important;}

[data-testid="stHorizontalBlock"]{gap:8px !important;}
[data-testid="stHorizontalBlock"] > div{min-width:0 !important;}

[data-testid="stVerticalBlockBorderWrapper"]{
  background:var(--surface) !important;
  border:1.5px solid var(--trait) !important;
  border-radius:var(--r) !important;
  padding:16px 18px 14px !important;
  box-shadow:var(--ombre) !important;
  margin-bottom:14px !important;
}

.bloc-head{
  display:flex; justify-content:space-between; align-items:center; gap:10px;
  padding-bottom:10px; margin-bottom:10px;
  font-size:15px; font-weight:700; letter-spacing:-.01em; color:var(--accent-fonce);
  border-bottom:1.5px solid var(--trait);
}
.bloc-head .n{
  background:var(--accent-doux); color:var(--accent); border:1px solid var(--accent-bord);
  border-radius:999px; padding:1px 9px; font-size:11.5px; font-weight:700;
  font-variant-numeric:tabular-nums;
}
.section{font-size:15px; font-weight:700; color:var(--accent-fonce); margin:20px 0 8px;
  letter-spacing:-.01em;}
.jour-titre{font-size:13px; font-weight:700; color:var(--encre-2); padding:10px 0 6px;}

.stButton>button, .stFormSubmitButton>button, .stDownloadButton>button{
  border-radius:12px !important; font-weight:600 !important; font-size:16px !important;
  padding:10px 14px !important; width:100%;
  border:1.5px solid var(--trait) !important; box-shadow:none !important;
  transition:background .12s ease, border-color .12s ease;
}
button[kind="secondary"], button[data-testid="stBaseButton-secondary"],
button[kind="secondaryFormSubmit"], button[data-testid="stBaseButton-secondaryFormSubmit"],
.stDownloadButton>button{
  background:var(--surface) !important; color:var(--accent) !important;
}
button[kind="secondary"]:hover, button[data-testid="stBaseButton-secondary"]:hover{
  border-color:var(--accent-bord) !important; background:var(--accent-doux) !important;
}
button[kind="primary"], button[data-testid="stBaseButton-primary"],
button[kind="primaryFormSubmit"], button[data-testid="stBaseButton-primaryFormSubmit"]{
  background:linear-gradient(180deg,var(--accent) 0%,var(--accent-fonce) 100%) !important;
  color:#fff !important; border-color:var(--accent-fonce) !important;
  box-shadow:0 6px 16px -8px rgba(140,20,68,.7) !important;
}
button:focus-visible{outline:2px solid var(--accent) !important; outline-offset:2px;}
@media (prefers-reduced-motion:reduce){ *{transition:none !important; animation:none !important;} }

.line{font-size:14.5px; font-weight:600; color:var(--encre); line-height:1.45; padding:2px 0;}
.line.done{color:var(--gris); text-decoration:line-through;}
.line .q{font-weight:600; color:var(--gris); font-size:12.5px;
  font-variant-numeric:tabular-nums;}
[data-testid="stHorizontalBlock"]:has(.line){
  align-items:center !important; gap:6px !important;
  padding:7px 0 !important; border-bottom:1px solid var(--trait-doux) !important;
}
[data-testid="stHorizontalBlock"]:has(.line) button{
  background:transparent !important; border:none !important; box-shadow:none !important;
  color:var(--gris) !important; padding:6px !important; font-size:14px !important;
}
[data-testid="stHorizontalBlock"]:has(.line) button:hover{
  background:var(--accent-doux) !important; color:var(--accent) !important;}

.tag{display:inline-block; padding:2px 8px; border-radius:999px; font-size:11px;
  font-weight:700; background:var(--accent-doux); color:var(--accent);
  border:1px solid var(--accent-bord); margin-right:6px; vertical-align:middle;
  font-variant-numeric:tabular-nums;}
.rayon{font-size:12px; font-weight:700; color:var(--encre-2); display:block;
  margin:4px 0 6px; letter-spacing:.01em;}
.empty{text-align:center; padding:26px 16px; border-radius:var(--r);
  border:1.5px dashed var(--trait); background:var(--accent-doux); color:var(--gris); font-weight:500; font-size:13.5px;}
.today-none{font-size:13.5px; color:var(--gris); font-weight:500; padding:10px 0;}

.solde{display:flex; justify-content:space-between; align-items:center; gap:12px;
  border:1.5px solid var(--trait); border-left:4px solid var(--accent);
  border-radius:var(--r); background:var(--surface); box-shadow:var(--ombre);
  padding:16px 18px; margin:16px 0;
  font-size:12.5px; font-weight:600; color:var(--gris);}
.solde .m{font-size:17px; font-weight:700; color:var(--accent); text-align:right;
  font-variant-numeric:tabular-nums;}

.bandeau{border-radius:12px; padding:10px 13px; font-size:13px; font-weight:600;
  margin-bottom:10px;}
.bandeau.info{background:var(--accent-doux); border:1px solid var(--accent-bord);
  color:var(--accent);}
.bandeau.warn{background:#FDF4EA; border:1px solid #EBD3B4; color:var(--ambre);}

.stTextInput input, .stTextArea textarea, .stNumberInput input,
.stDateInput input, .stTimeInput input{
  color:var(--encre) !important; background:var(--surface) !important;
  -webkit-text-fill-color:var(--encre) !important;
  border-radius:12px !important; border:1.5px solid var(--trait) !important;
  padding:11px 13px !important; font-size:14.5px !important; font-weight:500 !important;
}
.stTextInput input:focus, .stTextArea textarea:focus, .stNumberInput input:focus{
  border-color:var(--accent) !important; box-shadow:0 0 0 3px var(--accent-doux) !important;}
[data-baseweb="select"]>div{border-radius:12px !important;
  border:1.5px solid var(--trait) !important; background:var(--surface) !important;}
label p{font-weight:600 !important; font-size:12.5px !important; color:var(--encre-2) !important;}
[data-testid="stMetric"]{background:var(--surface); border:1px solid var(--trait) !important;
  border-radius:var(--r); padding:14px 16px; box-shadow:none;}
[data-testid="stMetricValue"]{color:var(--encre) !important; font-weight:700 !important;
  font-variant-numeric:tabular-nums;}
[data-testid="stMetricLabel"]{color:var(--gris) !important; font-weight:600 !important;}

.cal-week{display:grid; grid-template-columns:repeat(7,1fr); gap:4px; margin:0 0 6px;}
.cal-week span{text-align:center; font-size:11px; font-weight:700; color:var(--gris);}
.cal-title{text-align:center; font-size:15px; font-weight:700; color:var(--accent-fonce);
  padding-top:8px;}
.st-key-cal-grid [data-testid="stVerticalBlockBorderWrapper"]{
  border:none !important; box-shadow:none !important; padding:0 !important;
  background:transparent !important; margin-bottom:0 !important;}
.st-key-cal-grid [data-testid="stHorizontalBlock"],
[data-testid="stHorizontalBlock"]:has([class*="st-key-cal_"]){gap:4px !important;}
.st-key-cal-grid [data-testid="stHorizontalBlock"] > div,
[data-testid="stHorizontalBlock"]:has([class*="st-key-cal_"]) > div{
  flex:1 1 0 !important; width:auto !important; min-width:0 !important; padding:0 !important;}
[class*="st-key-cal_"] button{
  min-height:0 !important; padding:9px 0 !important; border-radius:10px !important;
  font-size:12.5px !important; font-weight:600 !important; background:var(--surface) !important;
  color:var(--encre-2) !important; border:1.5px solid transparent !important;}
[class*="st-key-cal_"] button p{font-size:12.5px !important; font-weight:600 !important;
  line-height:1.1 !important;}
[class*="st-key-cal_"] button:disabled{background:transparent !important;
  color:#E6C8D6 !important; opacity:1 !important; border:none !important;}
[class*="st-key-cal_"] button[kind="primary"],
[class*="st-key-cal_"] button[data-testid="stBaseButton-primary"]{
  background:linear-gradient(180deg,var(--accent) 0%,var(--accent-fonce) 100%) !important;
  color:#fff !important; border-color:var(--accent-fonce) !important;}

[class*="st-key-goto-"] [data-testid="stVerticalBlockBorderWrapper"]{
  padding:0 !important; border:none !important; box-shadow:none !important;
  background:transparent !important; margin-bottom:14px !important;}
[class*="st-key-goto-"] button{
  background:var(--surface) !important; border:1.5px solid var(--trait) !important;
  border-radius:var(--r) !important; box-shadow:var(--ombre) !important;
  color:var(--accent-fonce) !important; font-size:15px !important; font-weight:700 !important;
  padding:16px 18px !important; text-align:left !important; justify-content:flex-start !important;}
[class*="st-key-goto-"] button p{font-size:15px !important; font-weight:700 !important;}
</style>
"""

# ==========================================================
# 3. ÉTAT DE SESSION
# ==========================================================
DEFAULTS = {
    "creds_json": None,
    "ops": [],
    "erreur_synchro": None,
    "derniere_synchro": None,
    "annulation": None,
    "show_add_tache": False,
    "mode_ia": False,
    "lab_ouvert_a": None,
    "m_tab": ONGLETS_M[0],
    "theme_mode": "🌸 Rose",
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

palette_active = CSS_ROSE if st.session_state["theme_mode"] == "🌸 Rose" else CSS_NOIR_BLEU
st.markdown(palette_active + CSS_COMMUN, unsafe_allow_html=True)

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
def conteneur(cle=None, bordure=True):
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
                        styles.append(f".st-key-{cle} button{{background:#FBE0EC !important;"
                                     f"color:#C2185B !important;}}")
                    if jour == aujourd:
                        styles.append(f".st-key-{cle} button{{border:1.5px solid #C2185B !important;"
                                     f"color:#C2185B !important;}}")
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
            st.markdown(f"<div class='bandeau warn'>⏳ {en_attente} modification(s) en attente</div>", unsafe_allow_html=True)
        with c2:
            if st.button("Réessayer", key="retry_sync"):
                vider_file()
                st.rerun()

def entete_bloc(texte, compteur=None):
    pastille = f"<span class='n'>{compteur}</span>" if compteur is not None else ""
    st.markdown(f"<div class='bloc-head'><span>{texte}</span>{pastille}</div>", unsafe_allow_html=True)

def entete_lien(cle, texte, compteur, onglet):
    with conteneur(f"goto-{cle}"):
        if st.button(f"{texte}    ·    {compteur}", key=f"goto_{cle}"):
            st.session_state["m_tab"] = onglet
            st.query_params["p"] = "maison"
            st.rerun()

# ==========================================================
# 6. CONNEXION
# ==========================================================
ajd = date.today()

if not st.session_state["creds_json"]:
    titre("Connexion à Google Sheets")
    st.caption("Déposez le fichier JSON du compte de service.")
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
# 7. NAVIGATION & MODE IA (Uniquement des sigles/émojis)
# ==========================================================
params = st.query_params
page_cle = params.get("p", "accueil")
if page_cle not in PAGES and page_cle != "ialab":
    page_cle = "accueil"

# Le labo se referme tout seul après deux heures
ouvert_a = st.session_state.get("lab_ouvert_a")
if ouvert_a and datetime.now() - ouvert_a > DUREE_LABO:
    st.session_state["mode_ia"] = False
    st.session_state["lab_ouvert_a"] = None

pages_dispo = PAGES.copy()
if st.session_state.get("mode_ia"):
    pages_dispo["ialab"] = "🧠"

cols_nav = st.columns(len(pages_dispo))
for col, (cle, libelle) in zip(cols_nav, pages_dispo.items()):
    with col:
        if st.button(libelle, key=f"nav_{cle}", type="primary" if page_cle == cle else "secondary"):
            st.query_params["p"] = cle
            st.rerun()

st.divider()

bandeaux()

evenements = evenements_tries()
par_jour = {}
for ev in evenements:
    par_jour.setdefault(ev[0], []).append(ev)

# ==========================================================
# 8a. ACCUEIL
# ==========================================================
if page_cle == "accueil":
    courses = rows("Courses")
    budget = rows("Budget")
    repas = rows("Repas")
    actives = taches_actives()

    evts_jour = par_jour.get(ajd, [])
    a_venir = [e for e in evenements if e[0] > ajd]
    repas_jour = [(i, pad(r, 3)) for i, r in repas if pad(r, 3)[0] == JOURS[ajd.weekday()]]

    # 1. MÉTÉO TOUT EN HAUT (module externe meteo.py)
    try:
        import meteo
        meteo.carte(conteneur, entete_bloc)
    except Exception as err:
        st.caption(f"Météo indisponible : {str(err)[:90]}")

    # 2. À FAIRE
    with conteneur("carte-taches"):
        entete_bloc("🌸 À faire", len(actives) or None)
        if actives:
            for idx, nom in actives[:6]:
                clique = ligne_action(nom, [("✔️", f"acc_tk_{idx}"), ("🗑️", f"acc_td_{idx}")])
                if clique == f"acc_tk_{idx}":
                    set_cell("Taches", idx, 2, "Fait")
                    st.rerun()
                elif clique == f"acc_td_{idx}":
                    delete_row("Taches", idx, libelle=f"« {nom} » supprimée")
                    st.rerun()
        else:
            st.markdown("<div class='today-none'>🎉 Tout est fait.</div>", unsafe_allow_html=True)

        if not st.session_state.get("show_add_tache", False):
            if st.button("＋ Ajouter une tâche", key="btn_toggle_tache"):
                st.session_state["show_add_tache"] = True
                st.rerun()
        else:
            dash_t_txt = st.text_input("Nouvelle tâche", key="dash_t_txt", placeholder="Écrire ici…", label_visibility="collapsed")
            col_b1, col_b2 = st.columns(2)
            with col_b1:
                if st.button("Enregistrer", key="dash_add_t", type="primary") and dash_t_txt.strip():
                    add_row("Taches", [dash_t_txt.strip(), "À faire"])
                    st.session_state["show_add_tache"] = False
                    reset_after(dash_t_txt="")
                    st.rerun()
            with col_b2:
                if st.button("Annuler", key="dash_cancel_t"):
                    st.session_state["show_add_tache"] = False
                    st.rerun()

    # 3. AUJOURD'HUI
    with conteneur("carte-aujourdhui"):
        entete_bloc("📅 Aujourd'hui", len(evts_jour) + len(repas_jour) or None)
        if not evts_jour and not repas_jour:
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

    # 4. COURSES (Redirection épurée)
    entete_lien("courses", "🛒 Courses", len(courses), ONGLETS_M[0])

    # 5. LE MOIS
    if "dash_jour" not in st.session_state:
        st.session_state["dash_jour"] = ajd
    jour_sel = st.session_state["dash_jour"]

    with conteneur("dash-cal"):
        entete_bloc("🗓️ Notre mois", len(a_venir) or None)
        d_annee, d_mois = navigateur_mois("dash_ym", ajd, "dash")
        clic = grille_mois(d_annee, d_mois, par_jour, ajd, jour_sel)
        if clic:
            st.session_state["dash_jour"] = clic
            st.rerun()

        marque = " · aujourd'hui" if jour_sel == ajd else ""
        st.markdown(f"<div class='jour-titre'>{JOURS[jour_sel.weekday()]} {jour_sel.day} {MOIS[jour_sel.month - 1]}{marque}</div>", unsafe_allow_html=True)
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
            n_titre = st.text_input("Événement", key="dash_etitre", placeholder="Ajouter ici…", label_visibility="collapsed")
        with nc:
            if st.button("＋", key="dash_add_ev", type="primary") and n_titre.strip():
                add_row("Agenda", [str(jour_sel), n_heure.strip(), n_titre.strip(), ""])
                reset_after(dash_etitre="", dash_eheure="")
                st.rerun()

    # 6. BUDGET PARTAGÉ
    total_l = sum(to_float(pad(r, 5)[3]) for _, r in budget if pad(r, 5)[1] == "Lucas")
    total_a = sum(to_float(pad(r, 5)[3]) for _, r in budget if pad(r, 5)[1] == "Alex")
    ecart = (total_l - total_a) / 2
    qui = f"Alex doit à Lucas : {ecart:.2f} €" if ecart > 0.005 else f"Lucas doit à Alex : {abs(ecart):.2f} €" if ecart < -0.005 else "Comptes équilibrés 💖"
    st.markdown(f"<div class='solde'><span>État</span><span class='m'>{qui}</span></div>", unsafe_allow_html=True)

    # 7. RÉGLAGES & ACCÈS DIRECT LABO IA
    with st.expander("⚙️ Réglages & Apparence"):
        nouveau_theme = st.radio("Thème visuel", ["🌸 Rose", "🌙 Noir & Bleu"],
                                 index=0 if st.session_state["theme_mode"] == "🌸 Rose" else 1,
                                 horizontal=True)
        if nouveau_theme != st.session_state["theme_mode"]:
            st.session_state["theme_mode"] = nouveau_theme
            st.rerun()

        st.divider()
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
                for k in ["creds_json", "db", "ops", "annulation", "mode_ia",
                          "lab_ouvert_a", "theme_mode"]:
                    st.session_state.pop(k, None)
                st.rerun()

        st.divider()
        st.markdown("**🔐 Accès Labo IA**")
        if st.session_state.get("mode_ia"):
            reste = ""
            if st.session_state.get("lab_ouvert_a"):
                minutes = int((DUREE_LABO - (datetime.now() - st.session_state["lab_ouvert_a"]))
                              .total_seconds() // 60)
                reste = f" · se referme dans {max(minutes, 0)} min"
            st.caption(f"Labo déverrouillé pour cette session{reste}.")
            b1, b2 = st.columns(2)
            with b1:
                if st.button("🧠 Ouvrir le labo", key="sec_open", type="primary"):
                    st.query_params["p"] = "ialab"
                    st.rerun()
            with b2:
                if st.button("🔒 Verrouiller", key="sec_lock"):
                    st.session_state["mode_ia"] = False
                    st.session_state["lab_ouvert_a"] = None
                    st.query_params["p"] = "accueil"
                    st.rerun()
        else:
            pwd = st.text_input("Code secret", type="password", key="sec_pwd_input",
                                placeholder="Entrez le code…")
            if st.button("Déverrouiller", key="sec_pwd_go"):
                if pwd and hmac.compare_digest(pwd.strip(), CODE_LABO):
                    st.session_state["mode_ia"] = True
                    st.session_state["lab_ouvert_a"] = datetime.now()
                    reset_after(sec_pwd_input="")
                    st.query_params["p"] = "ialab"
                    st.rerun()
                else:
                    st.error("Code incorrect")

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
            lignes.append({"idx": idx, "Date": parse_date(d), "Payeur": pyr, "Intitulé": lbl, "Montant": to_float(mnt), "Catégorie": cat or "Alimentation"})
        df = pd.DataFrame(lignes)
        m1, m2 = st.columns(2)
        m1.metric("Payé par Lucas", f"{df[df['Payeur'] == 'Lucas']['Montant'].sum():.2f} €")
        m2.metric("Payé par Alex", f"{df[df['Payeur'] == 'Alex']['Montant'].sum():.2f} €")
        titre("Dépenses")
        for _, r in df.iloc[::-1].iterrows():
            if ligne_action(f"{r['Intitulé']} <span class='tag'>{r['Catégorie']}</span><br><span class='q'>{r['Montant']:.2f} € · {r['Payeur']}</span>", [("🗑️", f"bu_{r['idx']}")]):
                delete_row("Budget", int(r["idx"]), libelle="Dépense supprimée")
                st.rerun()
    else:
        vide("Aucune dépense.")

    st.divider()
    titre("Nouvelle dépense")
    b_payeur = pills("new_bud_payeur", PERSONNES, cols=2)
    b_cat = pills("new_bud_cat", CAT_BUDGET, cols=2)
    b_label = st.text_input("Intitulé", key="new_bud_label", placeholder="Magasin…")
    bc1, bc2 = st.columns(2)
    with bc1:
        b_montant = st.number_input("Montant (€)", min_value=0.0, step=0.5, key="new_bud_montant")
    with bc2:
        b_date = st.date_input("Date", value=ajd, key="new_bud_date")
    if st.button("Enregistrer", type="primary", key="add_budget") and b_label.strip() and b_montant > 0:
        add_row("Budget", [str(b_date), b_payeur, b_label.strip(), f"{b_montant:.2f}", b_cat])
        reset_after(new_bud_label="", new_bud_montant=0.0)
        st.rerun()

# ==========================================================
# 8c. MAISON
# ==========================================================
elif page_cle == "maison":
    with conteneur("mtabs"):
        onglet_m = pills("m_tab", ONGLETS_M, cols=2)

    if onglet_m == ONGLETS_M[0]:
        courses = rows("Courses")
        titre("💖 Articles habituels")
        rayon_memo = pills("memo_rayon", RAYONS[:-1], cols=2)
        deja = {pad(r, 3)[0].strip().lower() for _, r in courses}
        mc1, mc2 = st.columns(2)
        for i, memo in enumerate([m for m in MEMOIRE_COURSES if m["rayon"] == rayon_memo]):
            with (mc1 if i % 2 == 0 else mc2):
                if st.button(("✅ " if memo["article"].lower() in deja else "＋ ") + memo["article"], key=f"memo_{memo['article']}"):
                    add_course(memo["article"], memo["qte"], memo["rayon"])
                    st.rerun()

        st.divider()
        titre(f"🛒 Panier ({len(courses)})")
        if courses:
            for rayon in RAYONS:
                du_rayon = [(i, r) for i, r in courses if (pad(r, 3)[2] or "Autre") == rayon]
                if not du_rayon:
                    continue
                with conteneur(f"grp-{slug(rayon)}"):
                    st.markdown(f"<div class='rayon'>{rayon}</div>", unsafe_allow_html=True)
                    for idx, r in du_rayon:
                        art, qte, _ = pad(r, 3)
                        if ligne_action(f"{art} <span class='q'>· {qte}</span>", [("✔️", f"co_{idx}")]):
                            delete_row("Courses", idx, libelle="Article retiré")
                            st.rerun()
        else:
            vide("Panier vide.")

    elif onglet_m == ONGLETS_M[1]:
        recettes = rows("Recettes")
        for idx, r in recettes:
            t, ing, _ = pad(r, 3)
            with st.expander(f"🍲 {t}"):
                if ing:
                    st.markdown(f"**Ingrédients**\n\n{ing}")
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
                        delete_row("Recettes", idx, libelle="Recette supprimée")
                        st.rerun()
        if not recettes:
            vide("Aucune recette pour l'instant.")

        st.divider()
        with st.form("form_recette", clear_on_submit=True):
            titre("Nouvelle recette")
            st.caption("Un ingrédient par ligne : « 200 g de farine ». Le panier saura les relire.")
            r_titre = st.text_input("Nom")
            r_ing = st.text_area("Ingrédients", height=120)
            if st.form_submit_button("Enregistrer la recette", type="primary") and r_titre.strip():
                add_row("Recettes", [r_titre.strip(), r_ing, ""])
                st.rerun()

# ==========================================================
# 8d. TRANSPORTS — module externe transports.py
# ==========================================================
elif page_cle == "transport":
    try:
        import transports
        transports.carte({
            "conteneur": conteneur, "entete_bloc": entete_bloc,
            "rows": rows, "add_row": add_row, "delete_row": delete_row, "pad": pad,
        })
    except Exception as err:
        st.error(f"Module transports.py indisponible : {str(err)[:120]}")

# ==========================================================
# 8e. CODE DE LA ROUTE — module externe code_route.py
# ==========================================================
elif page_cle == "route":
    titre("🚦 Code de la Route — Entraînement Panneaux")
    try:
        import code_route
        code_route.carte(conteneur, entete_bloc)
    except Exception as err:
        st.error(f"Module code_route.py indisponible : {str(err)[:120]}")

# ==========================================================
# 8f. LABO IA & MARCHÉS — module externe labo_ia.py
# ==========================================================
elif page_cle == "ialab" and st.session_state.get("mode_ia"):
    try:
        import labo_ia
    except Exception as err:
        st.error(f"Module labo_ia.py introuvable : {err}")
    else:
        labo_ia.render({
            "rows": rows, "add_row": add_row, "delete_row": delete_row,
            "set_cell": set_cell, "pad": pad, "to_float": to_float,
            "parse_date": parse_date, "conteneur": conteneur, "titre": titre,
            "vide": vide, "pills": pills, "reset_after": reset_after,
            "vider_file": vider_file,
        })

# ==========================================================
# 8g. LABO DEMANDÉ SANS ACCÈS
# ==========================================================
elif page_cle == "ialab":
    vide("Le labo est verrouillé. Entrez le code dans Réglages, sur la page d'accueil.")
