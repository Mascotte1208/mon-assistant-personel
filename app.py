import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Notre Assistant", 
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
        <meta name="theme-color" content="#6366f1" />
        <link rel="apple-touch-icon" href="https://img.icons8.com/emoji/192/sparkles-emoji.png" />
    </head>
""", unsafe_allow_html=True)

# --- STYLE CSS APPLI NATIVE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    /* Configuration Écran Mobile */
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        background-color: #f8fafc;
        color: #0f172a;
        -webkit-tap-highlight-color: transparent;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Centrage et marges tactiles */
    .block-container {
        padding-top: 1.2rem !important;
        padding-bottom: 4rem !important;
        max-width: 550px !important;
    }

    /* Barre d'Onglets Tactiles (PWA Bottom-Nav Style) */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #e2e8f0;
        padding: 6px;
        border-radius: 22px;
        overflow-x: auto;
        margin-bottom: 16px;
        box-shadow: inset 0 2px 4px rgba(0,0,0,0.03);
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 16px;
        padding: 10px 14px;
        font-weight: 700;
        font-size: 13px;
        color: #64748b;
        background-color: transparent;
        border: none;
        white-space: nowrap;
        transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #4f46e5 !important;
        box-shadow: 0 4px 16px rgba(79, 70, 229, 0.18);
    }

    /* Cartes Tactiles */
    .widget-card {
        background: #ffffff;
        border: 1px solid #f1f5f9;
        border-radius: 22px;
        padding: 18px;
        box-shadow: 0 10px 25px -5px rgba(0, 0, 0, 0.04);
        margin-bottom: 12px;
        transition: transform 0.15s ease, box-shadow 0.15s ease;
    }
    .widget-card:active {
        transform: scale(0.98);
        box-shadow: 0 6px 14px -5px rgba(0, 0, 0, 0.06);
    }
    .widget-title {
        font-size: 11px;
        font-weight: 800;
        color: #94a3b8;
        text-transform: uppercase;
        letter-spacing: 0.9px;
    }
    .widget-value {
        font-size: 26px;
        font-weight: 800;
        color: #0f172a;
        margin-top: 2px;
    }
    .widget-sub {
        font-size: 12px;
        font-weight: 600;
        color: #6366f1;
        margin-top: 2px;
    }

    /* Badges */
    .badge-tag {
        display: inline-block;
        padding: 3px 10px;
        border-radius: 12px;
        font-size: 11px;
        font-weight: 700;
        background-color: #e0e7ff;
        color: #4338ca;
    }

    /* Boutons Tactiles */
    .stButton button {
        border-radius: 16px;
        font-weight: 700;
        font-size: 14px;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 14px 20px;
        box-shadow: 0 4px 16px rgba(99, 102, 241, 0.28);
        transition: all 0.15s ease;
    }
    .stButton button:active {
        transform: scale(0.96);
    }

    /* Formulaires fluides sans zoom */
    .stTextInput input, .stTextArea textarea, .stSelectbox select {
        border-radius: 16px !important;
        border: 1px solid #e2e8f0 !important;
        padding: 12px 16px !important;
        font-size: 16px !important; /* Empêche le zoom auto sur iPhone */
        background-color: #ffffff !important;
    }

    .streamlit-expanderHeader {
        background-color: #ffffff !important;
        border-radius: 18px !important;
        border: 1px solid #f1f5f9 !important;
        font-weight: 700 !important;
        color: #1e293b !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.02) !important;
    }
    </style>
""", unsafe_allow_html=True)

# --- CACHE DONNÉES GOOGLE SHEETS (30 SECONDES) ---
@st.cache_data(ttl=30, show_spinner=False)
def fetch_sheet_data(json_str, sheet_name):
    try:
        creds_dict = json.loads(json_str)
        scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("MonAssistantData")
        ws = sheet.worksheet(sheet_name)
        return ws.get_all_values()
    except Exception:
        return []

def get_gspread_client(json_str):
    creds_dict = json.loads(json_str)
    scope = ["https://www.googleapis.com/auth/spreadsheets", "https://www.googleapis.com/auth/drive"]
    creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
    return gspread.authorize(creds)

# --- SESSION CONFIGURATION ---
if "json_credentials_str" not in st.session_state:
    st.session_state["json_credentials_str"] = None

