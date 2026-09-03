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

# --- STYLE CSS ULTRA-MODERNE ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', sans-serif;
    }
    
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        background-color: #f1f5f9;
        padding: 6px;
        border-radius: 16px;
        overflow-x: auto;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 8px 12px;
        font-weight: 600;
        font-size: 13px;
        color: #64748b;
        background-color: transparent;
        border: none;
        white-space: nowrap;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    .stButton button {
        border-radius: 12px;
        width: 100%;
        font-weight: 600;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 10px 16px;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.25);
        transition: all 0.2s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 18px rgba(99, 102, 241, 0.35);
    }

    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 14px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
        margin-bottom: 8px;
    }
    .metric-value {
        font-size: 22px;
        font-weight: 700;
        color: #4f46e5;
    }
    .metric-label {
        font-size: 11px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONNEXION GOOGLE SHEETS VIA FICHIER JSON ---
def connect_with_file(uploaded_file):
    try:
        creds_dict = json.load(uploaded_file)
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        
        try:
            sheet = client.open("MonAssistantData")
        except gspread.SpreadsheetNotFound:
            sheet = client.create("MonAssistantData")
            sheet.values_append("Sheet1", {'valueInputOption': 'RAW'}, {'values': [['Tache', 'Categorie', 'Statut']]})
            sheet.rename_worksheet(sheet.worksheet("Sheet1"), "Taches")
            
            sheet.add_worksheet(title="Agenda", rows="100", cols="20")
            sheet.values_append("Agenda", {'valueInputOption': 'RAW'}, {'values': [['Date', 'Heure', 'Titre', 'Description']]})
            
            sheet.add_worksheet(title="Courses", rows="100", cols="20")
            sheet.values_append("Courses", {'valueInputOption': 'RAW'}, {'values': [['Article', 'Quantite', 'Categorie']]})
            
            sheet.add_worksheet(title="Notes", rows="100", cols="20")
            sheet.values_append("Notes", {'valueInputOption': 'RAW'}, {'values': [['Titre', 'Contenu']]})
            
            sheet.add_worksheet(title="Recettes", rows="100", cols="20")
            sheet.values_append("Recettes", {'valueInputOption': 'RAW'}, {'values': [['Titre', 'Ingrédients', 'Instructions']]})
            
            sheet.add_worksheet(title="Saiko", rows="100", cols="20")
            sheet.values_append("Saiko", {'valueInputOption': 'RAW'}, {'values': [['Date', 'Type', 'Sujet', 'Notes']]})
            
        return sheet, None
    except Exception as e:
        return None, str(e)

def connect_with_secrets():
    try:
        if "gcp_service_account" in st.secrets:
            creds_dict = dict(st.secrets["gcp_service_account"])
            if "private_key" in creds_dict:
                creds_dict["private_key"] = creds_dict["private_key"].replace("\\n", "\n")
            scope = [
                "https://www.googleapis.com/auth/spreadsheets",
                "https://www.googleapis.com/auth/drive"
            ]
            creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
            client = gspread.authorize(creds)
            return client.open("MonAssistantData")
    except Exception:
        return None
    return None

sheet = connect_with_secrets()
if not sheet and "uploaded_sheet_data" in st.session_state:
    sheet = st.session_state["uploaded_sheet_data"]

# --- EN-TÊTE ---
st.markdown("## ✨ Notre Espace Partagé")
st.caption("Centralisez votre quotidien à deux, en toute simplicité 🚀")

# --- NAVIGATION PAR ONGLETS ---
tab_accueil, tab_agenda, tab_taches, tab_courses, tab_saiko, tab_notes, tab_recettes = st.tabs([
    "🏠 Accueil", "📅 Agenda", "✅ Tâches", "🛒 Courses", "🐶 Saiko", "📝 Notes", "🍲 Recettes"
])

# ==========================================
# ONGLET 0 : ACCUEIL
# ==========================================
with tab_accueil:
    if sheet:
        try:
            ws_dict = {w.title: w for w in sheet.worksheets()}
            
            taches_count = max(0, len(ws_dict["Taches"].get_all_values()) - 1) if "Taches" in ws_dict else 0
            agenda_count = max(0, len(ws_dict["Agenda"].get_all_values()) - 1) if "Agenda" in ws_dict else 0
            courses_count = max(0, len(ws_dict["Courses"].get_all_values()) - 1) if "Courses" in ws_dict else 0
            notes_count = max(0, len(ws_dict["Notes"].get_all_values()) - 1) if "Notes" in ws_dict else 0
            recettes_count = max(0, len(ws_dict["Recettes"].get_all_values()) - 1) if "Recettes" in ws_dict else 0
            saiko_count = max(0, len(ws_dict["Saiko"].get_all_values()) - 1) if "Saiko" in ws_dict else 0
            
            st.markdown("### 📊 Vue d'ensemble")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{agenda_count}</div><div class="metric-label">📅 Agenda</div></div>', unsafe_allow_html=True)
            with c2:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{taches_count}</div><div class="metric-label">✅ Tâches</div></div>', unsafe_allow_html=True)
            with c3:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{courses_count}</div><div class="metric-label">🛒 Courses</div></div>', unsafe_allow_html=True)
                
            c4, c5, c6 = st.columns(3)
            with c4:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{saiko_count}</div><div class="metric-label">🐶 Saiko</div></div>', unsafe_allow_html=True)
            with c5:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{notes_count}</div><div class="metric-label">📌 Notes</div></div>', unsafe_allow_html=True)
            with c6:
                st.markdown(f'<div class="metric-card"><div class="metric-value">{recettes_count}</div><div class="metric-label">🍲 Recettes</div></div>', unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("💡 **Astuce mobile :** Enregistrez cette page sur l'écran d'accueil de votre smartphone pour l'ouvrir comme une application native !")
        except Exception as e:
            st.warning(f"Erreur de chargement du dashboard : {e}")
    else:
        st.warning("⚠️ Connexion Google Sheets requise.")
        uploaded_json = st.file_uploader("Glissez votre fichier JSON de configuration ici", type=["json"])
        if uploaded_json is not None:
            connected_sheet, error_msg = connect_with_file(uploaded_json)
            if connected_sheet:
                st.session_state["uploaded_sheet_data"] = connected_sheet
                st.success("Connexion réussie !")
                st.rerun()
            else:
                st.error(f"Erreur : {error_msg}")

# ==========================================
# ONGLET 1 : AGENDA
# ==========================================
with tab_agenda:
    st.subheader("📅 Agenda & Événements")
    if sheet:
        try:
            ws_names = [w.title for w in sheet.worksheets()]
            agenda_ws = sheet.worksheet("Agenda") if "Agenda" in ws_names else sheet.add_worksheet(title="Agenda", rows="100", cols="20")
            
            all_vals = agenda_ws.get_all_values()
            if len(all_vals) <= 1:
                agenda_ws.append_row(["Date", "Heure", "Titre", "Description"])
                all_vals = [["Date", "Heure", "Titre", "Description"]]

            events_data = all_vals[1:]
            if events_data:
                for idx, row in enumerate(events_data):
                    date_ev = row[0] if len(row) > 0 else ""
                    heure_ev = row[1] if len(row) > 1 else ""
                    titre_ev = row[2] if len(row) > 2 else "Sans titre"
                    desc_ev = row[3] if len(row) > 3 else ""
                    real_idx = all_vals.index(row) + 1
                    
                    with st.expander(f"🗓️ {date_ev} {f'à {heure_ev}' if heure_ev else ''} — {titre_ev}"):
                        if desc_ev:
                            st.write(f"**Détails :** {desc_ev}")
                        if st.button("🗑️ Supprimer l'événement", key=f"del_ev_{idx}_{real_idx}"):
                            agenda_ws.delete_rows(real_idx)
                            st.rerun()
            else:
                st.info("Aucun événement prévu.")

            st.divider()
            with st.form("form_agenda", clear_on_submit=True):
                st.markdown("#### ➕ Ajouter un événement")
                e_date = st.date_input("Date", value=datetime.today())
                e_heure = st.time_input("Heure", value=datetime.now().time())
                e_titre = st.text_input("Titre de l'événement")
                e_desc = st.text_area("Description / Lieu (optionnel)")
                if st.form_submit_button("Enregistrer l'événement") and e_titre:
                    agenda_ws.append_row([str(e_date), str(e_heure.strftime("%H:%M")), e_titre, e_desc])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur Agenda : {e}")
    else:
        st.info("Veuillez connecter votre fichier dans l'Accueil.")

# ==========================================
# ONGLET 2 : TÂCHES
# ==========================================
with tab_taches:
    st.subheader("✅ Tâches à faire")
    if sheet:
        try:
            ws_names = [w.title for w in sheet.worksheets()]
            taches_ws = sheet.worksheet("Taches") if "Taches" in ws_names else sheet.add_worksheet(title="Taches", rows="100", cols="20")
            
            all_vals = taches_ws.get_all_values()
            if len(all_vals) <= 1:
                taches_ws.append_row(["Tache", "Categorie", "Statut"])
                all_vals = [["Tache", "Categorie", "Statut"]]

            taches_data = all_vals[1:]
            
            cat_filter = st.selectbox("🔍 Filtrer par catégorie", ["Toutes", "Maison", "Admin", "Saiko", "Urgent", "Autre"])
            filtered_taches = [t for t in taches_data if cat_filter == "Toutes" or (len(t) > 1 and t[1] == cat_filter)] if taches_data else []

            if filtered_taches:
                for idx, row in enumerate(filtered_taches):
                    nom_t = row[0] if len(row) > 0 else "Sans nom"
                    cat_t = row[1] if len(row) > 1 else "Général"
                    real_idx = all_vals.index(row) + 1
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"- **{nom_t}** *[{cat_t}]*")
                    with col2:
                        if st.button("✔️ Fait", key=f"del_t_{idx}_{real_idx}"):
                            taches_ws.delete_rows(real_idx)
                            st.rerun()
            else:
                st.info("Aucune tâche dans cette catégorie.")

            st.divider()
            with st.form("form_tache", clear_on_submit=True):
                st.markdown("#### ➕ Nouvelle tâche")
                n_tache = st.text_input("Intitulé de la tâche")
                n_cat = st.selectbox("Catégorie", ["Maison", "Admin", "Saiko", "Urgent", "Autre"])
                if st.form_submit_button("Ajouter la tâche") and n_tache:
                    taches_ws.append_row([n_tache, n_cat, "À faire"])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur Tâches : {e}")
    else:
        st.info("Veuillez connecter votre fichier dans l'Accueil.")

# ==========================================
# ONGLET 3 : COURSES
# ==========================================
with tab_courses:
    st.subheader("🛒 Liste de Courses")
    if sheet:
        try:
            ws_names = [w.title for w in sheet.worksheets()]
            courses_ws = sheet.worksheet("Courses") if "Courses" in ws_names else sheet.add_worksheet(title="Courses", rows="100", cols="20")
            
            all_vals = courses_ws.get_all_values()
            if len(all_vals) <= 1:
                courses_ws.append_row(["Article", "Quantite", "Categorie"])
                all_vals = [["Article", "Quantite", "Categorie"]]

            courses_data = all_vals[1:]
            if courses_data:
                for idx, row in enumerate(courses_data):
                    art = row[0] if len(row) > 0 else "Article"
                    qte = row[1] if len(row) > 1 else "1"
                    cat = row[2] if len(row) > 2 else "Général"
                    real_idx = all_vals.index(row) + 1
                    
                    col1, col2 = st.columns([3, 1])
                    with col1:
                        st.markdown(f"- **{art}** *(Qté: {qte} | {cat})*")
                    with col2:
                        if st.button("✔️ Acquis", key=f"del_c_{idx}_{real_idx}"):
                            courses_ws.delete_rows(real_idx)
                            st.rerun()
            else:
                st.info("La liste de courses est vide.")

            st.divider()
            with st.form("form_courses", clear_on_submit=True):
                st.markdown("#### ➕ Ajouter un article")
                c_art = st.text_input("Article (ex: Pain, Lait...)")
                c_qte = st.text_input("Quantité", value="1")
                c_cat = st.selectbox("Rayon", ["Supermarché", "Frais", "Fruits & Légumes", "Boissons", "Entretien", "Autre"])
                if st.form_submit_button("Ajouter aux courses") and c_art:
                    courses_ws.append_row([c_art, c_qte, c_cat])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur Courses : {e}")
    else:
        st.info("Veuillez connecter votre fichier dans l'Accueil.")

# ==========================================
# ONGLET 4 : SAIKO 🐾
# ==========================================
with tab_saiko:
    st.subheader("🐶 Espace Saiko")
    st.caption("Suivi des soins, rendez-vous vétérinaire et santé")
    if sheet:
        try:
            ws_names = [w.title for w in sheet.worksheets()]
            saiko_ws = sheet.worksheet("Saiko") if "Saiko" in ws_names else sheet.add_worksheet(title="Saiko", rows="100", cols="20")
            
            all_vals = saiko_ws.get_all_values()
            if len(all_vals) <= 1:
                saiko_ws.append_row(["Date", "Type", "Sujet", "Notes"])
                all_vals = [["Date", "Type", "Sujet", "Notes"]]

            saiko_data = all_vals[1:]
            if saiko_data:
                for idx, row in enumerate(saiko_data):
                    dt = row[0] if len(row) > 0 else ""
                    tp = row[1] if len(row) > 1 else "Soin"
                    sj = row[2] if len(row) > 2 else "Remarque"
                    nt = row[3] if len(row) > 3 else ""
                    real_idx = all_vals.index(row) + 1
                    
                    with st.expander(f"🐾 [{tp}] {sj} ({dt})"):
                        if nt:
                            st.write(nt)
                        if st.button("🗑️ Supprimer", key=f"del_sk_{idx}_{real_idx}"):
                            saiko_ws.delete_rows(real_idx)
                            st.rerun()
            else:
                st.info("Aucun rappel ni soin enregistré pour Saiko.")

            st.divider()
            with st.form("form_saiko", clear_on_submit=True):
                st.markdown("#### ➕ Ajouter un suivi pour Saiko")
                s_date = st.date_input("Date", value=datetime.today())
                s_type = st.selectbox("Type", ["Vétérinaire / Vaccin", "Anti-puces / Vermifuge", "Achat Croquettes / Matériel", "Soin / Toilettage", "Autre"])
                s_sujet = st.text_input("Titre / Sujet")
                s_notes = st.text_area("Notes complémentaires")
                if st.form_submit_button("Enregistrer pour Saiko") and s_sujet:
                    saiko_ws.append_row([str(s_date), s_type, s_sujet, s_notes])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur Saiko : {e}")
    else:
        st.info("Veuillez connecter votre fichier dans l'Accueil.")

# ==========================================
# ONGLET 5 : NOTES
# ==========================================
with tab_notes:
    st.subheader("📝 Notes Partagées")
    if sheet:
        try:
            ws_names = [w.title for w in sheet.worksheets()]
            notes_ws = sheet.worksheet("Notes") if "Notes" in ws_names else sheet.add_worksheet(title="Notes", rows="100", cols="20")
            
            all_vals = notes_ws.get_all_values()
            if len(all_vals) <= 1:
                notes_ws.append_row(["Titre", "Contenu"])
                all_vals = [["Titre", "Contenu"]]

            search_note = st.text_input("🔍 Rechercher dans les notes...", placeholder="Mot-clé...")
            notes_data = all_vals[1:]

            if search_note and notes_data:
                filtered_notes = [n for n in notes_data if search_note.lower() in " ".join(n).lower()]
            else:
                filtered_notes = notes_data

            if filtered_notes:
                for idx, row in enumerate(filtered_notes):
                    titre = row[0] if len(row) > 0 and row[0] else "Sans titre"
                    contenu = row[1] if len(row) > 1 else ""
                    real_idx = all_vals.index(row) + 1
                    
                    with st.expander(f"📌 {titre}"):
                        st.write(contenu)
                        if st.button("🗑️ Supprimer", key=f"del_n_{idx}_{real_idx}"):
                            notes_ws.delete_rows(real_idx)
                            st.rerun()
            else:
                st.info("Aucune note trouvée.")

            st.divider()
            with st.form("form_note", clear_on_submit=True):
                st.markdown("#### ➕ Nouvelle note")
                n_titre = st.text_input("Titre")
                n_contenu = st.text_area("Contenu")
                if st.form_submit_button("Enregistrer la note") and n_titre:
                    notes_ws.append_row([n_titre, n_contenu])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur Notes : {e}")
    else:
        st.info("Veuillez connecter votre fichier dans l'Accueil.")

# ==========================================
# ONGLET 6 : RECETTES
# ==========================================
with tab_recettes:
    st.subheader("🍲 Recettes de Cuisine")
    if sheet:
        try:
            ws_names = [w.title for w in sheet.worksheets()]
            recettes_ws = sheet.worksheet("Recettes") if "Recettes" in ws_names else sheet.add_worksheet(title="Recettes", rows="100", cols="20")
            courses_ws = sheet.worksheet("Courses") if "Courses" in ws_names else sheet.add_worksheet(title="Courses", rows="100", cols="20")
            
            all_vals = recettes_ws.get_all_values()
            if len(all_vals) <= 1:
                recettes_ws.append_row(["Titre", "Ingrédients", "Instructions"])
                all_vals = [["Titre", "Ingrédients", "Instructions"]]

            search_recette = st.text_input("🔍 Rechercher une recette...", placeholder="Nom ou ingrédient...")
            recettes_data = all_vals[1:]

            if search_recette and recettes_data:
                filtered_recettes = [r for r in recettes_data if search_recette.lower() in " ".join(r).lower()]
            else:
                filtered_recettes = recettes_data

            if filtered_recettes:
                for idx, row in enumerate(filtered_recettes):
                    titre = row[0] if len(row) > 0 and row[0] else "Sans titre"
                    ingredients = row[1] if len(row) > 1 else ""
                    instructions = row[2] if len(row) > 2 else ""
                    real_idx = all_vals.index(row) + 1
                    
                    with st.expander(f"🍲 {titre}"):
                        st.markdown(f"**🛒 Ingrédients :**\n{ingredients}")
                        st.markdown(f"**👨‍🍳 Instructions :**\n{instructions}")
                        
                        col_act1, col_act2 = st.columns(2)
                        with col_act1:
                            if st.button("🛒 Envoyer aux courses", key=f"send_c_{idx}_{real_idx}"):
                                lines_ing = [l.strip() for l in ingredients.split('\n') if l.strip()]
                                for ing in lines_ing:
                                    courses_ws.append_row([ing, "1", f"Recette: {titre}"])
                                st.success("Ingrédients ajoutés aux courses !")
                                st.rerun()
                        with col_act2:
                            if st.button("🗑️ Supprimer", key=f"del_r_{idx}_{real_idx}"):
                                recettes_ws.delete_rows(real_idx)
                                st.rerun()
            else:
                st.info("Aucune recette trouvée.")

            st.divider()
            with st.form("form_recette", clear_on_submit=True):
                st.markdown("#### ➕ Nouvelle recette")
                r_titre = st.text_input("Nom de la recette")
                r_ing = st.text_area("Ingrédients (un par ligne)")
                r_inst = st.text_area("Instructions")
                if st.form_submit_button("Enregistrer la recette") and r_titre:
                    recettes_ws.append_row([r_titre, r_ing, r_inst])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur Recettes : {e}")
    else:
        st.info("Veuillez connecter votre fichier dans l'Accueil.")
