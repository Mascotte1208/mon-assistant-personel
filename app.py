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

    /* Hero Banner Gradient Indigo & Violet Royal */
    .hero-banner {
        background: linear-gradient(135deg, #3730a3 0%, #5b21b6 50%, #831843 100%);
        border-radius: 28px;
        padding: 24px 22px;
        color: white;
        margin-bottom: 22px;
        box-shadow: 0 16px 32px -8px rgba(55, 48, 163, 0.28);
        position: relative;
        overflow: hidden;
    }
    .hero-banner::after {
        content: "✨";
        position: absolute;
        right: -10px;
        bottom: -15px;
        font-size: 85px;
        opacity: 0.12;
    }
    .hero-title {
        font-size: 24px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
    }
    .hero-sub {
        font-size: 13px;
        opacity: 0.92;
        margin-top: 5px;
        font-weight: 600;
    }

    /* WIDGET CALENDRIER EN BLOCS EN BOIS */
    .wooden-block-calendar {
        background: linear-gradient(145deg, #2d241e, #1a1512);
        border: 2px solid #524136;
        border-radius: 24px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 14px 28px rgba(0,0,0,0.25);
        margin-bottom: 20px;
    }
    .block-month {
        font-size: 14px;
        font-weight: 800;
        color: #f59e0b;
        text-transform: uppercase;
        letter-spacing: 2px;
        margin-bottom: 10px;
    }
    .block-cubes {
        display: flex;
        justify-content: center;
        gap: 12px;
        margin-bottom: 12px;
    }
    .block-cube {
        background: linear-gradient(135deg, #ffffff 0%, #e2e8f0 100%);
        color: #1e293b;
        font-size: 38px;
        font-weight: 800;
        width: 65px;
        height: 70px;
        line-height: 70px;
        border-radius: 16px;
        box-shadow: inset 0 -4px 0 rgba(0,0,0,0.15), 0 6px 12px rgba(0,0,0,0.3);
    }
    .block-dayname {
        font-size: 13px;
        font-weight: 700;
        color: #e2e8f0;
        background: rgba(255,255,255,0.1);
        padding: 6px 14px;
        border-radius: 12px;
        display: inline-block;
    }

    /* Navigation Onglets Flottante */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: rgba(229, 229, 224, 0.8);
        backdrop-filter: blur(10px);
        padding: 6px;
        border-radius: 24px;
        overflow-x: auto;
        margin-bottom: 20px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.02);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 18px;
        padding: 10px 16px;
        font-weight: 700;
        font-size: 13px;
        color: #78716c;
        background-color: transparent;
        border: none;
        white-space: nowrap;
        transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #3730a3 !important;
        box-shadow: 0 6px 18px rgba(55, 48, 163, 0.15);
    }

    /* Cartes Glassmorphism */
    .glass-card-purple {
        background: #ffffff;
        border: 1px solid #e0e7ff;
        border-top: 4px solid #4338ca;
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 10px 25px -5px rgba(28, 25, 23, 0.04);
        margin-bottom: 12px;
    }
    .glass-card-emerald {
        background: #ffffff;
        border: 1px solid #d1fae5;
        border-top: 4px solid #059669;
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 10px 25px -5px rgba(28, 25, 23, 0.04);
        margin-bottom: 12px;
    }
    .glass-card-amber {
        background: #ffffff;
        border: 1px solid #fef3c7;
        border-top: 4px solid #d97706;
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 10px 25px -5px rgba(28, 25, 23, 0.04);
        margin-bottom: 12px;
    }
    .glass-card-sky {
        background: #ffffff;
        border: 1px solid #e0f2fe;
        border-top: 4px solid #0284c7;
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 10px 25px -5px rgba(28, 25, 23, 0.04);
        margin-bottom: 12px;
    }

    .card-head {
        font-size: 11px;
        font-weight: 800;
        color: #78716c;
        text-transform: uppercase;
        letter-spacing: 0.9px;
    }
    .card-num {
        font-size: 28px;
        font-weight: 800;
        color: #1c1917;
        margin-top: 2px;
    }
    .card-foot {
        font-size: 12px;
        font-weight: 600;
        color: #4338ca;
        margin-top: 4px;
    }

    .badge-tag {
        display: inline-block;
        padding: 4px 12px;
        border-radius: 14px;
        font-size: 11px;
        font-weight: 700;
        background-color: #e0e7ff;
        color: #3730a3;
    }

    /* Boutons Gradient Pill */
    .stButton button {
        border-radius: 18px;
        font-weight: 800;
        font-size: 14px;
        background: linear-gradient(135deg, #4338ca 0%, #3730a3 100%);
        color: white;
        border: none;
        padding: 14px 22px;
        box-shadow: 0 6px 18px rgba(67, 56, 202, 0.25);
        transition: all 0.2s ease;
    }
    .stButton button:active {
        transform: scale(0.97);
    }

    /* Inputs Visibilité & Focus */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        color: #1c1917 !important;
        background-color: #ffffff !important;
        -webkit-text-fill-color: #1c1917 !important;
        border-radius: 18px !important;
        border: 1.5px solid #d6d3d1 !important;
        padding: 12px 16px !important;
        font-size: 16px !important;
    }
    .stTextInput input:focus, .stTextArea textarea:focus {
        border-color: #4338ca !important;
        box-shadow: 0 0 0 4px rgba(67, 56, 202, 0.12) !important;
    }

    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        border-radius: 20px !important;
        border: 1px solid #e7e5e4 !important;
        font-weight: 700 !important;
        color: #1c1917 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.02) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- FONCTIONS CACHE MÉMOIRE OPTIMISTIC ---
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

# --- SESSION CONFIGURATION ---
if "json_credentials_str" not in st.session_state:
    st.session_state["json_credentials_str"] = None

# --- HERO BANNER ---
st.markdown("""
    <div class="hero-banner">
        <div class="hero-title">Bonjour Lucas & Alex 👋</div>
        <div class="hero-sub">Espace partagé & assistant quotidien</div>
    </div>
""", unsafe_allow_html=True)

# --- WIDGET CALENDRIER EN BLOCS EN BOIS DU JOUR ---
today = date.today()
mois_fr = ["JANVIER", "FÉVRIER", "MARS", "AVRIL", "MAI", "JUIN", "JUILLET", "AOÛT", "SEPTEMBRE", "OCTOBRE", "NOVEMBRE", "DÉCEMBRE"]
jours_fr = ["LUNDI", "MARDI", "MERCREDI", "JEUDI", "VENDREDI", "SAMEDI", "DIMANCHE"]

day_str = f"{today.day:02d}"
cube1, cube2 = day_str[0], day_str[1]
month_str = mois_fr[today.month - 1]
day_name_str = jours_fr[today.weekday()]

st.markdown(f"""
    <div class="wooden-block-calendar">
        <div class="block-month">📅 {month_str}</div>
        <div class="block-cubes">
            <div class="block-cube">{cube1}</div>
            <div class="block-cube">{cube2}</div>
        </div>
        <div class="block-dayname">{day_name_str}</div>
    </div>
""", unsafe_allow_html=True)

# --- NAVIGATION RESTRUCTURÉE ---
tab_dash, tab_quotidien, tab_budget_adv, tab_pro, tab_loisirs = st.tabs([
    "🏠 Dashboard", "📋 Quotidien", "📊 Budget", "🎓 Espace Pro", "🐾 Saiko & Cuisine"
])

# ==========================================
# SUPER-ONGLET 1 : DASHBOARD DESIGN
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
                    ("Saiko", [['Date', 'Type', 'Sujet', 'Notes']]),
                    ("Budget", [['Date', 'Payé Par', 'Intitulé', 'Montant', 'Catégorie']]),
                    ("Repas", [['Jour', 'Repas', 'Plat']]),
                    ("Admin", [['Sujet', 'Echéance', 'Détails']]),
                    ("Listes", [['Catégorie', 'Élément', 'Notes']]),
                    ("Candidatures", [['Organisme', 'Intitulé', 'Statut', 'Date Échéance', 'Notes / Contacts']])
                ]:
                    doc.add_worksheet(title=ws_title, rows="100", cols="20")
                    doc.values_append(ws_title, {'valueInputOption': 'RAW'}, {'values': headers})
            
            st.success("Connexion réussie !")
            st.rerun()
    else:
        json_str = st.session_state["json_credentials_str"]
        
        taches_vals = get_data("Taches")
        agenda_vals = get_data("Agenda")
        courses_vals = get_data("Courses")
        budget_vals = get_data("Budget")
        cand_vals = get_data("Candidatures")
        
        taches_data = taches_vals[1:] if len(taches_vals) > 1 else []
        taches_faites = len([t for t in taches_data if len(t) > 2 and t[2] == "Fait"])
        total_taches = len(taches_data)
        
        nb_courses = max(0, len(courses_vals) - 1)
        nb_cand = max(0, len(cand_vals) - 1)

        # Calcul budget
        total_lucas, total_alex = 0.0, 0.0
        for r in (budget_vals[1:] if len(budget_vals) > 1 else []):
            payer = r[1] if len(r) > 1 else ""
            try: amt = float(r[3].replace(',', '.')) if len(r) > 3 else 0.0
            except ValueError: amt = 0.0
            if payer == "Lucas": total_lucas += amt
            elif payer == "Alex": total_alex += amt
        diff = (total_lucas - total_alex) / 2

        st.markdown("<h4 style='font-weight: 800; color: #1c1917; margin-bottom: 14px;'>📊 Métriques de l'assistant</h4>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'''
                <div class="glass-card-purple">
                    <div class="card-head">✅ Tâches accomplies</div>
                    <div class="card-num">{taches_faites} <span style="font-size:15px; color:#a8a29e;">/ {total_taches}</span></div>
                    <div class="card-foot">{"🎉 Tout est à jour !" if total_taches == taches_faites and total_taches > 0 else "Actions en cours"}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            st.markdown(f'''
                <div class="glass-card-amber">
                    <div class="card-head">🛒 En liste de courses</div>
                    <div class="card-num">{nb_courses}</div>
                    <div class="card-foot">Articles à acheter</div>
                </div>
            ''', unsafe_allow_html=True)

        with c2:
            st.markdown(f'''
                <div class="glass-card-emerald">
                    <div class="card-head">💶 Équilibre Budget</div>
                    <div class="card-num">{abs(diff):.2f} €</div>
                    <div class="card-foot">{"Alex ➔ Lucas" if diff > 0 else ("Lucas ➔ Alex" if diff < 0 else "Comptes équilibrés")}</div>
                </div>
            ''', unsafe_allow_html=True)

            st.markdown(f'''
                <div class="glass-card-sky">
                    <div class="card-head">🎓 Formations & Pro</div>
                    <div class="card-num">{nb_cand}</div>
                    <div class="card-foot">Dossiers suivis</div>
                </div>
            ''', unsafe_allow_html=True)

        st.divider()
        st.markdown("<h4 style='font-weight: 800; color: #1c1917; margin-bottom: 10px;'>🗓️ Prochains Événements</h4>", unsafe_allow_html=True)
        agenda_data = agenda_vals[1:] if len(agenda_vals) > 1 else []
        if agenda_data:
            for ev in agenda_data[:3]:
                dt_e, hr_e, tit_e = (ev + ["", "", ""])[:3]
                st.markdown(f"📌 **{dt_e}** {f'à {hr_e}' if hr_e else ''} — **{tit_e}**")
        else:
            st.info("Aucun événement prévu.")

        st.divider()
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔄 Re-synchroniser"):
                for key in list(st.session_state.keys()):
                    if key.startswith("data_"):
                        del st.session_state[key]
                st.rerun()
        with col_act2:
            if st.button("🔴 Déconnexion"):
                st.session_state["json_credentials_str"] = None
                for key in list(st.session_state.keys()):
                    if key.startswith("data_"):
                        del st.session_state[key]
                st.rerun()

json_str = st.session_state["json_credentials_str"]

# ==========================================
# SUPER-ONGLET 2 : QUOTIDIEN
# ==========================================
with tab_quotidien:
    if json_str:
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["✅ Tâches", "📅 Agenda & Vue Mois", "🛒 Courses", "🍽️ Repas"])
        
        with sub_tab1:
            st.subheader("✅ Tâches à faire")
            all_vals = get_data("Taches")
            taches_data = all_vals[1:] if len(all_vals) > 1 else []
            
            total_taches = len(taches_data)
            taches_faites = len([t for t in taches_data if len(t) > 2 and t[2] == "Fait"])
            
            if total_taches > 0:
                st.progress(taches_faites / total_taches)

            cat_filter = st.selectbox("🔍 Filtrer par catégorie", ["Toutes", "Maison", "Admin", "Saiko", "Urgent", "Autre"])
            filtered = [t for t in taches_data if cat_filter == "Toutes" or (len(t) > 1 and t[1] == cat_filter)]

            if filtered:
                for idx, row in enumerate(filtered):
                    nom_t = row[0] if len(row) > 0 else "Sans nom"
                    cat_t = row[1] if len(row) > 1 else "Général"
                    statut_t = row[2] if len(row) > 2 else "À faire"
                    real_idx = all_vals.index(row)
                    
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        if statut_t == "Fait":
                            st.markdown(f"- ~~**{nom_t}**~~ <span class='badge-tag'>{cat_t}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"- **{nom_t}** <span class='badge-tag'>{cat_t}</span>", unsafe_allow_html=True)
                    with c2:
                        if statut_t != "Fait":
                            if st.button("✔️", key=f"t_fait_{real_idx}"):
                                update_cell_fast("Taches", real_idx, 3, "Fait")
                                st.rerun()
                        else:
                            if st.button("🗑️", key=f"t_del_{real_idx}"):
                                delete_row_fast("Taches", real_idx)
                                st.rerun()
            else:
                st.info("Aucune tâche.")

            st.divider()
            with st.form("form_tache", clear_on_submit=True):
                st.markdown("#### ➕ Ajouter une tâche")
                n_tache = st.text_input("Intitulé")
                n_cat = st.selectbox("Catégorie", ["Maison", "Admin", "Saiko", "Urgent", "Autre"])
                if st.form_submit_button("Ajouter") and n_tache:
                    append_row_fast("Taches", [n_tache, n_cat, "À faire"])
                    st.rerun()

        with sub_tab2:
            st.subheader("📅 Agenda & Vue Mois")
            
            # --- INDEXATION DES ÉVÉNEMENTS ---
            all_agenda_vals = get_data("Agenda")
            agenda_events_data = all_agenda_vals[1:] if len(all_agenda_vals) > 1 else []
            
            events_by_date = {}
            for ev in agenda_events_data:
                if len(ev) > 0 and ev[0]:
                    d_key = ev[0].strip()
                    titre_ev = ev[2] if len(ev) > 2 else "Événement"
                    if d_key not in events_by_date:
                        events_by_date[d_key] = []
                    events_by_date[d_key].append(titre_ev)

            # --- VUE CALENDRIER DU MOIS COMPLÈTEMENT LISIBLE SUR MOBILE ---
            st.markdown(f"#### 🗓️ Calendrier - {mois_fr[today.month - 1]} {today.year}")
            
            num_days = calendar.monthrange(today.year, today.month)[1]
            
            # Affichage en blocs élégants pour chaque jour du mois
            for day_num in range(1, num_days + 1):
                d_str = f"{today.year}-{today.month:02d}-{day_num:02d}"
                is_today = day_num == today.day
                has_events = d_str in events_by_date
                
                # Style de la ligne du jour
                day_bg = "#e0e7ff" if is_today else ("#ffffff" if has_events else "#fafaf9")
                border_col = "#4338ca" if is_today else ("#cbd5e1" if has_events else "#e7e5e4")
                
                evs_html = ""
                if has_events:
                    evs_html = "<br>".join([f"<span style='color:#4338ca; font-weight:700; font-size:13px;'>• {t}</span>" for t in events_by_date[d_str]])
                else:
                    evs_html = "<span style='color:#a8a29e; font-size:12px;'>Rien de prévu</span>"
                
                today_badge = " ⭐ (Aujourd'hui)" if is_today else ""
                
                st.markdown(f"""
                    <div style="background:{day_bg}; border: 1.5px solid {border_col}; border-radius: 14px; padding: 10px 14px; margin-bottom: 8px;">
                        <div style="font-weight: 800; font-size: 13px; color: #1c1917; margin-bottom: 2px;">Jour {day_num}{today_badge}</div>
                        <div>{evs_html}</div>
                    </div>
                """, unsafe_allow_html=True)

            st.divider()

            if agenda_events_data:
                for idx, row in enumerate(agenda_events_data):
                    date_ev, heure_ev, titre_ev, desc_ev = (row + ["", "", "", ""])[:4]
                    real_idx = idx + 1
                    with st.expander(f"🗓️ {date_ev} {f'à {heure_ev}' if heure_ev else ''} — {titre_ev}"):
                        if desc_ev: st.write(f"**Détails :** {desc_ev}")
                        if st.button("🗑️ Supprimer", key=f"ev_del_{real_idx}"):
                            delete_row_fast("Agenda", real_idx)
                            st.rerun()
            else: st.info("Aucun événement dans la base.")

            st.divider()
            with st.form("form_agenda", clear_on_submit=True):
                st.markdown("#### ➕ Nouvel événement")
                e_date = st.date_input("Date", value=datetime.today())
                e_heure = st.time_input("Heure", value=datetime.now().time())
                e_titre = st.text_input("Titre")
                e_desc = st.text_area("Description")
                if st.form_submit_button("Enregistrer") and e_titre:
                    append_row_fast("Agenda", [str(e_date), str(e_heure.strftime("%H:%M")), e_titre, e_desc])
                    st.rerun()

        with sub_tab3:
            st.subheader("🛒 Liste de Courses")
            all_vals = get_data("Courses")
            courses_data = all_vals[1:] if len(all_vals) > 1 else []

            if courses_data:
                for idx, row in enumerate(courses_data):
                    art, qte, cat = (row + ["Article", "1", "Général"])[:3]
                    real_idx = idx + 1
                    c1, c2 = st.columns([3, 1])
                    with c1: st.markdown(f"- **{art}** *(Qté: {qte} | {cat})*")
                    with c2:
                        if st.button("✔️ Acquis", key=f"c_del_{real_idx}"):
                            delete_row_fast("Courses", real_idx)
                            st.rerun()
            else: st.info("Liste de courses vide.")

            st.divider()
            with st.form("form_courses", clear_on_submit=True):
                c_art = st.text_input("Article")
                c_qte = st.text_input("Quantité", value="1")
                c_cat = st.selectbox("Rayon", ["Supermarché", "Frais", "Fruits & Légumes", "Boissons", "Entretien", "Autre"])
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
# SUPER-ONGLET 3 : BUDGET AVANCÉ
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
                amt_str = r[3] if len(r) > 3 else "0"
                cat_str = r[4] if len(r) > 4 else "Alimentation"
                try: amt = float(amt_str.replace(',', '.'))
                except ValueError: amt = 0.0
                
                parsed_rows.append({
                    "Date": dt_str,
                    "Payeur": pyr,
                    "Intitulé": lbl,
                    "Montant (€)": amt,
                    "Catégorie": cat_str if cat_str else "Alimentation"
                })
            
            df_budget = pd.DataFrame(parsed_rows)
            
            st.markdown("#### 🏷️ Ventilation par Catégorie")
            df_cat = df_budget.groupby("Catégorie")["Montant (€)"].sum().reset_index()
            st.bar_chart(df_cat, x="Catégorie", y="Montant (€)")

            st.markdown("#### ⚖️ Bilan Équilibré")
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
            csv_buffer = df_budget.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="📄 Exporter en CSV / Excel",
                data=csv_buffer,
                file_name=f"recapitulatif_budget_{datetime.now().strftime('%Y_%m')}.csv",
                mime="text/csv"
            )

            st.divider()
            st.markdown("#### 📜 Historique des dépenses")
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
        else:
            st.info("Aucune dépense enregistrée.")

        st.divider()
        with st.form("form_budget_adv", clear_on_submit=True):
            st.markdown("#### ➕ Saisir une dépense")
            b_date = st.date_input("Date", value=datetime.today())
            b_payer = st.radio("Qui a payé ?", ["Lucas", "Alex"], horizontal=True)
            b_label = st.text_input("Intitulé")
            b_cat = st.selectbox("Catégorie", ["Alimentation", "Saiko", "Maison/Bricolage", "Sorties", "Fixe/Admin"])
            b_amount = st.number_input("Montant (€)", min_value=0.0, step=0.5)
            if st.form_submit_button("Enregistrer la dépense") and b_label and b_amount > 0:
                append_row_fast("Budget", [str(b_date), b_payer, b_label, str(b_amount), b_cat])
                st.rerun()

