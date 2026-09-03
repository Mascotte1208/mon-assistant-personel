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
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px 8px 0px 0px;
        padding: 10px 16px;
        font-weight: 600;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CONNEXION GOOGLE SHEETS VIA FICHIER JSON ---
@st.cache_resource
def connect_with_file(uploaded_file):
    try:
        creds_dict = json.load(uploaded_file)
        scope = [
            "https://www.googleapis.com/auth/spreadsheets",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = Credentials.from_service_account_info(creds_dict, scopes=scope)
        client = gspread.authorize(creds)
        sheet = client.open("MonAssistantData")
        return sheet
    except Exception as e:
        return None

@st.cache_resource
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

# Tentative de récupération depuis la session ou les secrets
sheet = connect_with_secrets()
if not sheet and "uploaded_sheet_data" in st.session_state:
    sheet = st.session_state["uploaded_sheet_data"]

# --- EN-TÊTE DE LA PAGE ---
st.title("💡 Notre Tableau de Bord")
st.caption("Partagé en direct entre vous et votre copine 🚀")

# --- NAVIGATION PAR ONGLET ---
tab_accueil, tab_assistant, tab_notes, tab_recettes = st.tabs(["🏠 Accueil", "🤖 Assistant IA", "📝 Notes", "🍲 Recettes"])

# ==========================================
# ONGLET 0 : ACCUEIL
# ==========================================
with tab_accueil:
    st.header("Bienvenue sur votre espace !")
    st.write("Ce tableau de bord centralise toutes vos idées, vos mémos et vos meilleures recettes de cuisine.")
    
    if sheet:
        try:
            notes_count = len(sheet.worksheet("Notes").get_all_records())
            recettes_count = len(sheet.worksheet("Recettes").get_all_records())
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric(label="📌 Notes partagées", value=notes_count)
            with col2:
                st.metric(label="🍲 Recettes enregistrées", value=recettes_count)
                
            st.divider()
            st.info("💡 **Astuce mobile :** Vous pouvez ajouter cette application sur l'écran d'accueil de votre téléphone pour l'utiliser comme une vraie application native !")
        except Exception as e:
            st.warning("Impossible de charger les statistiques d'accueil pour le moment.")
    else:
        st.warning("⚠️ Connexion Google Sheets requise.")
        st.write("Pour activer l'application, déposez votre fichier de clé JSON ci-dessous :")
        
        uploaded_json = st.file_uploader("Fichier JSON de configuration", type=["json"])
        if uploaded_json is not None:
            connected_sheet = connect_with_file(uploaded_json)
            if connected_sheet:
                st.session_state["uploaded_sheet_data"] = connected_sheet
                st.success("Connexion réussie ! Actualisation en cours...")
                st.rerun()
            else:
                st.error("Impossible de se connecter avec ce fichier. Vérifiez qu'il s'agit bien de la bonne clé Google Cloud.")

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
# ONGLET 2 : NOTES
# ==========================================
with tab_notes:
    st.header("Nos Notes Partagées")
    
    if sheet:
        try:
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
                        if st.button("🗑️ Supprimer cette note", key=f"del_note_{index}"):
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
                    st.success("Note ajoutée avec succès !")
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur avec l'onglet Notes : {e}")
    else:
        st.info("Veuillez d'abord connecter votre Google Sheet depuis l'onglet Accueil.")

# ==========================================
# ONGLET 3 : RECETTES
# ==========================================
with tab_recettes:
    st.header("Nos Recettes de Cuisine")
    
    if sheet:
        try:
            recettes_ws = sheet.worksheet("Recettes")
            all_recettes = recettes_ws.get_all_records()
            
            search_recette = st.text_input("🔍 Rechercher une recette ou un ingrédient", placeholder="Ex: Pâtes, chocolat...")
            
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
                    st.success("Recette ajoutée avec succès !")
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur avec l'onglet Recettes : {e}")
    else:
        st.info("Veuillez d'abord connecter votre Google Sheet depuis l'onglet Accueil.")
