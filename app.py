import streamlit as st
import pandas as pd
import gspread
from google.oauth2.service_account import Credentials
import json

# --- CONFIGURATION DE LA PAGE ---
st.set_page_config(
    page_title="Notre Assistant Partagé", 
    page_icon="💡", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# --- STYLE CSS PERSONNALISÉ ---
st.markdown("""
    <style>
    .stButton button {
        border-radius: 12px;
        width: 100%;
        font-weight: bold;
    }
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 8px 12px;
        font-weight: 600;
        font-size: 13px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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
            # Création automatique des onglets si le fichier est neuf
            sheet.values_append("Sheet1", {'valueInputOption': 'RAW'}, {'values': [['Tache', 'Statut']]})
            sheet.rename_worksheet(sheet.worksheet("Sheet1"), "Taches")
            
            sheet.add_worksheet(title="Notes", rows="100", cols="20")
            sheet.values_append("Notes", {'valueInputOption': 'RAW'}, {'values': [['Titre', 'Contenu']]})
            
            sheet.add_worksheet(title="Recettes", rows="100", cols="20")
            sheet.values_append("Recettes", {'valueInputOption': 'RAW'}, {'values': [['Titre', 'Ingrédients', 'Instructions']]})
            
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

# --- EN-TÊTE DE LA PAGE ---
st.title("💡 Notre Tableau de Bord")
st.caption("Partagé en direct entre vous et votre copine 🚀")

# --- NAVIGATION PAR ONGLET (5 onglets) ---
tab_accueil, tab_assistant, tab_taches, tab_notes, tab_recettes = st.tabs(["🏠 Accueil", "🤖 Assistant IA", "✅ Tâches", "📝 Notes", "🍲 Recettes"])

# ==========================================
# ONGLET 0 : ACCUEIL
# ==========================================
with tab_accueil:
    st.header("Bienvenue sur votre espace !")
    st.write("Ce tableau de bord centralise toutes vos idées, vos tâches, vos mémos et vos recettes.")
    
    if sheet:
        try:
            sheet_names = [w.title for w in sheet.worksheets()]
            taches_count = len(sheet.worksheet("Taches").get_all_records()) if "Taches" in sheet_names else 0
            notes_count = len(sheet.worksheet("Notes").get_all_records()) if "Notes" in sheet_names else 0
            recettes_count = len(sheet.worksheet("Recettes").get_all_records()) if "Recettes" in sheet_names else 0
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric(label="✅ Tâches", value=taches_count)
            with col2:
                st.metric(label="📌 Notes", value=notes_count)
            with col3:
                st.metric(label="🍲 Recettes", value=recettes_count)
                
            st.divider()
            st.info("💡 **Astuce mobile :** Vous pouvez ajouter cette application sur l'écran d'accueil de votre téléphone pour l'utiliser comme une vraie application native !")
        except Exception as e:
            st.warning(f"Connecté, mais structure incomplète : {e}")
    else:
        st.warning("⚠️ Connexion Google Sheets requise.")
        st.write("Pour activer l'application, déposez votre fichier de clé JSON ci-dessous :")
        
        uploaded_json = st.file_uploader("Fichier JSON de configuration", type=["json"])
        if uploaded_json is not None:
            connected_sheet, error_msg = connect_with_file(uploaded_json)
            if connected_sheet:
                st.session_state["uploaded_sheet_data"] = connected_sheet
                st.success("Connexion réussie ! Actualisation en cours...")
                st.rerun()
            else:
                st.error(f"Erreur de connexion : {error_msg}")

# ==========================================
# ONGLET 1 : ASSISTANT IA
# ==========================================
with tab_assistant:
    st.header("Discutez avec votre assistant")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    if prompt := st.chat_input("Que voulez-vous planifier ou chercher ?"):
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        response = f"J'ai bien reçu votre message : '{prompt}'. Je m'en occupe !"
        with st.chat_message("assistant"):
            st.markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

# ==========================================
# ONGLET 2 : TÂCHES
# ==========================================
with tab_taches:
    st.header("✅ Tâches à faire")
    
    if sheet:
        try:
            sheet_names = [w.title for w in sheet.worksheets()]
            if "Taches" not in sheet_names:
                taches_ws = sheet.add_worksheet(title="Taches", rows="100", cols="20")
                taches_ws.append_row(["Tache", "Statut"])
            else:
                taches_ws = sheet.worksheet("Taches")
                
            all_taches = taches_ws.get_all_records()
            
            if all_taches:
                st.write(f"*{len(all_taches)} tâche(s) enregistrée(s)*")
                for index, row in enumerate(all_taches):
                    tache_nom = row.get('Tache', 'Sans nom')
                    
                    col_t, col_b = st.columns([3, 1])
                    with col_t:
                        st.markdown(f"- {tache_nom}")
                    with col_b:
                        if st.button("✔️ Fait", key=f"del_tache_{index}"):
                            real_row_index = all_taches.index(row) + 2
                            taches_ws.delete_rows(real_row_index)
                            st.success("Tâche validée !")
                            st.rerun()
            else:
                st.info("Aucune tâche en cours. Bravo !")
                
            st.divider()
            
            with st.form("form_tache", clear_on_submit=True):
                st.subheader("➕ Ajouter une tâche")
                n_tache = st.text_input("Intitulé de la tâche")
                submitted_tache = st.form_submit_button("Ajouter la tâche")
                
                if submitted_tache and n_tache:
                    taches_ws.append_row([n_tache, "À faire"])
                    st.success("Tâche ajoutée !")
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur avec l'onglet Tâches : {e}")
    else:
        st.info("Veuillez d'abord connecter votre Google Sheet depuis l'onglet Accueil.")

# ==========================================
# ONGLET 3 : NOTES
# ==========================================
with tab_notes:
    st.header("Nos Notes Partagées")
    
    if sheet:
        try:
            sheet_names = [w.title for w in sheet.worksheets()]
            if "Notes" not in sheet_names:
                notes_ws = sheet.add_worksheet(title="Notes", rows="100", cols="20")
                notes_ws.append_row(["Titre", "Contenu"])
            else:
                notes_ws = sheet.worksheet("Notes")
                
            all_notes = notes_ws.get_all_records()
            
            search_note = st.text_input("🔍 Rechercher dans les notes", placeholder="Tapez un mot-clé...")
            
            if search_note:
                filtered_notes = [n for n in all_notes if search_note.lower() in str(n.get('Titre','')).lower() or search_note.lower() in str(n.get('Contenu','')).lower()]
            else:
                filtered_notes = all_notes

            if filtered_notes:
                st.write(f"*{len(filtered_notes)} note(s) affichée(s)*")
                for index, row in enumerate(filtered_notes):
                    titre = row.get('Titre', 'Sans titre')
                    contenu = row.get('Contenu', '')
                    
                    with st.expander(f"📌 {titre}"):
                        st.write(contenu)
                        if st.button("🗑️ Supprimer", key=f"del_note_{index}"):
                            real_row_index = all_notes.index(row) + 2
                            notes_ws.delete_rows(real_row_index)
                            st.success("Note supprimée !")
                            st.rerun()
            else:
                st.info("Aucune note trouvée.")
                
            st.divider()
            
            with st.form("form_note", clear_on_submit=True):
                st.subheader("➕ Ajouter une nouvelle note")
                n_titre = st.text_input("Titre de la note")
                n_contenu = st.text_area("Contenu de la note")
                submitted_note = st.form_submit_button("Enregistrer la note")
                
                if submitted_note and n_titre:
                    notes_ws.append_row([n_titre, n_contenu])
                    st.success("Note ajoutée !")
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur avec l'onglet Notes : {e}")
    else:
        st.info("Veuillez d'abord connecter votre Google Sheet depuis l'onglet Accueil.")

# ==========================================
# ONGLET 4 : RECETTES
# ==========================================
with tab_recettes:
    st.header("Nos Recettes de Cuisine")
    
    if sheet:
        try:
            sheet_names = [w.title for w in sheet.worksheets()]
            if "Recettes" not in sheet_names:
                recettes_ws = sheet.add_worksheet(title="Recettes", rows="100", cols="20")
                recettes_ws.append_row(["Titre", "Ingrédients", "Instructions"])
            else:
                recettes_ws = sheet.worksheet("Recettes")
                
            all_recettes = recettes_ws.get_all_records()
            
            search_recette = st.text_input("🔍 Rechercher une recette ou un ingrédient", placeholder="Ex: Pâtes...")
            
            if search_recette:
                filtered_recettes = [r for r in all_recettes if search_recette.lower() in str(r.get('Titre','')).lower() or search_recette.lower() in str(r.get('Ingrédients','')).lower()]
            else:
                filtered_recettes = all_recettes

            if filtered_recettes:
                st.write(f"*{len(filtered_recettes)} recette(s) affichée(s)*")
                for index, row in enumerate(filtered_recettes):
                    titre = row.get('Titre', 'Sans titre')
                    ingredients = row.get('Ingrédients', '')
                    instructions = row.get('Instructions', '')
                    
                    with st.expander(f"🍲 {titre}"):
                        st.markdown(f"**🛒 Ingrédients :**\n{ingredients}")
                        st.markdown(f"**👨‍🍳 Instructions :**\n{instructions}")
                        
                        if st.button("🗑️ Supprimer cette recette", key=f"del_recette_{index}"):
                            real_row_index = all_recettes.index(row) + 2
                            recettes_ws.delete_rows(real_row_index)
                            st.success("Recette supprimée !")
                            st.rerun()
            else:
                st.info("Aucune recette trouvée.")
                
            st.divider()
            
            with st.form("form_recette", clear_on_submit=True):
                st.subheader("➕ Ajouter une nouvelle recette")
                r_titre = st.text_input("Nom de la recette")
                r_ingredients = st.text_area("Ingrédients nécessaires")
                r_instructions = st.text_area("Étapes de préparation")
                submitted_recette = st.form_submit_button("Enregistrer la recette")
                
                if submitted_recette and r_titre:
                    recettes_ws.append_row([r_titre, r_ingredients, r_instructions])
                    st.success("Recette ajoutée !")
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur avec l'onglet Recettes : {e}")
    else:
        st.info("Veuillez d'abord connecter votre Google Sheet depuis l'onglet Accueil.")