# --- EN-TÊTE PRINCIPAL ---
st.markdown("<h1 style='text-align: center; font-weight: 800; color: #0f172a; margin-bottom: 0px;'>✨ Notre Espace</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; font-size: 13px; font-weight: 600; color: #64748b; margin-top: 4px; margin-bottom: 20px;'>Tableau de bord partagé — <b>Lucas & Alex</b></p>", unsafe_allow_html=True)

# --- NAVIGATION RESTRUCTURÉE (5 SUPER-ONGLETS) ---
tab_dash, tab_quotidien, tab_budget_adv, tab_pro, tab_loisirs = st.tabs([
    "🏠 Dashboard", "📋 Quotidien", "📊 Budget", "🎓 Espace Pro", "🐾 Saiko & Cuisine"
])

# ==========================================
# SUPER-ONGLET 1 : DASHBOARD VISUEL & PWA
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
        
        taches_vals = fetch_sheet_data(json_str, "Taches")
        agenda_vals = fetch_sheet_data(json_str, "Agenda")
        courses_vals = fetch_sheet_data(json_str, "Courses")
        budget_vals = fetch_sheet_data(json_str, "Budget")
        cand_vals = fetch_sheet_data(json_str, "Candidatures")
        
        taches_data = taches_vals[1:] if len(taches_vals) > 1 else []
        taches_faites = len([t for t in taches_data if len(t) > 2 and t[2] == "Fait"])
        total_taches = len(taches_data)
        
        nb_courses = max(0, len(courses_vals) - 1)
        nb_agenda = max(0, len(agenda_vals) - 1)
        nb_cand = max(0, len(cand_vals) - 1)

        st.markdown("<h4 style='font-weight: 800; color: #1e293b; margin-bottom: 12px;'>⚡ Aperçu Rapide</h4>", unsafe_allow_html=True)
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'''
                <div class="widget-card">
                    <div class="widget-title">✅ Tâches</div>
                    <div class="widget-value">{taches_faites} <span style="font-size:16px; color:#94a3b8;">/ {total_taches}</span></div>
                    <div class="widget-sub">{"🎉 À jour !" if total_taches == taches_faites and total_taches > 0 else "En cours"}</div>
                </div>
            ''', unsafe_allow_html=True)
            
            st.markdown(f'''
                <div class="widget-card">
                    <div class="widget-title">🛒 Courses</div>
                    <div class="widget-value">{nb_courses}</div>
                    <div class="widget-sub">Articles à acheter</div>
                </div>
            ''', unsafe_allow_html=True)

        with c2:
            st.markdown(f'''
                <div class="widget-card">
                    <div class="widget-title">🎓 Candidatures</div>
                    <div class="widget-value">{nb_cand}</div>
                    <div class="widget-sub">Dossiers suivis</div>
                </div>
            ''', unsafe_allow_html=True)
            
            total_lucas, total_alex = 0.0, 0.0
            for r in (budget_vals[1:] if len(budget_vals) > 1 else []):
                payer = r[1] if len(r) > 1 else ""
                try: amt = float(r[3].replace(',', '.')) if len(r) > 3 else 0.0
                except ValueError: amt = 0.0
                if payer == "Lucas": total_lucas += amt
                elif payer == "Alex": total_alex += amt
            diff = (total_lucas - total_alex) / 2
            
            st.markdown(f'''
                <div class="widget-card">
                    <div class="widget-title">💶 Équilibre</div>
                    <div class="widget-value">{abs(diff):.2f} €</div>
                    <div class="widget-sub">{"Alex ➔ Lucas" if diff > 0 else ("Lucas ➔ Alex" if diff < 0 else "Équilibré")}</div>
                </div>
            ''', unsafe_allow_html=True)

        st.divider()
        
        with st.expander("📲 **Installer sur Smartphone (Mode App)**"):
            st.markdown("""
            * **Sur iPhone (Safari) :** Appuyez sur le bouton de partage <span style='font-size:16px;'>🔗</span> puis sélectionnez **"Sur l'écran d'accueil"**.
            * **Sur Android (Chrome) :** Appuyez sur les 3 points <span style='font-size:16px;'>⋮</span> puis sélectionnez **"Installer l'application"**.
            """)

        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔄 Actualiser"):
                st.cache_data.clear()
                st.rerun()
        with col_act2:
            if st.button("🔴 Déconnexion"):
                st.session_state["json_credentials_str"] = None
                st.cache_data.clear()
                st.rerun()

