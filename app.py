import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime, date
import calendar

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Notre Assistant Shared", 
    page_icon="✨", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- BALISES PWA & NATIVE MOBILE ---
st.markdown("""
    <head>
        <meta name="viewport" content="width=device-width, initial-scale=1.0, maximum-scale=1.0, user-scalable=no" />
        <meta name="apple-mobile-web-app-capable" content="yes" />
        <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent" />
        <meta name="theme-color" content="#4338ca" />
        <link rel="apple-touch-icon" href="https://img.icons8.com/emoji/192/sparkles-emoji.png" />
    </head>
""", unsafe_allow_html=True)

# --- STYLE CSS DESIGN SUR-MESURE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background: linear-gradient(180deg, #f8f8f6 0%, #f1f1ed 100%) !important;
        color: #1c1917;
        -webkit-tap-highlight-color: transparent;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 4rem !important;
        max-width: 550px !important;
    }

    .hero-banner {
        background: linear-gradient(135deg, #3730a3 0%, #5b21b6 50%, #831843 100%);
        border-radius: 28px;
        padding: 22px 20px;
        color: white;
        margin-bottom: 18px;
        box-shadow: 0 12px 24px -6px rgba(55, 48, 163, 0.25);
        position: relative;
        overflow: hidden;
    }
    .hero-title {
        font-size: 22px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-sub {
        font-size: 12px;
        opacity: 0.9;
        margin-top: 4px;
        font-weight: 600;
    }

    .wooden-block-calendar {
        background: linear-gradient(145deg, #2d241e, #1a1512);
        border: 2px solid #524136;
        border-radius: 20px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 10px 20px rgba(0,0,0,0.2);
        margin-bottom: 16px;
    }
    .block-month {
        font-size: 13px;
        font-weight: 800;
        color: #f59e0b;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 8px;
    }
    .block-cubes {
        display: flex;
        justify-content: center;
        gap: 10px;
        margin-bottom: 8px;
    }
    .block-cube {
        background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%);
        color: #1e293b;
        font-size: 32px;
        font-weight: 800;
        width: 55px;
        height: 60px;
        line-height: 60px;
        border-radius: 14px;
        box-shadow: inset 0 -3px 0 rgba(0,0,0,0.15), 0 4px 8px rgba(0,0,0,0.25);
    }
    .block-dayname {
        font-size: 12px;
        font-weight: 700;
        color: #e2e8f0;
        background: rgba(255,255,255,0.1);
        padding: 4px 12px;
        border-radius: 10px;
        display: inline-block;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: rgba(229, 229, 224, 0.8);
        backdrop-filter: blur(10px);
        padding: 6px;
        border-radius: 24px;
        overflow-x: auto;
        margin-bottom: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 16px;
        padding: 8px 14px;
        font-weight: 700;
        font-size: 12px;
        color: #78716c;
        background-color: transparent;
        border: none;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #3730a3 !important;
        box-shadow: 0 4px 12px rgba(55, 48, 163, 0.12);
    }

    /* Mini Cartes Épurées Dashboard */
    .metric-card {
        background: #ffffff;
        border-radius: 18px;
        padding: 14px 16px;
        border: 1px solid #e7e5e4;
        box-shadow: 0 4px 12px rgba(0,0,0,0.02);
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .metric-title {
        font-size: 12px;
        font-weight: 700;
        color: #78716c;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 20px;
        font-weight: 800;
        color: #1c1917;
    }

    .stButton button {
        border-radius: 16px;
        font-weight: 800;
        font-size: 13px;
        background: linear-gradient(135deg, #4338ca 0%, #3730a3 100%);
        color: white;
        border: none;
        padding: 12px 18px;
        box-shadow: 0 4px 12px rgba(67, 56, 202, 0.2);
    }
    .stButton button:active { transform: scale(0.97); }

    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        color: #1c1917 !important;
        background-color: #ffffff !important;
        -webkit-text-fill-color: #1c1917 !important;
        border-radius: 16px !important;
        border: 1.5px solid #d6d3d1 !important;
        padding: 10px 14px !important;
        font-size: 15px !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- MÉMOIRE DES ARTICLES HABITUELS ---
MEMOIRE_COURSES = [
    {"article": "Tomates cerises", "qte": "1 bte", "rayon": "Fruits & Légumes"},
    {"article": "Avocats", "qte": "2", "rayon": "Fruits & Légumes"},
    {"article": "Concombre", "qte": "1", "rayon": "Fruits & Légumes"},
    {"article": "Salade / Roquette", "qte": "1 sachet", "rayon": "Fruits & Légumes"},
    {"article": "Oignons", "qte": "1 sachet", "rayon": "Fruits & Légumes"},
    {"article": "Ail", "qte": "1 tte", "rayon": "Fruits & Légumes"},
    {"article": "Courgettes", "qte": "2", "rayon": "Fruits & Légumes"},
    {"article": "Citrons", "qte": "2", "rayon": "Fruits & Légumes"},
    {"article": "Œufs frais", "qte": "1 bte", "rayon": "Frais"},
    {"article": "Lait sans lactose / Demi-écrémé", "qte": "1 L", "rayon": "Frais"},
    {"article": "Beurre doux", "qte": "1 plq", "rayon": "Frais"},
    {"article": "Gouda / Fromage tranché", "qte": "1 pqt", "rayon": "Frais"},
    {"article": "Feta ou Mozzarella / Burrata", "qte": "1", "rayon": "Frais"},
    {"article": "Escalopes ou Nuggets vegan", "qte": "1 pqt", "rayon": "Frais"},
    {"article": "Saumon fumé", "qte": "1 pqt", "rayon": "Frais"},
    {"article": "Thon en boîte", "qte": "1 bte", "rayon": "Frais"},
    {"article": "Yaourts nature / grecs", "qte": "4 pot", "rayon": "Frais"},
    {"article": "Pain / Baguette tradition", "qte": "1", "rayon": "Boulangerie"},
    {"article": "Sandwichs / Pains panini", "qte": "2", "rayon": "Boulangerie"},
    {"article": "Pâtes / Tortellini", "qte": "1 sachet", "rayon": "Supermarché"},
    {"article": "Riz basmati", "qte": "1 pqt", "rayon": "Supermarché"},
    {"article": "Café moulu / Capsules", "qte": "1 pqt", "rayon": "Supermarché"},
    {"article": "Sirop de menthe", "qte": "1 btl", "rayon": "Boissons"},
    {"article": "Jus d'orange / Mandarine", "qte": "1 btl", "rayon": "Boissons"},
    {"article": "Huile d'olive", "qte": "1 btl", "rayon": "Supermarché"},
    {"article": "Sel & Poivre / Épices", "qte": "1", "rayon": "Supermarché"},
    {"article": "Papier toilette", "qte": "1 pqt", "rayon": "Entretien"},
    {"article": "Liquide vaisselle", "qte": "1 btl", "rayon": "Entretien"},
    {"article": "Éponges", "qte": "1 pqt", "rayon": "Entretien"},
    {"article": "Sacs poubelle", "qte": "1 rlx", "rayon": "Entretien"}
]

def get_gspread_client(json_str):
    creds_dict = json.loads(json_str)
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

def sync_sheet_to_state(sheet_name, data):
    st.session_state[f"data_{sheet_name}"] = data

def get_data(sheet_name):
    if f"data_{sheet_name}" not in st.session_state:
        if st.session_state.get("json_credentials_str"):
            try:
                client = get_gspread_client(st.session_state["json_credentials_str"])
                ws = client.open("MonAssistantData").worksheet(sheet_name)
                st.session_state[f"data_{sheet_name}"] = ws.get_all_values()
            except Exception:
                st.session_state[f"data_{sheet_name}"] = []
        else:
            st.session_state[f"data_{sheet_name}"] = []
    return st.session_state[f"data_{sheet_name}"]

def append_row_fast(sheet_name, row):
    data = get_data(sheet_name)
    data.append(row)
    sync_sheet_to_state(sheet_name, data)
    if st.session_state.get("json_credentials_str"):
        try:
            client = get_gspread_client(st.session_state["json_credentials_str"])
            client.open("MonAssistantData").worksheet(sheet_name).append_row(row)
        except Exception:
            pass

def delete_row_fast(sheet_name, index):
    data = get_data(sheet_name)
    if 0 <= index < len(data):
        data.pop(index)
        sync_sheet_to_state(sheet_name, data)
        if st.session_state.get("json_credentials_str"):
            try:
                client = get_gspread_client(st.session_state["json_credentials_str"])
                client.open("MonAssistantData").worksheet(sheet_name).delete_rows(index + 1)
            except Exception:
                pass

def update_cell_fast(sheet_name, row_idx, col_idx, value):
    data = get_data(sheet_name)
    if 0 <= row_idx < len(data):
        data[row_idx][col_idx - 1] = value
        sync_sheet_to_state(sheet_name, data)
        if st.session_state.get("json_credentials_str"):
            try:
                client = get_gspread_client(st.session_state["json_credentials_str"])
                client.open("MonAssistantData").worksheet(sheet_name).update_cell(row_idx + 1, col_idx, value)
            except Exception:
                pass

if "json_credentials_str" not in st.session_state:
    st.session_state["json_credentials_str"] = None

# --- HERO BANNER ---
st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">Bonjour Lucas & Alex 👋</div>
        <div class="hero-sub">Espace partagé & assistant quotidien</div>
    </div>
""", unsafe_allow_html=True)

# --- CALENDRIER ---
today = date.today()
mois_fr = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"]
jours_fr = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"]

day_str = f"{today.day:02d}"
st.markdown(f"""
    <div class="wooden-block-calendar">
        <div class="block-month">📅 {mois_fr[today.month - 1]}</div>
        <div class="block-cubes">
            <div class="block-cube">{day_str[0]}</div>
            <div class="block-cube">{day_str[1]}</div>
        </div>
        <div class="block-dayname">{jours_fr[today.weekday()]}</div>
    </div>
""", unsafe_allow_html=True)

# --- NAVIGATION ---
tab_dash, tab_quotidien, tab_budget_adv, tab_loisirs = st.tabs([
    "🏠 Dashboard", "📋 Quotidien", "📊 Budget", "🐾 Maison & Loisirs"
])

# ==========================================
# 1. DASHBOARD ULTRA CLAIR & ÉPURÉ
# ==========================================
with tab_dash:
    if not st.session_state["json_credentials_str"]:
        st.warning("⚠️ Connexion Google Sheets requise.")
        uploaded_json = st.file_uploader("Glissez votre fichier JSON de configuration ici", type=["json"])
        if uploaded_json is not None:
            raw_json = uploaded_json.read().decode("utf-8")
            st.session_state["json_credentials_str"] = raw_json
            client = get_gspread_client(raw_json)
            try:
                doc = client.open("MonAssistantData")
            except gspread.SpreadsheetNotFound:
                doc = client.create("MonAssistantData")
                doc.values_append("Sheet1", {'valueInputOption': 'RAW'}, {'values': [['Tache', 'Categorie', 'Statut']]})
                doc.rename_worksheet(doc.worksheet("Sheet1"), "Taches")
                for ws_title, headers in [
                    ("Agenda", [['Date', 'Heure', 'Titre', 'Description']]),
                    ("Courses", [['Article', 'Quantite', 'Categorie']]),
                    ("Notes", [['Titre', 'Contenu']]),
                    ("Recettes", [['Titre', 'Ingrédients', 'Instructions']]),
                    ("Budget", [['Date', 'Payé Par', 'Intitulé', 'Montant', 'Catégorie']]),
                    ("Repas", [['Jour', 'Repas', 'Plat']]),
                    ("Listes", [['Catégorie', 'Élément', 'Notes']])
                ]:
                    doc.add_worksheet(title=ws_title, rows="100", cols="20")
                    doc.values_append(ws_title, {'valueInputOption': 'RAW'}, {'values': headers})
            st.success("Connexion réussie !")
            st.rerun()
    else:
        json_str = st.session_state["json_credentials_str"]
        taches_vals = get_data("Taches")
        courses_vals = get_data("Courses")
        budget_vals = get_data("Budget")
        
        taches_data = taches_vals[1:] if len(taches_vals) > 1 else []
        taches_faites = len([t for t in taches_data if len(t) > 2 and t[2] == "Fait"])
        total_taches = len(taches_data)
        nb_courses = max(0, len(courses_vals) - 1)

        total_lucas, total_alex = 0.0, 0.0
        for r in (budget_vals[1:] if len(budget_vals) > 1 else []):
            payer = r[1] if len(r) > 1 else ""
            try: amt = float(r[3].replace(',', '.')) if len(r) > 3 else 0.0
            except ValueError: amt = 0.0
            if payer == "Lucas": total_lucas += amt
            elif payer == "Alex": total_alex += amt
        diff = (total_lucas - total_alex) / 2
        bilan_str = f"Alex doit {diff:.2f} € à Lucas" if diff > 0 else (f"Lucas doit {abs(diff):.2f} € à Alex" if diff < 0 else "Comptes équilibrés ⚖️")

        st.markdown("<p style='font-weight: 800; font-size: 15px; color: #1c1917; margin-bottom: 12px;'>📊 Vue d'ensemble</p>", unsafe_allow_html=True)

        # Lignes épurées sous forme de mini-cartes clean
        st.markdown(f"""
            <div class="metric-card">
                <span class="metric-title">✅ Tâches du jour</span>
                <span class="metric-value">{taches_faites} / {total_taches}</span>
            </div>
            <div class="metric-card">
                <span class="metric-title">🛒 Panier Courses</span>
                <span class="metric-value">{nb_courses} art.</span>
            </div>
            <div class="metric-card">
                <span class="metric-title">💶 Équilibre Budget</span>
                <span class="metric-value" style="font-size: 15px; font-weight: 700; color: #4338ca;">{bilan_str}</span>
            </div>
        """, unsafe_allow_html=True)

        st.divider()
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔄 Actualiser"):
                for key in list(st.session_state.keys()):
                    if key.startswith("data_"): del st.session_state[key]
                st.rerun()
        with col_act2:
            if st.button("🔴 Déconnexion"):
                st.session_state["json_credentials_str"] = None
                for key in list(st.session_state.keys()):
                    if key.startswith("data_"): del st.session_state[key]
                st.rerun()

json_str = st.session_state["json_credentials_str"]

# ==========================================
# 2. QUOTIDIEN
# ==========================================
with tab_quotidien:
    if json_str:
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["✅ Tâches", "📅 Agenda", "🛒 Courses", "🍽️ Repas"])
        
        with sub_tab1:
            st.subheader("✅ Tâches à faire")
            all_vals = get_data("Taches")
            taches_data = all_vals[1:] if len(all_vals) > 1 else []
            
            if taches_data: st.progress(len([t for t in taches_data if len(t) > 2 and t[2] == "Fait"]) / len(taches_data))

            cat_filter = st.selectbox("🔍 Filtrer", ["Toutes", "Maison", "Urgent", "Autre"])
            filtered = [t for t in taches_data if cat_filter == "Toutes" or (len(t) > 1 and t[1] == cat_filter)]

            if filtered:
                for idx, row in enumerate(filtered):
                    nom_t, cat_t, statut_t = (row + ["Sans nom", "Général", "À faire"])[:3]
                    real_idx = all_vals.index(row)
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        if statut_t == "Fait": st.markdown(f"- ~~**{nom_t}**~~ <span class='badge-tag'>{cat_t}</span>", unsafe_allow_html=True)
                        else: st.markdown(f"- **{nom_t}** <span class='badge-tag'>{cat_t}</span>", unsafe_allow_html=True)
                    with c2:
                        if statut_t != "Fait":
                            if st.button("✔️", key=f"t_fait_{real_idx}"):
                                update_cell_fast("Taches", real_idx, 3, "Fait")
                                st.rerun()
                        else:
                            if st.button("🗑️", key=f"t_del_{real_idx}"):
                                delete_row_fast("Taches", real_idx)
                                st.rerun()
            else: st.info("Aucune tâche.")

            st.divider()
            with st.form("form_tache", clear_on_submit=True):
                n_tache = st.text_input("Intitulé")
                n_cat = st.selectbox("Catégorie", ["Maison", "Urgent", "Autre"])
                if st.form_submit_button("Ajouter") and n_tache:
                    append_row_fast("Taches", [n_tache, n_cat, "À faire"])
                    st.rerun()

        with sub_tab2:
            st.subheader("📅 Agenda")
            all_agenda_vals = get_data("Agenda")
            agenda_events_data = all_agenda_vals[1:] if len(all_agenda_vals) > 1 else []
            
            if agenda_events_data:
                for idx, row in enumerate(agenda_events_data):
                    date_ev, heure_ev, titre_ev, desc_ev = (row + ["", "", "", ""])[:4]
                    real_idx = idx + 1
                    with st.expander(f"🗓️ {date_ev} {f'à {heure_ev}' if heure_ev else ''} — {titre_ev}"):
                        if desc_ev: st.write(f"**Détails :** {desc_ev}")
                        if st.button("🗑️ Supprimer", key=f"ev_del_{real_idx}"):
                            delete_row_fast("Agenda", real_idx)
                            st.rerun()
            else: st.info("Aucun événement.")

            st.divider()
            with st.form("form_agenda", clear_on_submit=True):
                e_date = st.date_input("Date", value=datetime.today())
                e_heure = st.time_input("Heure", value=datetime.now().time())
                e_titre = st.text_input("Titre")
                e_desc = st.text_area("Description")
                if st.form_submit_button("Enregistrer") and e_titre:
                    append_row_fast("Agenda", [str(e_date), str(e_heure.strftime("%H:%M")), e_titre, e_desc])
                    st.rerun()

        with sub_tab3:
            st.subheader("🛒 Liste de Courses Organisée")
            
            with st.expander("🧠 Piocher dans mes articles habituels"):
                rayons_dispos = sorted(list(set(item["rayon"] for item in MEMOIRE_COURSES)))
                selected_rayon = st.selectbox("Filtrer par rayon :", rayons_dispos)
                filtered_memo = [m for m in MEMOIRE_COURSES if m["rayon"] == selected_rayon]
                memo_noms = [m["article"] for m in filtered_memo]
                
                chosen_memo = st.multiselect(f"Articles ({selected_rayon}) :", memo_noms)
                if st.button("➕ Ajouter la sélection"):
                    if chosen_memo:
                        for article_name in chosen_memo:
                            match = next((m for m in MEMOIRE_COURSES if m["article"] == article_name), None)
                            if match:
                                append_row_fast("Courses", [match["article"], match["qte"], match["rayon"]])
                        st.success("Ajouté !")
                        st.rerun()

            st.divider()
            all_vals = get_data("Courses")
            courses_data = all_vals[1:] if len(all_vals) > 1 else []

            if courses_data:
                rayons_ordre = ["Fruits & Légumes", "Frais", "Boulangerie", "Supermarché", "Boissons", "Entretien", "Autre"]
                for rayon in rayons_ordre:
                    articles_du_rayon = [r for r in courses_data if (r[2] if len(r) > 2 else "Autre") == rayon]
                    if articles_du_rayon:
                        st.markdown(f"**🏷️ {rayon}**")
                        for row in articles_du_rayon:
                            art, qte = (row + ["Article", "1"])[:2]
                            real_idx = all_vals.index(row)
                            c1, c2 = st.columns([3, 1])
                            with c1: st.markdown(f"- {art} *(Qté: {qte})*")
                            with c2:
                                if st.button("✔️", key=f"c_del_{real_idx}"):
                                    delete_row_fast("Courses", real_idx)
                                    st.rerun()
                st.divider()
            else: st.info("Panier vide.")

            with st.form("form_courses", clear_on_submit=True):
                c_art = st.text_input("Article libre")
                c_qte = st.text_input("Quantité", value="1")
                c_cat = st.selectbox("Rayon", ["Fruits & Légumes", "Frais", "Boulangerie", "Supermarché", "Boissons", "Entretien", "Autre"])
                if st.form_submit_button("Ajouter") and c_art:
                    append_row_fast("Courses", [c_art, c_qte, c_cat])
                    st.rerun()

        with sub_tab4:
            st.subheader("🍽️ Planning des Repas")
            all_vals = get_data("Repas")
            repas_data = all_vals[1:] if len(all_vals) > 1 else []
            jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

            for jour in jours:
                st.markdown(f"##### 📅 {jour}")
                repas_j = [r for r in repas_data if len(r) > 0 and r[0] == jour]
                if repas_j:
                    for r in repas_j:
                        typ, plt = (r[1:] + ["", ""])[:2]
                        real_idx = all_vals.index(r)
                        c1, c2 = st.columns([4, 1])
                        with c1: st.write(f"- **{typ}** : {plt}")
                        with c2:
                            if st.button("🗑️", key=f"rep_del_{real_idx}"):
                                delete_row_fast("Repas", real_idx)
                                st.rerun()
                else: st.caption("Rien de prévu")

            st.divider()
            with st.form("form_repas", clear_on_submit=True):
                r_jour = st.selectbox("Jour", jours)
                r_type = st.radio("Repas", ["Midi", "Soir"], horizontal=True)
                r_plat = st.text_input("Plat")
                if st.form_submit_button("Ajouter au planning") and r_plat:
                    append_row_fast("Repas", [r_jour, r_type, r_plat])
                    st.rerun()

# ==========================================
# 3. BUDGET
# ==========================================
with tab_budget_adv:
    if json_str:
        st.subheader("📊 Tableau de Bord Financier")
        all_vals = get_data("Budget")
        budget_data = all_vals[1:] if len(all_vals) > 1 else []

        if budget_data:
            parsed_rows = []
            for r in budget_data:
                dt_str, pyr, lbl = (r + ["", "", ""])[:3]
                try: amt = float(r[3].replace(',', '.')) if len(r) > 3 else 0.0
                except ValueError: amt = 0.0
                cat_str = r[4] if len(r) > 4 else "Alimentation"
                parsed_rows.append({"Date": dt_str, "Payeur": pyr, "Intitulé": lbl, "Montant (€)": amt, "Catégorie": cat_str})
            
            df_budget = pd.DataFrame(parsed_rows)
            total_lucas = df_budget[df_budget["Payeur"] == "Lucas"]["Montant (€)"].sum()
            total_alex = df_budget[df_budget["Payeur"] == "Alex"]["Montant (€)"].sum()
            diff = (total_lucas - total_alex) / 2

            b1, b2 = st.columns(2)
            with b1: st.metric("Payé par Lucas", f"{total_lucas:.2f} €")
            with b2: st.metric("Payé par Alex", f"{total_alex:.2f} €")

            if diff > 0: st.success(f"👉 **Alex doit {diff:.2f} € à Lucas**")
            elif diff < 0: st.success(f"👉 **Lucas doit {abs(diff):.2f} € à Alex**")
            else: st.info("⚖️ Comptes parfaitement équilibrés !")

            st.divider()
            for idx, row in enumerate(budget_data):
                dt, pyr, lbl = (row + ["", "", ""])[:3]
                val = row[3] if len(row) > 3 else "0"
                cat = row[4] if len(row) > 4 else "Alimentation"
                real_idx = idx + 1
                c1, c2 = st.columns([4, 1])
                with c1: st.markdown(f"- **{lbl}** <span class='badge-tag'>{cat}</span> : {val} € *(par {pyr} le {dt})*", unsafe_allow_html=True)
                with c2:
                    if st.button("🗑️", key=f"adv_b_del_{real_idx}"):
                        delete_row_fast("Budget", real_idx)
                        st.rerun()
        else: st.info("Aucune dépense enregistrée.")

        st.divider()
        with st.form("form_budget_adv", clear_on_submit=True):
            b_date = st.date_input("Date", value=datetime.today())
            b_payer = st.radio("Qui a payé ?", ["Lucas", "Alex"], horizontal=True)
            b_label = st.text_input("Intitulé")
            b_cat = st.selectbox("Catégorie", ["Alimentation", "Maison/Bricolage", "Sorties", "Fixe/Admin"])
            b_amount = st.number_input("Montant (€)", min_value=0.0, step=0.5)
            if st.form_submit_button("Enregistrer la dépense") and b_label and b_amount > 0:
                append_row_fast("Budget", [str(b_date), b_payer, b_label, str(b_amount), b_cat])
                st.rerun()

# ==========================================
# 4. MAISON & LOISIRS
# ==========================================
with tab_loisirs:
    if json_str:
        sub_tab_r, sub_tab_n, sub_tab_l = st.tabs(["🍲 Recettes", "📝 Notes", "🧳 Listes & Cadeaux"])

        with sub_tab_r:
            st.subheader("🍲 Recettes de Cuisine")
            all_vals = get_data("Recettes")
            recettes_data = all_vals[1:] if len(all_vals) > 1 else []

            if recettes_data:
                for idx, row in enumerate(recettes_data):
                    titre, ing, inst = (row + ["Sans titre", "", ""])[:3]
                    real_idx = all_vals.index(row)
                    with st.expander(f"🍲 {titre}"):
                        st.markdown(f"**🛒 Ingrédients :**\n{ing}")
                        st.markdown(f"**👨‍🍳 Instructions :**\n{inst}")
                        if st.button("🗑️ Supprimer", key=f"r_del_{real_idx}"):
                            delete_row_fast("Recettes", real_idx)
                            st.rerun()
            else: st.info("Aucune recette.")

            st.divider()
            with st.form("form_recette", clear_on_submit=True):
                r_titre = st.text_input("Nom de la recette")
                r_ing = st.text_area("Ingrédients (un par ligne)")
                r_inst = st.text_area("Instructions")
                if st.form_submit_button("Enregistrer la recette") and r_titre:
                    append_row_fast("Recettes", [r_titre, r_ing, r_inst])
                    st.rerun()

        with sub_tab_n:
            st.subheader("📝 Notes Partagées")
            all_vals = get_data("Notes")
            notes_data = all_vals[1:] if len(all_vals) > 1 else []

            if notes_data:
                for idx, row in enumerate(notes_data):
                    titre, contenu = (row + ["Sans titre", ""])[:2]
                    real_idx = all_vals.index(row)
                    with st.expander(f"📌 {titre}"):
                        st.write(contenu)
                        if st.button("🗑️ Supprimer", key=f"n_del_{real_idx}"):
                            delete_row_fast("Notes", real_idx)
                            st.rerun()
            else: st.info("Aucune note.")

            st.divider()
            with st.form("form_note", clear_on_submit=True):
                n_titre = st.text_input("Titre")
                n_contenu = st.text_area("Contenu")
                if st.form_submit_button("Enregistrer la note") and n_titre:
                    append_row_fast("Notes", [n_titre, n_contenu])
                    st.rerun()

        with sub_tab_l:
            st.subheader("🧳 Listes & Cadeaux")
            all_vals = get_data("Listes")
            listes_data = all_vals[1:] if len(all_vals) > 1 else []
            cat_l = st.radio("Type", ["Idées Cadeaux", "Valise / Voyage", "Choses à acheter (Maison)"], horizontal=True)

            filtered = [l for l in listes_data if len(l) > 0 and l[0] == cat_l]
            if filtered:
                for idx, row in enumerate(filtered):
                    elm, nts = (row[1:] + ["", ""])[:2]
                    real_idx = all_vals.index(row)
                    c1, c2 = st.columns([4, 1])
                    with c1: st.markdown(f"- **{elm}** {f'(*{nts}*)' if nts else ''}")
                    with c2:
                        if st.button("🗑️", key=f"lst_del_{real_idx}"):
                            delete_row_fast("Listes", real_idx)
                            st.rerun()
            else: st.info("Rien dans cette liste.")

            st.divider()
            with st.form("form_listes", clear_on_submit=True):
                l_cat = st.selectbox("Liste", ["Idées Cadeaux", "Valise / Voyage", "Choses à acheter (Maison)"])
                l_elem = st.text_input("Élément")
                l_notes = st.text_input("Notes (optionnel)")
                if st.form_submit_button("Ajouter") and l_elem:
                    append_row_fast("Listes", [l_cat, l_elem, l_notes])
                    st.rerun()
