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

# --- STYLE CSS ULTRA-MODERNISÉ ---
st.markdown("""
    <style>
    /* Style général et typographie douce */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Plus Jakarta+Sans', sans-serif;
    }
    
    /* Supprimer les éléments par défaut de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    /* Style des onglets modernes */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f8fafc;
        padding: 6px;
        border-radius: 16px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 12px;
        padding: 10px 18px;
        font-weight: 600;
        font-size: 14px;
        color: #64748b;
        background-color: transparent;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background-color: #ffffff !important;
        color: #0f172a !important;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
    }

    /* Boutons stylisés */
    .stButton button {
        border-radius: 12px;
        width: 100%;
        font-weight: 600;
        background: linear-gradient(135deg, #6366f1 0%, #4f46e5 100%);
        color: white;
        border: none;
        padding: 10px 20px;
        box-shadow: 0 4px 14px rgba(99, 102, 241, 0.3);
        transition: all 0.3s ease;
    }
    .stButton button:hover {
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(99, 102, 241, 0.4);
    }

    /* Cartes de statistiques personnalisées */
    .metric-card {
        background: linear-gradient(135deg, #ffffff 0%, #f8fafc 100%);
        border: 1px solid #e2e8f0;
        border-radius: 16px;
        padding: 20px;
        text-align: center;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.02);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #4f46e5;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 600;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    </style>
""", unsafe_allow_html=True)

# --- CONNEXION VIA FICHIER JSON ---
def connect_with_json_file(uploaded_file):
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
            sheet.values_append("Sheet1", {'valueInputOption': 'RAW'}, {'values': [['Date', 'Heure', 'Titre', 'Description']]})
            sheet.rename_worksheet(sheet.worksheet("Sheet1"), "Agenda")
            sheet.add_worksheet(title="Notes", rows="100", cols="20")
            sheet.values_append("Notes", {'valueInputOption': 'RAW'}, {'values': [['Titre', 'Contenu']]})
            sheet.add_worksheet(title="Recettes", rows="100", cols="20")
            sheet.values_append("Recettes", {'valueInputOption': 'RAW'}, {'values': [['Titre', 'Ingrédients', 'Instructions']]})
            
        return sheet, None
    except Exception as e:
        return None, str(e)

# --- EN-TÊTE ---
st.markdown("## ✨ Notre Espace Partagé")
st.caption("Centralisez votre quotidien à deux, en toute simplicité 🚀")
st.markdown("---")

sheet = st.session_state.get("sheet_instance", None)

# --- NAVIGATION PAR ONGLETS ---
tab_accueil, tab_agenda, tab_notes, tab_recettes = st.tabs(["🏠 Accueil", "📅 Agenda", "📝 Notes", "🍲 Recettes"])

# ==========================================
# ONGLET 0 : ACCUEIL
# ==========================================
with tab_accueil:
    if not sheet:
        st.markdown("### 🔐 Connexion requise")
        st.write("Glissez votre fichier de clé JSON Google Cloud ci-dessous pour lancer l'application :")
        
        uploaded_json = st.file_uploader("Fichier JSON de configuration", type=["json"])
        if uploaded_json is not None:
            connected_sheet, error_msg = connect_with_json_file(uploaded_json)
            if connected_sheet:
                st.session_state["sheet_instance"] = connected_sheet
                st.success("Connexion établie avec succès ! ✨")
                st.rerun()
            else:
                st.error(f"Erreur de connexion : {error_msg}")
    else:
        try:
            agenda_count = len(sheet.worksheet("Agenda").get_all_records()) if "Agenda" in [w.title for w in sheet.worksheets()] else 0
            notes_count = len(sheet.worksheet("Notes").get_all_records()) if "Notes" in [w.title for w in sheet.worksheets()] else 0
            recettes_count = len(sheet.worksheet("Recettes").get_all_records()) if "Recettes" in [w.title for w in sheet.worksheets()] else 0
            
            st.markdown("### 📊 Vue d'ensemble")
            
            c1, c2, c3 = st.columns(3)
            with c1:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{agenda_count}</div>
                        <div class="metric-label">📅 Événements</div>
                    </div>
                """, unsafe_allow_html=True)
            with c2:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{notes_count}</div>
                        <div class="metric-label">📌 Notes</div>
                    </div>
                """, unsafe_allow_html=True)
            with c3:
                st.markdown(f"""
                    <div class="metric-card">
                        <div class="metric-value">{recettes_count}</div>
                        <div class="metric-label">🍲 Recettes</div>
                    </div>
                """, unsafe_allow_html=True)
                
            st.markdown("<br>", unsafe_allow_html=True)
            st.info("💡 **Astuce mobile :** Enregistrez cette application sur l'écran d'accueil de votre téléphone pour y accéder comme une application native.")
        except Exception as e:
            st.warning(f"Connecté, mais structure des onglets incomplète : {e}")

