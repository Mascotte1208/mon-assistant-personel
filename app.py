import streamlit as st
import pandas as pd
import gspread
from datetime import datetime

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
        font-size: 14px;
    }
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    </style>
""", unsafe_allow_html=True)

# --- CONNEXION GOOGLE SHEETS SIMPLIFIÉE ---
@st.cache_resource
def get_sheet_connection(sheet_url):
    try:
        client = gspread.service_account(filename="secrets.json")
        sheet = client.open_by_url(sheet_url)
        return sheet
    except Exception:
        try:
            client = gspread.no_credentials()
            sheet = client.open_by_url(sheet_url)
            return sheet
        except Exception as e:
            return None

# --- EN-TÊTE DE LA PAGE ---
st.title("💡 Notre Tableau de Bord")
st.caption("Partagé en direct 🚀")

# Récupération de l'URL depuis les secrets ou la session
sheet_url = st.secrets.get("sheet_url", st.session_state.get("sheet_url", ""))

sheet = None
if sheet_url:
    sheet = get_sheet_connection(sheet_url)

# NAVIGATION PAR ONGLETS
tab_accueil, tab_agenda, tab_notes, tab_recettes = st.tabs(["🏠 Accueil", "📅 Agenda", "📝 Notes", "🍲 Recettes"])

# ==========================================
# ONGLET 0 : ACCUEIL
# ==========================================
with tab_accueil:
    st.header("Bienvenue sur votre espace !")
    st.write("Ce tableau de bord centralise votre agenda, vos notes et vos recettes partagées.")
    
    if not sheet_url:
        st.warning("⚠️ Veuillez configurer l'URL de votre Google Sheet.")
        new_url = st.text_input("Collez le lien de votre Google Sheet ici :")
        if new_url:
            st.session_state["sheet_url"] = new_url
            st.rerun()
    elif sheet:
        try:
            agenda_count = len(sheet.worksheet("Agenda").get_all_records()) if "Agenda" in [w.title for w in sheet.worksheets()] else 0
            notes_count = len(sheet.worksheet("Notes").get_all_records()) if "Notes" in [w.title for w in sheet.worksheets()] else 0
            recettes_count = len(sheet.worksheet("Recettes").get_all_records()) if "Recettes" in [w.title for w in sheet.worksheets()] else 0
            
            c1, c2, c3 = st.columns(3)
            with c1: st.metric(label="📅 Événements", value=agenda_count)
            with c2: st.metric(label="📌 Notes", value=notes_count)
            with c3: st.metric(label="🍲 Recettes", value=recettes_count)
            
            st.divider()
            st.info("💡 **Astuce mobile :** Ajoutez cette application à l'écran d'accueil de votre téléphone pour l'utiliser comme une appli native !")
        except Exception as e:
            st.warning(f"Connecté, mais structure des onglets incomplète : {e}")
    else:
        st.error("Impossible d'accéder au Google Sheet. Vérifiez que le lien est correct et accessible.")

# ==========================================
# ONGLET 1 : AGENDA
# ==========================================
with tab_agenda:
    st.header("📅 Agenda Partagé")
    
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
                st.write(f"*{len(all_events)} événement(s) prévu(s)*")
                for index, row in enumerate(all_events):
                    date_ev = row.get('Date', '')
                    heure_ev = row.get('Heure', '')
                    titre_ev = row.get('Titre', 'Sans titre')
                    desc_ev = row.get('Description', '')
                    
                    with st.expander(f"🗓️ {date_ev} à {heure_ev} - {titre_ev}"):
                        if desc_ev:
                            st.write(f"**Détails :** {desc_ev}")
                        if st.button("🗑️ Supprimer cet événement", key=f"del_ev_{index}"):
                            real_row_index = all_events.index(row) + 2
                            agenda_ws.delete_rows(real_row_index)
                            st.success("Événement supprimé !")
                            st.rerun()
            else:
                st.info("Aucun événement dans l'agenda pour l'instant.")
                
            st.divider()
            
            with st.form("form_agenda", clear_on_submit=True):
                st.subheader("➕ Ajouter un événement")
                e_date = st.date_input("Date de l'événement", value=datetime.today())
                e_heure = st.time_input("Heure", value=datetime.now().time())
                e_titre = st.text_input("Titre de l'événement")
                e_desc = st.text_area("Description (optionnel)")
                submitted_ev = st.form_submit_button("Ajouter à l'agenda")
                
                if submitted_ev and e_titre:
                    agenda_ws.append_row([str(e_date), str(e_heure.strftime("%H:%M")), e_titre, e_desc])
                    st.success("Événement ajouté avec succès !")
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur dans l'onglet Agenda : {e}")
    else:
        st.info("Veuillez d'abord configurer le lien Google Sheet dans l'accueil.")

# ==========================================
# ONGLET 2 : NOTES
# ==========================================
with tab_notes:
    st.header("Nos Notes Partagées")
    if sheet:
        try:
            notes_ws = sheet.worksheet("Notes")
            all_notes = notes_ws.get_all_records()
            
            search_note = st.text_input("🔍 Rechercher dans les notes", placeholder="Mot-clé...")
            filtered_notes = [n for n in all_notes if search_note.lower() in str(n.get('Titre','')).lower() or search_note.lower() in str(n.get('Contenu','')).lower()] if search_note else all_notes

            if filtered_notes:
                for index, row in enumerate(filtered_notes):
                    with st.expander(f"📌 {row.get('Titre', 'Sans titre')}"):
                        st.write(row.get('Contenu', ''))
                        if st.button("🗑️ Supprimer", key=f"del_n_{index}"):
                            notes_ws.delete_rows(all_notes.index(row) + 2)
                            st.rerun()
            else:
                st.info("Aucune note.")
                
            st.divider()
            with st.form("form_note", clear_on_submit=True):
                st.subheader("➕ Nouvelle note")
                n_titre = st.text_input("Titre")
                n_contenu = st.text_area("Contenu")
                if st.form_submit_button("Enregistrer") and n_titre:
                    notes_ws.append_row([n_titre, n_contenu])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.info("Connexion requise.")

# ==========================================
# ONGLET 3 : RECETTES
# ==========================================
with tab_recettes:
    st.header("Nos Recettes de Cuisine")
    if sheet:
        try:
            recettes_ws = sheet.worksheet("Recettes")
            all_recettes = recettes_ws.get_all_records()
            
            search_rec = st.text_input("🔍 Rechercher une recette", placeholder="Ex: Pâtes...")
            filtered_rec = [r for r in all_recettes if search_rec.lower() in str(r.get('Titre','')).lower()] if search_rec else all_recettes

            if filtered_rec:
                for index, row in enumerate(filtered_rec):
                    with st.expander(f"🍲 {row.get('Titre', 'Sans titre')}"):
                        st.markdown(f"**Ingrédients :**\n{row.get('Ingrédients', '')}")
                        st.markdown(f"**Instructions :**\n{row.get('Instructions', '')}")
                        if st.button("🗑️ Supprimer", key=f"del_r_{index}"):
                            recettes_ws.delete_rows(all_recettes.index(row) + 2)
                            st.rerun()
            else:
                st.info("Aucune recette.")
                
            st.divider()
            with st.form("form_recette", clear_on_submit=True):
                st.subheader("➕ Nouvelle recette")
                r_titre = st.text_input("Nom")
                r_ing = st.text_area("Ingrédients")
                r_inst = st.text_area("Instructions")
                if st.form_submit_button("Enregistrer") and r_titre:
                    recettes_ws.append_row([r_titre, r_ing, r_inst])
                    st.rerun()
        except Exception as e:
            st.error(f"Erreur : {e}")
    else:
        st.info("Connexion requise.")
