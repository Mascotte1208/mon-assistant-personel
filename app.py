# ==========================================================
# Notre Assistant — Application Principale Streamlit
# ==========================================================
import streamlit as st
import gspread
from google.oauth2.service_account import Credentials

# ----------------------------------------------------------
# 1. Configuration de la page
# ----------------------------------------------------------
st.set_page_config(
    page_title="Notre Assistant",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"
)

# ----------------------------------------------------------
# 2. Styles CSS globaux (Harmonie visuelle de l'app)
# ----------------------------------------------------------
st.markdown("""
<style>
:root {
    --accent: #C2185B;
    --accent-fonce: #8C1444;
    --accent-doux: #FDF0F6;
    --trait: #F3C7DA;
    --trait-doux: #FBE7F0;
    --encre: #3A1A28;
    --gris: #9B7F8C;
    --surface: #FFFFFF;
    --vert: #17683D;
    --rouge: #B3261E;
    --r: 16px;
}
.block-container {
    padding-top: 1.5rem;
    padding-bottom: 3rem;
    max-width: 820px;
}
/* Style général des cartes */
.app-card {
    background: var(--surface);
    border: 1.5px solid var(--trait);
    border-radius: var(--r);
    padding: 16px;
    margin-bottom: 12px;
    box-shadow: 0 1px 2px rgba(36,27,34,.04);
}
.jour-titre {
    font-size: 14px;
    font-weight: 600;
    color: var(--encre);
}
.tag {
    display: inline-block;
    padding: 2px 8px;
    background: var(--accent-doux);
    color: var(--accent);
    border-radius: 6px;
    font-size: 11.5px;
    font-weight: 600;
    margin-top: 4px;
}
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------
# 3. Connexion Google Sheets & Gestion des données
# ----------------------------------------------------------
@st.cache_resource
def connecter_gspread():
    try:
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        # Nom de la feuille partagée
        sheet_name = st.secrets.get("sheets", {}).get("name", "Notre Assistant")
        return client.open(sheet_name)
    except Exception as e:
        return None

sh = connecter_gspread()

def rows(nom_feuille):
    if not sh:
        return []
    try:
        ws = sh.worksheet(nom_feuille)
        lignes = ws.get_all_values()
        # Renvoie [(index_1_based, [valeurs])]
        return [(i + 1, ligne) for i, ligne in enumerate(lignes)]
    except Exception:
        return []

def add_row(nom_feuille, valeurs):
    if not sh:
        return
    try:
        ws = sh.worksheet(nom_feuille)
        ws.append_row(valeurs)
    except Exception as e:
        st.error(f"Erreur d'ajout : {e}")

def delete_row(nom_feuille, index, actualiser=True, message="Ligne supprimée"):
    if not sh:
        return
    try:
        ws = sh.worksheet(nom_feuille)
        ws.delete_rows(index)
        st.toast(message, icon="🗑️")
        if actualiser:
            st.rerun()
    except Exception as e:
        st.error(f"Erreur de suppression : {e}")

def set_cell(nom_feuille, index, colonne, valeur):
    if not sh:
        return
    try:
        ws = sh.worksheet(nom_feuille)
        ws.update_cell(index, colonne, valeur)
    except Exception as e:
        st.error(f"Erreur de mise à jour : {e}")

def pad(ligne, n):
    ligne = list(ligne)
    while len(ligne) < n:
        ligne.append("")
    return ligne[:n]

# ----------------------------------------------------------
# 4. Composants visuels de base
# ----------------------------------------------------------
def conteneur(cle=None, bordure=True):
    return st.container()

def titre(texte):
    st.markdown(f"## {texte}")

def vide(texte):
    st.markdown(f"<div style='text-align:center; color:var(--gris); padding:20px;'>{texte}</div>", unsafe_allow_html=True)

def pills(cle, options, defaut=None, cols=3):
    if defaut is None and options:
        defaut = options[0]
    return st.radio(cle, options, index=options.index(defaut) if defaut in options else 0, horizontal=True, label_visibility="collapsed")

def entete_bloc(titre_txt, info=""):
    st.markdown(f"""
    <div style='display:flex; justify-content:space-between; align-items:baseline; margin-bottom:8px;'>
        <span style='font-weight:700; font-size:15px; color:var(--accent-fonce);'>{titre_txt}</span>
        <span style='font-size:12px; font-weight:600; color:var(--gris);'>{info}</span>
    </div>
    """, unsafe_allow_html=True)

def reset_after(**champs):
    for k, v in champs.items():
        st.session_state[k] = v

# Dictionnaire du contexte partagé avec les modules externes
ctx = {
    "rows": rows,
    "add_row": add_row,
    "delete_row": delete_row,
    "set_cell": set_cell,
    "pad": pad,
    "conteneur": conteneur,
    "titre": titre,
    "vide": vide,
    "pills": pills,
    "entete_bloc": entete_bloc,
    "reset_after": reset_after,
}

# ----------------------------------------------------------
# 5. Navigation et Barre de sélection des pages
# ----------------------------------------------------------
PAGES = {
    "accueil": "🏠 Accueil",
    "budget": "📊 Budget",
    "maison": "🐾 Maison & Projets",
    "transport": "🚋 Transports",
    "route": "🚦 Code de la route",
    "ialab": "🧠 Labo IA & Marchés",
}

# Option pour activer/désactiver le mode IA Lab dans le menu
if "mode_ia" not in st.session_state:
    st.session_state["mode_ia"] = True

# Barre de navigation horizontale élégante
col_nav1, col_nav2 = st.columns([5, 1])
with col_nav1:
    cles_pages = list(PAGES.keys())
    labels_pages = list(PAGES.values())
    if not st.session_state.get("mode_ia"):
        cles_pages.remove("ialab")
        labels_pages = [v for k, v in PAGES.items() if k != "ialab"]

    # Gestion de l'onglet actif
    if "page_actuelle" not in st.session_state:
        st.session_state["page_actuelle"] = "accueil"

    page_choisie = st.selectbox(
        "Navigation", 
        options=cles_pages, 
        format_func=lambda x: PAGES[x],
        key="selecteur_page_principal",
        label_visibility="collapsed"
    )
    page_cle = page_choisie

with col_nav2:
    if st.button("⚙️ Réglages", use_container_width=True):
        st.session_state["modal_reglages"] = True

st.write("")

# ----------------------------------------------------------
# 6. Routage des Pages
# ----------------------------------------------------------

# --- PAGE ACCUEIL ---
if page_cle == "accueil":
    st.markdown("# 🏠 Bonjour Lucas & Alexia")
    st.markdown("Bienvenue dans votre espace centralisé.")
    
    col_g, col_d = st.columns(2)
    with col_g:
        with st.container():
            st.markdown("### 🚋 Prochains trams & bus")
            try:
                import transports
                transports.carte(ctx)
            except Exception as e:
                st.info("Module transports en attente de configuration.")
    with col_d:
        with st.container():
            st.markdown("### 🚦 Quiz du moment")
            try:
                import code_route
                code_route.carte(st.container, entete_bloc)
            except Exception as e:
                st.info("Module code de la route indisponible.")

# --- PAGE BUDGET ---
elif page_cle == "budget":
    titre("📊 Gestion du Budget")
    st.markdown("Suivi des comptes conjoints et dépenses.")
    # Intègre ton module budget ici si tu en as un séparé, ou gère l'affichage direct
    st.info("Module budget actif (synchronisé avec Google Sheets).")

# --- PAGE MAISON & PROJETS ---
elif page_cle == "maison":
    titre("🐾 Maison, DIY & Saiko")
    st.markdown("Suivi des aménagements (OSB, parpaings) et projets de vie.")
    st.info("Espace de suivi des travaux et idées d'aménagement.")

# --- PAGE TRANSPORTS (STIB) ---
elif page_cle == "transport":
    titre("🚋 Transports en commun (STIB)")
    try:
        import transports
        transports.carte(ctx)
    except Exception as e:
        st.error(f"Erreur de chargement du module transports : {e}")

# --- PAGE CODE DE LA ROUTE ---
elif page_cle == "route":
    titre("🚦 Code de la Route — Entraînement Panneaux")
    try:
        import code_route
        code_route.carte(st.container, entete_bloc)
    except Exception as e:
        st.error(f"Erreur de chargement du module code_route : {e}")

# --- PAGE LABO IA & MARCHÉS ---
elif page_cle == "ialab" and st.session_state.get("mode_ia"):
    try:
        import labo_ia
        labo_ia.render(ctx)
    except Exception as e:
        st.error(f"Erreur dans le Labo IA : {e}")

# ----------------------------------------------------------
# Modal des Réglages / Paramètres
# ----------------------------------------------------------
if st.session_state.get("modal_reglages"):
    with st.expander("🛠️ Panneau de configuration", expanded=True):
        st.markdown("### Options de l'application")
        st.session_state["mode_ia"] = st.toggle("Activer le Labo IA & Marchés", value=st.session_state.get("mode_ia", True))
        if st.button("Fermer les réglages", type="primary"):
            st.session_state["modal_reglages"] = False
            st.rerun()