# ==========================================
# SUPER-ONGLET 4 : ESPACE PRO
# ==========================================
with tab_pro:
    if json_str:
        sub_tab_c1, sub_tab_c2 = st.tabs(["📌 Suivi Dossiers", "🎯 Entretiens & Jury"])

        with sub_tab_c1:
            st.subheader("🎓 Candidatures & Formations")
            all_vals = get_data("Candidatures")
            cand_data = all_vals[1:] if len(all_vals) > 1 else []

            if cand_data:
                for idx, row in enumerate(cand_data):
                    org, intit, stat, ech, nts = (row + ["Organisme", "Formation", "Dossier envoyé", "", ""])[:5]
                    real_idx = idx + 1
                    
                    with st.expander(f"🏢 [{stat}] {org} — {intit}"):
                        if ech: st.write(f"**📅 Échéance :** {ech}")
                        if nts: st.write(f"**📝 Notes :** {nts}")
                        
                        col_stat, col_del = st.columns([3, 1])
                        with col_stat:
                            new_stat = st.selectbox(
                                "Modifier le statut", 
                                ["Dossier envoyé", "Relance à faire", "Entretien prévu", "Confirmé / Admis", "Refusé"],
                                index=["Dossier envoyé", "Relance à faire", "Entretien prévu", "Confirmé / Admis", "Refusé"].index(stat) if stat in ["Dossier envoyé", "Relance à faire", "Entretien prévu", "Confirmé / Admis", "Refusé"] else 0,
                                key=f"stat_sel_{real_idx}"
                            )
                            if st.button("Mettre à jour", key=f"btn_up_{real_idx}"):
                                update_cell_fast("Candidatures", real_idx, 3, new_stat)
                                st.rerun()
                        with col_del:
                            if st.button("🗑️ Supprimer", key=f"cand_del_{real_idx}"):
                                delete_row_fast("Candidatures", real_idx)
                                st.rerun()
            else:
                st.info("Aucun dossier enregistré.")

            st.divider()
            with st.form("form_cand", clear_on_submit=True):
                st.markdown("#### ➕ Ajouter une candidature")
                c_org = st.text_input("Organisme (ex: efp, BF technics...)")
                c_intit = st.text_input("Formation (ex: Électricien, Frigoriste...)")
                c_stat = st.selectbox("Statut initial", ["Dossier envoyé", "Relance à faire", "Entretien prévu", "Confirmé / Admis"])
                c_ech = st.text_input("Échéance / RDV")
                c_nts = st.text_area("Notes & pièces à fournir")
                if st.form_submit_button("Enregistrer") and c_org:
                    append_row_fast("Candidatures", [c_org, c_intit, c_stat, c_ech, c_nts])
                    st.rerun()

        with sub_tab_c2:
            st.subheader("🎯 Préparation Jury & Entretien")
            with st.expander("💡 **Fiche Projet : Électricité & Frigoriste**", expanded=True):
                st.markdown("""
                * **Synergie :** Argumenter sur la complémentarité entre la formation d'électricien et le métier de frigoriste.
                * **Atouts :** Rigueur, méthode et vision globale des installations techniques.
                * **Checklist :** CV à jour, lettre de motivation préparée et convention de stage signée.
                """)

