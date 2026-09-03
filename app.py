import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json
from datetime import datetime

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Notre Assistant Partagé", 
    page_icon="✨", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS DESIGN & ERGONOMIQUE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
        background-color: #f8fafc;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Style des Onglets Principaux */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #e2e8f0;
        padding: 6px;
        border-radius: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 10px 14px;
        font-weight: 700;
        font-size: 14px;
        color: #475569;
        background-color: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #4f46e5 !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
    }

    /* Style des cartes du Dashboard */
    .dashboard-card {
        background: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 18px;
        padding: 16px;
        text-align: center;
        box-shadow: 0 4px 12px rgba(0,0,0,0.03);
        margin-bottom: 12px;
    }
    .card-title {
        font-size: 12px;
        font-weight: 700;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .card-value {
        font-size: 26px;
        font-weight: 800;
        color: #4f46e5;
        margin-top: 4px;
    }

    /* Boutons modernisés */
    .stButton button {
        border-radius: 12px;
        font-weight: 700;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 10px 16px;
        box-shadow: 0 4px 12px rgba(99, 102, 241, 0.2);
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
st.markdown("# ✨ Notre Assistant")
st.caption("Espace personnel partagé — Lucas & Alex 🚀")

# --- NAVIGATION RESTRUCTURÉE (4 GRANDS GROUPES) ---
tab_dash, tab_quotidien, tab_vie_a_deux, tab_loisirs = st.tabs([
    "🏠 Dashboard", "📋 Quotidien", "💡 Vie à Deux", "🐾 Saiko & Cuisine"
])

# ==========================================
# SUPER-ONGLET 1 : DASHBOARD VISUEL
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
                    ("Budget", [['Date', 'Payé Par', 'Intitulé', 'Montant']]),
                    ("Repas", [['Jour', 'Repas', 'Plat']]),
                    ("Admin", [['Sujet', 'Echéance', 'Détails']]),
                    ("Listes", [['Catégorie', 'Élément', 'Notes']])
                ]:
                    doc.add_worksheet(title=ws_title, rows="100", cols="20")
                    doc.values_append(ws_title, {'valueInputOption': 'RAW'}, {'values': headers})
            
            st.success("Connexion réussie !")
            st.rerun()
    else:
        json_str = st.session_state["json_credentials_str"]
        
        # Récupération rapide du nombre d'éléments pour les cartes
        taches_vals = fetch_sheet_data(json_str, "Taches")
        agenda_vals = fetch_sheet_data(json_str, "Agenda")
        courses_vals = fetch_sheet_data(json_str, "Courses")
        notes_vals = fetch_sheet_data(json_str, "Notes")
        
        nb_taches = max(0, len(taches_vals) - 1)
        nb_agenda = max(0, len(agenda_vals) - 1)
        nb_courses = max(0, len(courses_vals) - 1)
        nb_notes = max(0, len(notes_vals) - 1)

        st.markdown("### 📊 Vue d'ensemble")
        
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f'<div class="dashboard-card"><div class="card-title">✅ Tâches en cours</div><div class="card-value">{nb_taches}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dashboard-card"><div class="card-title">🛒 Articles à acheter</div><div class="card-value">{nb_courses}</div></div>', unsafe_allow_html=True)
        with c2:
            st.markdown(f'<div class="dashboard-card"><div class="card-title">📅 Événements prévus</div><div class="card-value">{nb_agenda}</div></div>', unsafe_allow_html=True)
            st.markdown(f'<div class="dashboard-card"><div class="card-title">📌 Notes mémorisées</div><div class="card-value">{nb_notes}</div></div>', unsafe_allow_html=True)

        st.divider()
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🔄 Rafraîchir les données"):
                st.cache_data.clear()
                st.rerun()
        with col_act2:
            if st.button("🔴 Déconnexion JSON"):
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
        
        # --- SOUS-TAB : TÂCHES ---
        with sub_tab1:
            st.subheader("✅ Tâches à faire")
            all_vals = fetch_sheet_data(json_str, "Taches")
            taches_data = all_vals[1:] if len(all_vals) > 1 else []
            
            total_taches = len(taches_data)
            taches_faites = len([t for t in taches_data if len(t) > 2 and t[2] == "Fait"])
            
            if total_taches > 0:
                st.markdown(f"**Avancement : {taches_faites} / {total_taches} accomplie(s)**")
                st.progress(taches_faites / total_taches)

            cat_filter = st.selectbox("🔍 Catégorie", ["Toutes", "Maison", "Admin", "Saiko", "Urgent", "Autre"])
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
                            st.markdown(f"- ~~**{nom_t}**~~ *[{cat_t}]*")
                        else:
                            st.markdown(f"- **{nom_t}** *[{cat_t}]*")
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
                st.markdown("#### ➕ Nouvelle tâche")
                n_tache = st.text_input("Intitulé")
                n_cat = st.selectbox("Catégorie", ["Maison", "Admin", "Saiko", "Urgent", "Autre"])
                if st.form_submit_button("Ajouter") and n_tache:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Taches").append_row([n_tache, n_cat, "À faire"])
                    st.cache_data.clear()
                    st.rerun()

        # --- SOUS-TAB : AGENDA ---
        with sub_tab2:
            st.subheader("📅 Agenda")
            all_vals = fetch_sheet_data(json_str, "Agenda")
            events_data = all_vals[1:] if len(all_vals) > 1 else []

            if events_data:
                for idx, row in enumerate(events_data):
                    date_ev, heure_ev, titre_ev, desc_ev = (row + ["", "", "", ""])[:4]
                    real_idx = idx + 2
                    with st.expander(f"🗓️ {date_ev} {f'à {heure_ev}' if heure_ev else ''} — {titre_ev}"):
                        if desc_ev:
                            st.write(f"**Détails :** {desc_ev}")
                        if st.button("🗑️ Supprimer", key=f"ev_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Agenda").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.info("Aucun événement.")

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

        # --- SOUS-TAB : COURSES ---
        with sub_tab3:
            st.subheader("🛒 Liste de Courses")
            all_vals = fetch_sheet_data(json_str, "Courses")
            courses_data = all_vals[1:] if len(all_vals) > 1 else []

            if courses_data:
                for idx, row in enumerate(courses_data):
                    art, qte, cat = (row + ["Article", "1", "Général"])[:3]
                    real_idx = idx + 2
                    c1, c2 = st.columns([3, 1])
                    with c1:
                        st.markdown(f"- **{art}** *(Qté: {qte} | {cat})*")
                    with c2:
                        if st.button("✔️ Acquis", key=f"c_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Courses").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()
            else:
                st.info("Liste de courses vide.")

            st.divider()
            with st.form("form_courses", clear_on_submit=True):
                c_art = st.text_input("Article")
                c_qte = st.text_input("Quantité", value="1")
                c_cat = st.selectbox("Rayon", ["Supermarché", "Frais", "Fruits & Légumes", "Boissons", "Entretien", "Autre"])
                if st.form_submit_button("Ajouter aux courses") and c_art:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Courses").append_row([c_art, c_qte, c_cat])
                    st.cache_data.clear()
                    st.rerun()

        # --- SOUS-TAB : REPAS ---
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
                        with c1:
                            st.write(f"- **{typ}** : {plt}")
                        with c2:
                            if st.button("🗑️", key=f"rep_del_{real_idx}"):
                                get_gspread_client(json_str).open("MonAssistantData").worksheet("Repas").delete_rows(real_idx)
                                st.cache_data.clear()
                                st.rerun()
                else:
                    st.caption("Rien de prévu")

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
# SUPER-ONGLET 3 : VIE À DEUX
# ==========================================
with tab_vie_a_deux:
    if json_str:
        sub_tab_b, sub_tab_n, sub_tab_a, sub_tab_l = st.tabs(["💶 Budget", "📝 Notes", "🏡 Admin", "🧳 Listes"])

        # --- BUDGET ---
        with sub_tab_b:
            st.subheader("💶 Budget Commune")
            all_vals = fetch_sheet_data(json_str, "Budget")
            budget_data = all_vals[1:] if len(all_vals) > 1 else []

            total_lucas, total_alex = 0.0, 0.0
            if budget_data:
                for row in budget_data:
                    payer = row[1] if len(row) > 1 else ""
                    try:
                        amt = float(row[3].replace(',', '.')) if len(row) > 3 else 0.0
                    except ValueError:
                        amt = 0.0

                    if payer == "Lucas": total_lucas += amt
                    elif payer == "Alex": total_alex += amt

                chart_data = pd.DataFrame({"Personne": ["Lucas", "Alex"], "Total Dépensé (€)": [total_lucas, total_alex]})
                st.bar_chart(chart_data, x="Personne", y="Total Dépensé (€)")

                diff = (total_lucas - total_alex) / 2
                b1, b2 = st.columns(2)
                with b1: st.metric("Lucas a payé", f"{total_lucas:.2f} €")
                with b2: st.metric("Alex a payé", f"{total_alex:.2f} €")
                
                if diff > 0: st.success(f"👉 **Alex doit {diff:.2f} € à Lucas**")
                elif diff < 0: st.success(f"👉 **Lucas doit {abs(diff):.2f} € à Alex**")
                else: st.info("⚖️ Comptes équilibrés !")

                st.divider()
                for idx, row in enumerate(budget_data):
                    dt, pyr, lbl, val = (row + ["", "", "", "0"])[:4]
                    real_idx = idx + 2
                    c1, c2 = st.columns([4, 1])
                    with c1: st.markdown(f"- **{lbl}** : {val} € *(par {pyr} le {dt})*")
                    with c2:
                        if st.button("🗑️", key=f"b_del_{idx}"):
                            get_gspread_client(json_str).open("MonAssistantData").worksheet("Budget").delete_rows(real_idx)
                            st.cache_data.clear()
                            st.rerun()

            st.divider()
            with st.form("form_budget", clear_on_submit=True):
                b_date = st.date_input("Date", value=datetime.today())
                b_payer = st.radio("Qui a payé ?", ["Lucas", "Alex"], horizontal=True)
                b_label = st.text_input("Intitulé (ex: Courses, Resto...)")
                b_amount = st.number_input("Montant (€)", min_value=0.0, step=0.5)
                if st.form_submit_button("Ajouter dépense") and b_label and b_amount > 0:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Budget").append_row([str(b_date), b_payer, b_label, str(b_amount)])
                    st.cache_data.clear()
                    st.rerun()

        # --- NOTES ---
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

        # --- ADMIN ---
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

        # --- LISTES & CADEAUX ---
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

# ==========================================
# SUPER-ONGLET 4 : SAIKO & CUISINE
# ==========================================
with tab_loisirs:
    if json_str:
        sub_tab_s, sub_tab_r = st.tabs(["🐶 Saiko", "🍲 Recettes"])

        # --- SAIKO ---
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
                s_sujet = st.text_input("Titre / Sujet")
                s_notes = st.text_area("Notes")
                if st.form_submit_button("Enregistrer pour Saiko") and s_sujet:
                    get_gspread_client(json_str).open("MonAssistantData").worksheet("Saiko").append_row([str(s_date), s_type, s_sujet, s_notes])
                    st.cache_data.clear()
                    st.rerun()

        # --- RECETTES ---
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
                