json_str = st.session_state["json_credentials_str"]

# ==========================================
# SUPER-ONGLET 2 : QUOTIDIEN
# ==========================================
with tab_quotidien:
    if json_str:
        sub_tab1, sub_tab2, sub_tab3, sub_tab4 = st.tabs(["✅ Tâches", "📅 Agenda", "🛒 Courses", "🍽️ Repas"])
        
        with sub_tab1:
            st.subheader("✅ Tâches à faire")
            all_vals = fetch_sheet_data(json_str, "Taches")
            taches_data = all_vals[1:] if len(all_vals) > 1 else []
            
            total_taches = len(taches_data)
            taches_faites = len([t for t in taches_data if len(t) > 2 and t[2] == "Fait"])
            
            if total_taches > 0:
                st.progress(taches_faites / total_taches)

            cat_filter = st.selectbox("🔍 Filtrer", ["Toutes", "Maison", "Admin", "Saiko", "Urgent", "Autre"])
            filtered = [t for t in taches_data if cat_filter == "Toutes" or (len(t) > 1 and t[1] == cat_filter)]

            if filtered:
                for idx, row in enumerate(filtered):
                    nom_t = row[0] if len(row) > 0 else "Sans nom"
                    cat_t = row[1] if len(row) > 1 else "Général"
                    statut_t = row[2] if len(row) > 2 else "À faire"
                    real_idx = all_vals.index(row) + 1
                    
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        if statut_t == "Fait":
                            st.markdown(f"- ~~**{nom_t}**~~ <span class='badge-tag'>{cat_t}</span>", unsafe_allow_html=True)
                        else:
                            st.markdown(f"- **{nom_t}** <span class='badge-tag'>{cat_t}</span>", unsafe_allow_html=True)
                    with c2:
                        if statut_t != "Fait":
                            if st.button("✔️", key=f"t_fait_{idx}"):
                                get_gspread_client(json_str).open("MonAssistantData").worksheet("Taches").update_cell(real_idx, 3, "Fait")
                                st.cache_data.clear()
                                st.rerun()
                        else:
                            if st.button("🗑️", key=f"t_del_{idx}"):
                                get_gspread_client(json_str).open("MonAssistantData").worksheet("Taches").delete_rows(real_idx)
                                st.cache_data.clear()
                                st.rerun()
            else:
                st.info("Aucune tâche.")

            st.divider()
            with st.form("form_tache", clear_on_submit=True):
                st.markdown("#### ➕ Ajouter une tâche")
                n_tache = st.text_input("Intitulé")
                n_cat = st.selectbox("Catégorie", ["Maison", "Admin", "Saiko", "Urgent", "Autre"])
                if st.form_submit_button("Ajouter") and n_tache:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Taches").append_row([n_tache, n_cat, "À faire"])
                    st.cache_data.clear()
                    st.rerun()

        with sub_tab2:
            st.subheader("📅 Agenda")
            all_vals = fetch_sheet_data(json_str, "Agenda")
            events_data = all_vals[1:] if len(all_vals) > 1 else []

            if events_data:
                for idx, row in enumerate(events_data):
                    date_ev, heure_ev, titre_ev, desc_ev = (row + ["", "", "", ""])[:4]
                    real_idx = idx + 2
                    with st.expander(f"🗓️ {date_ev} {f'à {heure_ev}' if heure_ev else ''} — {titre_ev}"):
                        if desc_ev: st.write(f"**Détails :** {desc_ev}")
                        if st.button("🗑️ Supprimer", key=f"ev_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Agenda").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()
            else: st.info("Aucun événement.")

            st.divider()
            with st.form("form_agenda", clear_on_submit=True):
                st.markdown("#### ➕ Nouvel événement")
                e_date = st.date_input("Date", value=datetime.today())
                e_heure = st.time_input("Heure", value=datetime.now().time())
                e_titre = st.text_input("Titre")
                e_desc = st.text_area("Description")
                if st.form_submit_button("Enregistrer") and e_titre:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Agenda").append_row([str(e_date), str(e_heure.strftime("%H:%M")), e_titre, e_desc])
                    st.cache_data.clear()
                    st.rerun()

        with sub_tab3:
            st.subheader("🛒 Liste de Courses")
            all_vals = fetch_sheet_data(json_str, "Courses")
            courses_data = all_vals[1:] if len(all_vals) > 1 else []

            if courses_data:
                for idx, row in enumerate(courses_data):
                    art, qte, cat = (row + ["Article", "1", "Général"])[:3]
                    real_idx = idx + 2
                    c1, c2 = st.columns([3, 1])
                    with c1: st.markdown(f"- **{art}** *(Qté: {qte} | {cat})*")
                    with c2:
                        if st.button("✔️ Acquis", key=f"c_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Courses").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()
            else: st.info("Liste de courses vide.")

            st.divider()
            with st.form("form_courses", clear_on_submit=True):
                c_art = st.text_input("Article")
                c_qte = st.text_input("Quantité", value="1")
                c_cat = st.selectbox("Rayon", ["Supermarché", "Frais", "Fruits & Légumes", "Boissons", "Entretien", "Autre"])
                if st.form_submit_button("Ajouter") and c_art:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Courses").append_row([c_art, c_qte, c_cat])
                    st.cache_data.clear()
                    st.rerun()

        with sub_tab4:
            st.subheader("🍽️ Planning des Repas")
            all_vals = fetch_sheet_data(json_str, "Repas")
            repas_data = all_vals[1:] if len(all_vals) > 1 else []
            jours = ["Lundi", "Mardi", "Mercredi", "Jeudi", "Vendredi", "Samedi", "Dimanche"]

            for jour in jours:
                st.markdown(f"##### 📅 {jour}")
                repas_j = [r for r in repas_data if len(r) > 0 and r[0] == jour]
                if repas_j:
                    for r in repas_j:
                        typ, plt = (r[1:] + ["", ""])[:2]
                        real_idx = all_vals.index(r) + 1
                        c1, c2 = st.columns([4, 1])
                        with c1: st.write(f"- **{typ}** : {plt}")
                        with c2:
                            if st.button("🗑️", key=f"rep_del_{real_idx}"):
                                get_gspread_client(json_str).open("MonAssistantData").worksheet("Repas").delete_rows(real_idx)
                                st.cache_data.clear()
                                st.rerun()
                else: st.caption("Rien de prévu")

            st.divider()
            with st.form("form_repas", clear_on_submit=True):
                r_jour = st.selectbox("Jour", jours)
                r_type = st.radio("Repas", ["Midi", "Soir"], horizontal=True)
                r_plat = st.text_input("Plat")
                if st.form_submit_button("Ajouter au planning") and r_plat:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Repas").append_row([r_jour, r_type, r_plat])
                    st.cache_data.clear()
                    st.rerun()