# ==========================================
# SUPER-ONGLET 5 : SAIKO & CUISINE
# ==========================================
with tab_loisirs:
    if json_str:
        sub_tab_s, sub_tab_r, sub_tab_n, sub_tab_a, sub_tab_l = st.tabs(["🐶 Saiko", "🍲 Recettes", "📝 Notes", "🏡 Admin", "🧳 Listes"])

        with sub_tab_s:
            st.subheader("🐶 Espace Saiko")
            all_vals = get_data("Saiko")
            saiko_data = all_vals[1:] if len(all_vals) > 1 else []

            if saiko_data:
                for idx, row in enumerate(saiko_data):
                    dt, tp, sj, nt = (row + ["", "Soin", "Remarque", ""])[:4]
                    real_idx = idx + 1
                    with st.expander(f"🐾 [{tp}] {sj} ({dt})"):
                        if nt: st.write(nt)
                        if st.button("🗑️ Supprimer", key=f"sk_del_{real_idx}"):
                            delete_row_fast("Saiko", real_idx)
                            st.rerun()

            st.divider()
            with st.form("form_saiko", clear_on_submit=True):
                s_date = st.date_input("Date", value=datetime.today())
                s_type = st.selectbox("Type", ["Vétérinaire / Vaccin", "Anti-puces / Vermifuge", "Achat Croquettes / Matériel", "Soin / Toilettage", "Autre"])
                s_sujet = st.text_input("Titre")
                s_notes = st.text_area("Notes")
                if st.form_submit_button("Enregistrer") and s_sujet:
                    append_row_fast("Saiko", [str(s_date), s_type, s_sujet, s_notes])
                    st.rerun()

        with sub_tab_r:
            st.subheader("🍲 Recettes de Cuisine")
            all_vals = get_data("Recettes")
            recettes_data = all_vals[1:] if len(all_vals) > 1 else []

            search_recette = st.text_input("🔍 Rechercher une recette...", placeholder="Nom ou ingrédient...")
            filtered = [r for r in recettes_data if search_recette.lower() in " ".join(r).lower()] if search_recette else recettes_data

            if filtered:
                for idx, row in enumerate(filtered):
                    titre, ing, inst = (row + ["Sans titre", "", ""])[:3]
                    real_idx = all_vals.index(row)
                    with st.expander(f"🍲 {titre}"):
                        st.markdown(f"**🛒 Ingrédients :**\n{ing}")
                        st.markdown(f"**👨‍🍳 Instructions :**\n{inst}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🛒 Envoyer aux courses", key=f"r_send_{real_idx}"):
                                for line in [l.strip() for l in ing.split('\n') if l.strip()]:
                                    append_row_fast("Courses", [line, "1", f"Recette: {titre}"])
                                st.success("Ingrédients ajoutés aux courses !")
                                st.rerun()
                        with col2:
                            if st.button("🗑️ Supprimer", key=f"r_del_{real_idx}"):
                                delete_row_fast("Recettes", real_idx)
                                st.rerun()

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

            search_note = st.text_input("🔍 Rechercher...", placeholder="Mot-clé...")
            filtered = [n for n in notes_data if search_note.lower() in " ".join(n).lower()] if search_note else notes_data

            if filtered:
                for idx, row in enumerate(filtered):
                    titre, contenu = (row + ["Sans titre", ""])[:2]
                    real_idx = all_vals.index(row)
                    with st.expander(f"📌 {titre}"):
                        st.write(contenu)
                        if st.button("🗑️ Supprimer", key=f"n_del_{real_idx}"):
                            delete_row_fast("Notes", real_idx)
                            st.rerun()

            st.divider()
            with st.form("form_note", clear_on_submit=True):
                n_titre = st.text_input("Titre")
                n_contenu = st.text_area("Contenu")
                if st.form_submit_button("Enregistrer la note") and n_titre:
                    append_row_fast("Notes", [n_titre, n_contenu])
                    st.rerun()

        with sub_tab_a:
            st.subheader("🏡 Logement & Admin")
            all_vals = get_data("Admin")
            admin_data = all_vals[1:] if len(all_vals) > 1 else []

            if admin_data:
                for idx, row in enumerate(admin_data):
                    sj, ec, dt = (row + ["Sujet", "", ""])[:3]
                    real_idx = idx + 1
                    with st.expander(f"📋 {sj} {f'(Échéance : {ec})' if ec else ''}"):
                        if dt: st.write(dt)
                        if st.button("🗑️ Supprimer", key=f"adm_del_{real_idx}"):
                            delete_row_fast("Admin", real_idx)
                            st.rerun()

            st.divider()
            with st.form("form_admin", clear_on_submit=True):
                a_sujet = st.text_input("Sujet")
                a_echeance = st.text_input("Échéance / Date")
                a_details = st.text_area("Détails")
                if st.form_submit_button("Enregistrer") and a_sujet:
                    append_row_fast("Admin", [a_sujet, a_echeance, a_details])
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

            st.divider()
            with st.form("form_listes", clear_on_submit=True):
                l_cat = st.selectbox("Liste", ["Idées Cadeaux", "Valise / Voyage", "Choses à acheter (Maison)"])
                l_elem = st.text_input("Élément")
                l_notes = st.text_input("Notes (optionnel)")
                if st.form_submit_button("Ajouter") and l_elem:
                    append_row_fast("Listes", [l_cat, l_elem, l_notes])
                    st.rerun()