# ==========================================
# ONGLET 1 : AGENDA
# ==========================================
with tab_agenda:
    if sheet:
        try:
            sheet_names = [w.title for w in sheet.worksheets()]
            if "Agenda" not in sheet_names:
                agenda_ws = sheet.add_worksheet(title="Agenda", rows="100", cols="20")
                agenda_ws.append_row(["Date", "Heure", "Titre", "Description"])
            else:
                agenda_ws = sheet.worksheet("Agenda")
                
            all_events = agenda_ws.get_all_records()
            
            if all_events:
                st.markdown(f"**{len(all_events)} événement(s) à venir**")
                for index, row in enumerate(all_events):
                    with st.expander(f"🗓️ {row.get('Date', '')} à {row.get('Heure', '')} — {row.get('Titre', 'Sans titre')}"):
                        if row.get('Description'):
                            st.write(row.get('Description'))
                        if st.button("🗑️ Supprimer", key=f"del_ev_{index}"):
                            agenda_ws.delete_rows(all_events.index(row) + 2)
                            st.rerun()
            else:
                st.info("Aucun événement prévu pour le moment.")
                
            st.markdown("---")
            with st.form("form_agenda", clear_on_submit=True):
                st.markdown("#### ➕ Nouvel événement")
                e_date = st.date_input("Date", value=datetime.today())
                e_heure = st.time_input("Heure", value=datetime.now().time())
                e_titre = st.text_input("Titre")
                e_desc = st.text_area("Description (optionnel)")
                if st.form_submit_button("Ajouter à l'agenda") and e_titre:
                    agenda_ws.append_row([str(e_date), str(e_heure.strftime("%H:%M")), e_titre, e_desc])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.info("Veuillez connecter votre fichier dans l'onglet Accueil.")

# ==========================================
# ONGLET 2 : NOTES
# ==========================================
with tab_notes:
    if sheet:
        try:
            notes_ws = sheet.worksheet("Notes")
            all_notes = notes_ws.get_all_records()
            
            search_note = st.text_input("🔍 Rechercher...", placeholder="Mot-clé dans les notes")
            filtered_notes = [n for n in all_notes if search_note.lower() in str(n.get('Titre','')).lower() or search_note.lower() in str(n.get('Contenu','')).lower()] if search_note else all_notes

            if filtered_notes:
                for index, row in enumerate(filtered_notes):
                    with st.expander(f"📌 {row.get('Titre', 'Sans titre')}"):
                        st.write(row.get('Contenu', ''))
                        if st.button("🗑️ Supprimer", key=f"del_n_{index}"):
                            notes_ws.delete_rows(all_notes.index(row) + 2)
                            st.rerun()
            else:
                st.info("Aucune note trouvée.")
                
            st.markdown("---")
            with st.form("form_note", clear_on_submit=True):
                st.markdown("#### ➕ Nouvelle note")
                n_titre = st.text_input("Titre")
                n_contenu = st.text_area("Contenu")
                if st.form_submit_button("Enregistrer la note") and n_titre:
                    notes_ws.append_row([n_titre, n_contenu])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.info("Connexion requise dans l'Accueil.")

# ==========================================
# ONGLET 3 : RECETTES
# ==========================================
with tab_recettes:
    if sheet:
        try:
            recettes_ws = sheet.worksheet("Recettes")
            all_recettes = recettes_ws.get_all_records()
            
            search_rec = st.text_input("🔍 Rechercher une recette", placeholder="Ex: Pâtes...")
            filtered_rec = [r for r in all_recettes if search_rec.lower() in str(r.get('Titre','')).lower()] if search_rec else all_recettes

            if filtered_rec:
                for index, row in enumerate(filtered_rec):
                    with st.expander(f"🍲 {row.get('Titre', 'Sans titre')}"):
                        st.markdown(f"**🛒 Ingrédients :**\n{row.get('Ingrédients', '')}")
                        st.markdown(f"**👨‍🍳 Instructions :**\n{row.get('Instructions', '')}")
                        if st.button("🗑️ Supprimer", key=f"del_r_{index}"):
                            recettes_ws.delete_rows(all_recettes.index(row) + 2)
                            st.rerun()
            else:
                st.info("Aucune recette trouvée.")
                
            st.markdown("---")
            with st.form("form_recette", clear_on_submit=True):
                st.markdown("#### ➕ Nouvelle recette")
                r_titre = st.text_input("Nom de la recette")
                r_ing = st.text_input("Ingrédients")
                r_inst = st.text_area("Instructions")
                if st.form_submit_button("Enregistrer la recette") and r_titre:
                    recettes_ws.append_row([r_titre, r_ing, r_inst])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.info("Connexion requise dans l'Accueil.")