# ==========================================
# SUPER-ONGLET 3 : BUDGET AVANCÉ
# ==========================================
with tab_budget_adv:
    if json_str:
        st.subheader("📊 Tableau de Bord Financier")
        all_vals = fetch_sheet_data(json_str, "Budget")
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
                real_idx = idx + 2
                c1, c2 = st.columns([4, 1])
                with c1: st.markdown(f"- **{lbl}** <span class='badge-tag'>{cat}</span> : {val} € *(par {pyr} le {dt})*", unsafe_allow_html=True)
                with c2:
                    if st.button("🗑️", key=f"adv_b_del_{idx}"):
                        get_gspread_client(json_str).open("MonAssistantData").worksheet("Budget").delete_rows(real_idx)
                        st.cache_data.clear()
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
                get_gspread_client(json_str).open("MonAssistantData").worksheet("Budget").append_row([str(b_date), b_payer, b_label, str(b_amount), b_cat])
                st.cache_data.clear()
                st.rerun()

# ==========================================
# SUPER-ONGLET 4 : ESPACE PRO
# ==========================================
with tab_pro:
    if json_str:
        sub_tab_c1, sub_tab_c2 = st.tabs(["📌 Suivi Dossiers", "🎯 Entretiens & Jury"])

        with sub_tab_c1:
            st.subheader("🎓 Candidatures & Formations")
            all_vals = fetch_sheet_data(json_str, "Candidatures")
            cand_data = all_vals[1:] if len(all_vals) > 1 else []

            if cand_data:
                for idx, row in enumerate(cand_data):
                    org, intit, stat, ech, nts = (row + ["Organisme", "Formation", "Dossier envoyé", "", ""])[:5]
                    real_idx = idx + 2
                    
                    with st.expander(f"🏢 [{stat}] {org} — {intit}"):
                        if ech: st.write(f"**📅 Échéance :** {ech}")
                        if nts: st.write(f"**📝 Notes :** {nts}")
                        
                        col_stat, col_del = st.columns([3, 1])
                        with col_stat:
                            new_stat = st.selectbox(
                                "Modifier le statut", 
                                ["Dossier envoyé", "Relance à faire", "Entretien prévu", "Confirmé / Admis", "Refusé"],
                                index=["Dossier envoyé", "Relance à faire", "Entretien prévu", "Confirmé / Admis", "Refusé"].index(stat) if stat in ["Dossier envoyé", "Relance à faire", "Entretien prévu", "Confirmé / Admis", "Refusé"] else 0,
                                key=f"stat_sel_{idx}"
                            )
                            if st.button("Mettre à jour", key=f"btn_up_{idx}"):
                                get_gspread_client(json_str).open("MonAssistantData").worksheet("Candidatures").update_cell(real_idx, 3, new_stat)
                                st.cache_data.clear()
                                st.rerun()
                        with col_del:
                            if st.button("🗑️ Supprimer", key=f"cand_del_{idx}"):
                                get_gspread_client(json_str).open("MonAssistantData").worksheet("Candidatures").delete_rows(real_idx)
                                st.cache_data.clear()
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
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Candidatures").append_row([c_org, c_intit, c_stat, c_ech, c_nts])
                    st.cache_data.clear()
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
            all_vals = fetch_sheet_data(json_str, "Saiko")
            saiko_data = all_vals[1:] if len(all_vals) > 1 else []

            if saiko_data:
                for idx, row in enumerate(saiko_data):
                    dt, tp, sj, nt = (row + ["", "Soin", "Remarque", ""])[:4]
                    real_idx = idx + 2
                    with st.expander(f"🐾 [{tp}] {sj} ({dt})"):
                        if nt: st.write(nt)
                        if st.button("🗑️ Supprimer", key=f"sk_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Saiko").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()

            st.divider()
            with st.form("form_saiko", clear_on_submit=True):
                s_date = st.date_input("Date", value=datetime.today())
                s_type = st.selectbox("Type", ["Vétérinaire / Vaccin", "Anti-puces / Vermifuge", "Achat Croquettes / Matériel", "Soin / Toilettage", "Autre"])
                s_sujet = st.text_input("Titre")
                s_notes = st.text_area("Notes")
                if st.form_submit_button("Enregistrer") and s_sujet:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Saiko").append_row([str(s_date), s_type, s_sujet, s_notes])
                    st.cache_data.clear()
                    st.rerun()

        with sub_tab_r:
            st.subheader("🍲 Recettes de Cuisine")
            all_vals = fetch_sheet_data(json_str, "Recettes")
            recettes_data = all_vals[1:] if len(all_vals) > 1 else []

            search_recette = st.text_input("🔍 Rechercher une recette...", placeholder="Nom ou ingrédient...")
            filtered = [r for r in recettes_data if search_recette.lower() in " ".join(r).lower()] if search_recette else recettes_data

            if filtered:
                for idx, row in enumerate(filtered):
                    titre, ing, inst = (row + ["Sans titre", "", ""])[:3]
                    real_idx = all_vals.index(row) + 1
                    with st.expander(f"🍲 {titre}"):
                        st.markdown(f"**🛒 Ingrédients :**\n{ing}")
                        st.markdown(f"**👨‍🍳 Instructions :**\n{inst}")
                        
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("🛒 Envoyer aux courses", key=f"r_send_{idx}"):
                                client = get_gspread_client(json_str)
                                courses_ws = client.open("MonAssistantData").worksheet("Courses")
                                for line in [l.strip() for l in ing.split('\n') if l.strip()]:
                                    courses_ws.append_row([line, "1", f"Recette: {titre}"])
                                st.cache_data.clear()
                                st.success("Ingrédients ajoutés aux courses !")
                                st.rerun()
                        with col2:
                            if st.button("🗑️ Supprimer", key=f"r_del_{idx}"):
                                get_gspread_client(json_str).open("MonAssistantData").worksheet("Recettes").delete_rows(real_idx)
                                st.cache_data.clear()
                                st.rerun()

            st.divider()
            with st.form("form_recette", clear_on_submit=True):
                r_titre = st.text_input("Nom de la recette")
                r_ing = st.text_area("Ingrédients (un par ligne)")
                r_inst = st.text_area("Instructions")
                if st.form_submit_button("Enregistrer la recette") and r_titre:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Recettes").append_row([r_titre, r_ing, r_inst])
                    st.cache_data.clear()
                    st.rerun()

        with sub_tab_n:
            st.subheader("📝 Notes Partagées")
            all_vals = fetch_sheet_data(json_str, "Notes")
            notes_data = all_vals[1:] if len(all_vals) > 1 else []

            search_note = st.text_input("🔍 Rechercher...", placeholder="Mot-clé...")
            filtered = [n for n in notes_data if search_note.lower() in " ".join(n).lower()] if search_note else notes_data

            if filtered:
                for idx, row in enumerate(filtered):
                    titre, contenu = (row + ["Sans titre", ""])[:2]
                    real_idx = all_vals.index(row) + 1
                    with st.expander(f"📌 {titre}"):
                        st.write(contenu)
                        if st.button("🗑️ Supprimer", key=f"n_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Notes").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()

            st.divider()
            with st.form("form_note", clear_on_submit=True):
                n_titre = st.text_input("Titre")
                n_contenu = st.text_area("Contenu")
                if st.form_submit_button("Enregistrer la note") and n_titre:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Notes").append_row([n_titre, n_contenu])
                    st.cache_data.clear()
                    st.rerun()

        with sub_tab_a:
            st.subheader("🏡 Logement & Admin")
            all_vals = fetch_sheet_data(json_str, "Admin")
            admin_data = all_vals[1:] if len(all_vals) > 1 else []

            if admin_data:
                for idx, row in enumerate(admin_data):
                    sj, ec, dt = (row + ["Sujet", "", ""])[:3]
                    real_idx = idx + 2
                    with st.expander(f"📋 {sj} {f'(Échéance : {ec})' if ec else ''}"):
                        if dt: st.write(dt)
                        if st.button("🗑️ Supprimer", key=f"adm_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Admin").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()

            st.divider()
            with st.form("form_admin", clear_on_submit=True):
                a_sujet = st.text_input("Sujet")
                a_echeance = st.text_input("Échéance / Date")
                a_details = st.text_area("Détails")
                if st.form_submit_button("Enregistrer") and a_sujet:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Admin").append_row([a_sujet, a_echeance, a_details])
                    st.cache_data.clear()
                    st.rerun()

        with sub_tab_l:
            st.subheader("🧳 Listes & Cadeaux")
            all_vals = fetch_sheet_data(json_str, "Listes")
            listes_data = all_vals[1:] if len(all_vals) > 1 else []
            cat_l = st.radio("Type", ["Idées Cadeaux", "Valise / Voyage", "Choses à acheter (Maison)"], horizontal=True)

            filtered = [l for l in listes_data if len(l) > 0 and l[0] == cat_l]
            if filtered:
                for idx, row in enumerate(filtered):
                    elm, nts = (row[1:] + ["", ""])[:2]
                    real_idx = all_vals.index(row) + 1
                    c1, c2 = st.columns([4, 1])
                    with c1: st.markdown(f"- **{elm}** {f'(*{nts}*)' if nts else ''}")
                    with c2:
                        if st.button("🗑️", key=f"lst_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Listes").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()

            st.divider()
            with st.form("form_listes", clear_on_submit=True):
                l_cat = st.selectbox("Liste", ["Idées Cadeaux", "Valise / Voyage", "Choses à acheter (Maison)"])
                l_elem = st.text_input("Élément")
                l_notes = st.text_input("Notes (optionnel)")
                if st.form_submit_button("Ajouter") and l_elem:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Listes").append_row([l_cat, l_elem, l_notes])
                    st.cache_data.clear()
                    st.rerun()
