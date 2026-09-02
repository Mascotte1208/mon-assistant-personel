import sys
import asyncio

# --- Correctif de stabilité asyncio pour Windows ---
if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

try:
    asyncio.get_running_loop()
except RuntimeError:
    asyncio.set_event_loop(asyncio.new_event_loop())

import time
import json
import os
import calendar
import re
from datetime import datetime, timedelta
import streamlit as st
from google import genai
from google.genai import types
from google.genai.errors import ServerError, ClientError
from streamlit_mic_recorder import mic_recorder

# Configuration de la page
st.set_page_config(page_title="Mon Assistant Personnel", layout="wide", page_icon="🤖")

# --- INITIALISATION SÉCURISÉE DE LA CLÉ API (Anti-Alerte GitHub) ---
try:
    api_key = st.secrets["GEMINI_API_KEY"]
except Exception:
    api_key = "VOTRE_CLE_DE_SECOURS"

client = genai.Client(api_key=api_key)

# --- SAUVEGARDE PERMANENTE LOCALE (JSON) ---
AGENDA_FILE = "agenda.json"
NOTES_FILE = "notes.json"
TASKS_FILE = "tasks.json"
RECIPES_FILE = "recipes.json"
GROCERY_FILE = "grocery.json"

MONTH_MAP = {
    "janvier": 1, "février": 2, "fevrier": 2, "mars": 3, "avril": 4, "mai": 5, "juin": 6,
    "juillet": 7, "août": 8, "aout": 8, "septembre": 9, "octobre": 10, "novembre": 11, "décembre": 12, "decembre": 12
}

def parse_event_date(date_str):
    """Tente de convertir une chaîne en date datetime.date. Retourne None si invalide."""
    if not isinstance(date_str, str) or not date_str.strip():
        return None
    try:
        return datetime.strptime(date_str.strip(), "%Y-%m-%d").date()
    except ValueError:
        return None

def parse_french_date(text):
    """Extrait une date au format français depuis le texte."""
    today = datetime.now().date()
    
    match_digits = re.search(r"(\d{1,2})[/.-](\d{1,2})(?:[/.-](\d{2,4}))?", text)
    if match_digits:
        day = int(match_digits.group(1))
        month = int(match_digits.group(2))
        year = int(match_digits.group(3)) if match_digits.group(3) else today.year
        if year < 100: year += 2000
        try:
            return datetime(year, month, day).date()
        except ValueError:
            pass

    match_text = re.search(r"(\d{1,2})\s+([a-zA-ö]+)(?:\s+(\d{4}))?", text.lower())
    if match_text:
        day = int(match_text.group(1))
        month_str = match_text.group(2)
        year = int(match_text.group(3)) if match_text.group(3) else today.year
        if month_str in MONTH_MAP:
            month = MONTH_MAP[month_str]
            try:
                return datetime(year, month, day).date()
            except ValueError:
                pass

    return None

def load_data(filepath):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
                return []
        except Exception:
            return []
    return []

def save_data(filepath, data):
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def clean_json_response(raw_text):
    """Nettoie le texte reçu pour isoler le JSON sans casser la syntaxe."""
    txt = raw_text.strip()
    if txt.startswith("```"):
        lines = txt.splitlines()
        if len(lines) >= 2 and lines[0].startswith("```"):
            txt = "\n".join(lines[1:-1]) if lines[-1].startswith("```") else "\n".join(lines[1:])
    return txt.strip()

def combine_quantities(text1, text2):
    """Combine deux textes d'ingrédients en additionnant les chiffres si possible."""
    match1 = re.match(r"^(\d+(?:[\.,]\d+)?)\s*([a-zA-Z]*)\s+(.*)$", text1.strip())
    match2 = re.match(r"^(\d+(?:[\.,]\d+)?)\s*([a-zA-Z]*)\s+(.*)$", text2.strip())
    
    if match1 and match2:
        val1, unit1, name1 = match1.groups()
        val2, unit2, name2 = match2.groups()
        
        if name1.lower() == name2.lower() and unit1.lower() == unit2.lower():
            total = float(val1.replace(',', '.')) + float(val2.replace(',', '.'))
            total_str = int(total) if total.is_integer() else round(total, 2)
            unit_space = " " if unit1 else ""
            return f"{total_str}{unit_space}{unit1} {name1}".strip()
            
    return text1

def add_ingredient_smart(grocery_list, new_ing, recipe_name):
    """Ajoute un ingrédient à la liste de courses en évitant les doublons et en additionnant les quantités."""
    existing_idx = -1
    
    for idx, item in enumerate(grocery_list):
        if item.get("done"):
            continue
        
        t1 = re.sub(r"^\d+(?:[\.,]\d+)?\s*[a-zA-Z]*\s+", "", item["title"]).strip().lower()
        t2 = re.sub(r"^\d+(?:[\.,]\d+)?\s*[a-zA-Z]*\s+", "", new_ing).strip().lower()
        
        if t1 == t2 or item["title"].strip().lower() == new_ing.strip().lower():
            existing_idx = idx
            break

    if existing_idx >= 0:
        old_title = grocery_list[existing_idx]["title"]
        combined_title = combine_quantities(old_title, new_ing)
        grocery_list[existing_idx]["title"] = combined_title
        
        curr_rec = grocery_list[existing_idx].get("recipe", "")
        if recipe_name and recipe_name not in curr_rec:
            grocery_list[existing_idx]["recipe"] = f"{curr_rec}, {recipe_name}" if curr_rec else recipe_name
    else:
        grocery_list.append({"title": new_ing, "done": False, "recipe": recipe_name})

def safe_generate_content(contents):
    """Appelle Gemini avec gestion intelligente des limites de quota."""
    max_retries = 1
    for attempt in range(max_retries):
        try:
            return client.models.generate_content(
                model="gemini-3.6-flash",
                contents=contents
            )
        except ClientError as e:
            if getattr(e, 'code', None) == 429 or "429" in str(e) or "RESOURCE_EXHAUSTED" in str(e):
                st.warning("⚡ Quota d'IA temporairement atteint. Passage en mode local.")
                break
            else:
                st.error(f"Erreur client API : {e}")
                break
        except ServerError as e:
            st.error("⚠️ Serveurs de l'IA indisponibles actuellement.")
            break
        except Exception as e:
            st.error(f"Erreur inattendue : {e}")
            break

    return type('DummyResponse', (), {'text': '{"type": "none"}'})()

# Initialisation des variables de session
if "folders" not in st.session_state:
    st.session_state.folders = {"Général": []}

if "current_folder" not in st.session_state:
    st.session_state.current_folder = "Général"

if "events" not in st.session_state:
    raw_events = load_data(AGENDA_FILE)
    st.session_state.events = [e for e in raw_events if isinstance(e, dict) and parse_event_date(e.get("date")) is not None]

if "notes" not in st.session_state:
    st.session_state.notes = load_data(NOTES_FILE)

if "tasks" not in st.session_state:
    st.session_state.tasks = load_data(TASKS_FILE)

if "recipes" not in st.session_state:
    st.session_state.recipes = load_data(RECIPES_FILE)

if "grocery" not in st.session_state:
    st.session_state.grocery = load_data(GROCERY_FILE)

if "main_navigation" not in st.session_state:
    st.session_state.main_navigation = "📊 Dashboard"

if "theme" not in st.session_state:
    st.session_state.theme = "Clair"

# COULEURS DES CATÉGORIES
CATEGORY_COLORS = {
    "Général": "#4B5563",
    "Perso": "#3B82F6",
    "Pro": "#8B5CF6",
    "Santé": "#EC4899",
    "Anniversaire": "#F59E0B",
    "Sport": "#10B981"
}

# --- APPLIQUER LE THÈME ---
if st.session_state.theme == "Agenda Kraft":
    st.markdown("""
        <style>
        .stApp { background-color: #F7F1E5; color: #4A3E3D; }
        div[data-testid="stSidebar"] { background-color: #E7D4B5; }
        </style>
    """, unsafe_allow_html=True)
elif st.session_state.theme == "Sombre":
    st.markdown("""
        <style>
        .stApp { background-color: #1E1E2E; color: #CDD6F4; }
        div[data-testid="stSidebar"] { background-color: #181825; }
        </style>
    """, unsafe_allow_html=True)

# --- BARRE LATÉRALE ---
with st.sidebar:
    st.title("🤖 Mon Assistant")
    
    st.subheader("📌 Navigation")
    nav_options = [
        "📊 Dashboard", 
        "💬 Discussion & Fichiers", 
        "📖 Mon Agenda", 
        "📝 Mes Notes", 
        "✅ Tâches (To-Do)", 
        "🛒 Recettes & Courses",
        "🔍 Recherche & Export"
    ]
    st.session_state.main_navigation = st.radio(
        "Accès rapide :",
        nav_options,
        index=nav_options.index(st.session_state.main_navigation) if st.session_state.main_navigation in nav_options else 0
    )

    st.divider()

    st.subheader("🎨 Personnalisation")
    st.session_state.theme = st.selectbox(
        "Style d'interface :", 
        ["Clair", "Sombre", "Agenda Kraft"], 
        index=["Clair", "Sombre", "Agenda Kraft"].index(st.session_state.theme)
    )

    st.divider()

    st.subheader("📁 Mes Projets")
    new_folder = st.text_input("Nouveau dossier :")
    if st.button("➕ Créer un dossier", use_container_width=True):
        if new_folder and new_folder not in st.session_state.folders:
            st.session_state.folders[new_folder] = []
            st.session_state.current_folder = new_folder
            st.rerun()

    selected_folder = st.radio(
        "Dossier actif :",
        options=list(st.session_state.folders.keys()),
        index=list(st.session_state.folders.keys()).index(st.session_state.current_folder)
    )
    st.session_state.current_folder = selected_folder

    st.divider()
    
    st.subheader("🎙️ Commande vocale")
    audio = mic_recorder(
        start_prompt="Cliquez pour parler",
        stop_prompt="Cliquez pour envoyer",
        key='recorder'
    )


# ==================== PAGE 0 : DASHBOARD ====================
if st.session_state.main_navigation == "📊 Dashboard":
    st.title("📊 Tableau de Bord")
    st.caption(f"Aujourd'hui : **{datetime.now().strftime('%A %d %B %Y')}**")

    col_m1, col_m2, col_m3, col_m4 = st.columns(4)
    col_m1.metric("Événements", len(st.session_state.events))
    tasks_pending = len([t for t in st.session_state.tasks if not t.get("done", False)])
    col_m2.metric("Tâches à faire", tasks_pending)
    col_m3.metric("Notes", len(st.session_state.notes))
    courses_en_cours = len([g for g in st.session_state.grocery if not g.get("done", False)])
    col_m4.metric("Articles à acheter", courses_en_cours)

    st.divider()

    col_dash1, col_dash2 = st.columns(2)

    with col_dash1:
        st.subheader("🔔 Prochains Événements (3 prochains jours)")
        today = datetime.now().date()
        next_days = [today + timedelta(days=i) for i in range(4)]
        
        upcoming_events = [
            e for e in st.session_state.events 
            if parse_event_date(e.get("date")) in next_days
        ]

        if upcoming_events:
            for ev in upcoming_events:
                color = CATEGORY_COLORS.get(ev.get("category", "Général"), "#3B82F6")
                time_str = ev.get('time', '00:00') or '00:00'
                st.markdown(
                    f"""
                    <div style="background-color: #f8f9fa; padding: 10px; border-radius: 8px; border-left: 6px solid {color}; margin-bottom: 8px;">
                        <strong style="color: #111;">📅 {ev['date']} à {time_str[:5]}</strong> — <span style="color: #222;">{ev.get('title', 'Sans titre')}</span> <em>({ev.get('category', 'Général')})</em>
                    </div>
                    """, unsafe_allow_html=True
                )
        else:
            st.info("Aucun événement prévu pour les 3 prochains jours.")

    with col_dash2:
        st.subheader("✅ Tâches prioritaires à faire")
        pending_tasks = [t for t in st.session_state.tasks if not t.get("done", False)]
        
        if pending_tasks:
            for idx_dt, task in enumerate(pending_tasks[:6]):
                col_chk, col_txt = st.columns([1, 9])
                with col_chk:
                    chk = st.checkbox("", value=False, key=f"dash_task_{idx_dt}")
                    if chk:
                        real_idx = st.session_state.tasks.index(task)
                        st.session_state.tasks[real_idx]["done"] = True
                        save_data(TASKS_FILE, st.session_state.tasks)
                        st.rerun()
                with col_txt:
                    st.markdown(f"**{task['title']}**")
        else:
            st.success("Toutes vos tâches sont accomplies !")

    st.divider()

    col_d1, col_d2 = st.columns(2)
    with col_d1:
        st.subheader("🛒 Liste de courses rapide")
        if st.session_state.grocery:
            for item in st.session_state.grocery[:5]:
                status = "✅" if item.get("done") else "🛒"
                st.markdown(f"{status} **{item['title']}**")
        else:
            st.caption("Liste de courses vide.")
    
    with col_d2:
        st.subheader("🍳 Idées Recettes enregistrées")
        if st.session_state.recipes:
            for r in st.session_state.recipes[:5]:
                st.markdown(f"• **{r['title']}**")
        else:
            st.caption("Aucune recette enregistrée.")


# ==================== PAGE 1 : CHAT & DISCUSSIONS ====================
elif st.session_state.main_navigation == "💬 Discussion & Fichiers":
    st.title(f"📂 Projet : {st.session_state.current_folder}")

    uploaded_file = st.file_uploader(
        "📎 Déposez un document ou une image (PDF, PNG, JPG, TXT)",
        type=["pdf", "png", "jpg", "jpeg", "txt"]
    )

    current_messages = st.session_state.folders[st.session_state.current_folder]

    for message in current_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    prompt = st.chat_input("Ex: 'Crée un événement Permis de conduire le 20 septembre'...")

    user_text = None

    if audio:
        audio_bytes = audio['bytes']
        if "last_audio" not in st.session_state or st.session_state.last_audio != audio_bytes:
            st.session_state.last_audio = audio_bytes
            current_messages.append({"role": "user", "content": "🎙️ *Message vocal envoyé*"})
            
            res = safe_generate_content(
                contents=[
                    types.Part.from_bytes(data=audio_bytes, mime_type="audio/wav"),
                    "Transcris exactement le texte de cet enregistrement vocal sans rien ajouter."
                ]
            )
            user_text = res.text
    elif prompt:
        user_text = prompt
        user_display = f"📄 **[{uploaded_file.name}]**\n\n{prompt}" if uploaded_file else prompt
        current_messages.append({"role": "user", "content": user_display})
        with st.chat_message("user"):
            st.markdown(user_display)

    if user_text:
        today_str = datetime.now().strftime("%Y-%m-%d")
        today_date = datetime.now().date()
        parsed = False

        txt_lower = user_text.lower()
        extracted_date = parse_french_date(txt_lower)
        
        # Détection des TÂCHES
        if "tâche" in txt_lower or "tache" in txt_lower or "a faire" in txt_lower or "à faire" in txt_lower or "penser à" in txt_lower or "penser a" in txt_lower:
            clean_task = user_text
            clean_task = re.sub(r"(?i)^(crée|ajouter|rajoute|met|mets|penser à|penser a)\s+(une|la)?\s*(tâche|tache)?\s*", "", clean_task).strip().capitalize()
            if clean_task:
                st.session_state.tasks.append({"title": clean_task, "done": False})
                save_data(TASKS_FILE, st.session_state.tasks)
                confirmation = f"✅ Tâche ajoutée à votre liste : **{clean_task}** !"
                with st.chat_message("assistant"): st.markdown(confirmation)
                current_messages.append({"role": "assistant", "content": confirmation})
                parsed = True

        # Détection des ÉVÉNEMENTS AGENDA
        elif extracted_date or "evenement" in txt_lower or "événement" in txt_lower or "agenda" in txt_lower or "piscine" in txt_lower or "permis" in txt_lower or "football" in txt_lower:
            target_date = extracted_date if extracted_date else today_date
            
            clean_title = user_text
            clean_title = re.sub(r"(?i)^(crée|ajouter|met|mets|programme|planifie)\s+(un|l'|le|la)?\s*(événement|evenement)?\s*", "", clean_title)
            clean_title = re.sub(r"(?i)\s*(le|pour le)?\s*\d{1,2}\s+[a-zA-ö]+.*", "", clean_title)
            clean_title = clean_title.strip().capitalize()
            if not clean_title: clean_title = "Événement"

            cat = "Pro" if "permis" in txt_lower else ("Sport" if "piscine" in txt_lower or "football" in txt_lower else "Général")

            if any(k in txt_lower for k in ["tous les 2 jours", "tous les deux jours", "tous les deus jors"]):
                added_dates = []
                for i in range(15):
                    curr_d = target_date + timedelta(days=i * 2)
                    st.session_state.events.append({"title": clean_title, "date": str(curr_d), "time": "10:00", "category": cat})
                    added_dates.append(str(curr_d))
                confirmation = f"✅ **15 séances de {clean_title}** ajoutées à votre agenda (du **{added_dates[0]}** au **{added_dates[-1]}**)."
            else:
                st.session_state.events.append({"title": clean_title, "date": str(target_date), "time": "09:00", "category": cat})
                confirmation = f"✅ Événement ajouté à votre agenda : **{clean_title}** le **{target_date}** !"

            save_data(AGENDA_FILE, st.session_state.events)
            with st.chat_message("assistant"): st.markdown(confirmation)
            current_messages.append({"role": "assistant", "content": confirmation})
            parsed = True

        if not parsed:
            recipes_context = json.dumps([{"title": r["title"], "ingredients": r["ingredients"]} for r in st.session_state.recipes], ensure_ascii=False)
            
            extraction_prompt = (
                f"Aujourd'hui nous sommes le {today_str}.\n"
                f"Voici les recettes connues du carnet : {recipes_context}.\n"
                f"Analyse le texte suivant : '{user_text}'. "
                "1. S'il demande d'ajouter la liste de courses pour un plat/recette connu(e), réponds JSON : {\"type\": \"meal_grocery\", \"recipe_title\": \"Nom du plat\"}.\n"
                "2. S'il s'agit d'un AGENDA, réponds JSON : {\"type\": \"agenda\", \"title\": \"Titre\", \"date\": \"YYYY-MM-DD\", \"time\": \"HH:MM\", \"category\": \"Général\"}.\n"
                "3. S'il s'agit d'une NOTE, réponds JSON : {\"type\": \"note\", \"title\": \"Titre\", \"content\": \"Contenu\"}.\n"
                "4. S'il s'agit d'une TÂCHE, réponds JSON : {\"type\": \"task\", \"title\": \"Titre\"}.\n"
                "5. Sinon, réponds JSON : {\"type\": \"none\"}."
            )
            
            check_res = safe_generate_content(contents=[extraction_prompt])
            
            try:
                clean_json = clean_json_response(check_res.text)
                data = json.loads(clean_json)
                
                if data.get("type") == "meal_grocery":
                    plat_demande = data.get("recipe_title", "").lower()
                    recette_trouvee = next((r for r in st.session_state.recipes if plat_demande in r["title"].lower() or r["title"].lower() in plat_demande), None)
                    if recette_trouvee:
                        for ing in recette_trouvee["ingredients"]:
                            add_ingredient_smart(st.session_state.grocery, ing, recette_trouvee["title"])
                        save_data(GROCERY_FILE, st.session_state.grocery)
                        confirmation = f"🛒 Ingrédients pour **{recette_trouvee['title']}** fusionnés dans votre liste !"
                    else:
                        confirmation = f"⚠️ Je n'ai pas trouvé la recette de '{data.get('recipe_title')}'."
                    
                    with st.chat_message("assistant"): st.markdown(confirmation)
                    current_messages.append({"role": "assistant", "content": confirmation})
                    parsed = True

                elif data.get("type") == "agenda":
                    event_date = data.get("date") or today_str
                    new_ev = {"title": data.get("title", "Événement"), "date": str(event_date), "time": str(data.get("time") or "09:00"), "category": data.get("category", "Général")}
                    st.session_state.events.append(new_ev)
                    save_data(AGENDA_FILE, st.session_state.events)
                    confirmation = f"✅ Événement ajouté : **{new_ev['title']}** le **{new_ev['date']}** à **{new_ev['time']}**."
                    with st.chat_message("assistant"): st.markdown(confirmation)
                    current_messages.append({"role": "assistant", "content": confirmation})
                    parsed = True

                elif data.get("type") == "task":
                    new_task = {"title": data.get("title", "Tâche"), "done": False}
                    st.session_state.tasks.append(new_task)
                    save_data(TASKS_FILE, st.session_state.tasks)
                    confirmation = f"✅ Tâche ajoutée : **{new_task['title']}**."
                    with st.chat_message("assistant"): st.markdown(confirmation)
                    current_messages.append({"role": "assistant", "content": confirmation})
                    parsed = True

            except Exception:
                parsed = False

        if not parsed:
            contents_payload = []
            if uploaded_file is not None:
                file_bytes = uploaded_file.read()
                mime_type = uploaded_file.type
                contents_payload.append(types.Part.from_bytes(data=file_bytes, mime_type=mime_type))
            contents_payload.append(user_text)

            response = safe_generate_content(contents=contents_payload)
            with st.chat_message("assistant"):
                st.markdown(response.text)
            current_messages.append({"role": "assistant", "content": response.text})


# ==================== PAGE 2 : AGENDA ACCÈS DIRECT ====================
elif st.session_state.main_navigation == "📖 Mon Agenda":
    st.title("📖 Mon Agenda Interactif")
    
    st.subheader("➕ Ajouter un événement manuellement")
    col_a, col_b, col_c, col_cat, col_rep = st.columns([3, 2, 2, 2, 2])
    with col_a:
        ev_title = st.text_input("Titre :", key="ev_title")
    with col_b:
        ev_date = st.date_input("Date de début :", key="ev_date")
    with col_c:
        ev_time = st.time_input("Heure :", key="ev_time")
    with col_cat:
        ev_cat = st.selectbox("Catégorie :", list(CATEGORY_COLORS.keys()), key="ev_cat")
    with col_rep:
        ev_repeat = st.selectbox("Répétition :", ["Une seule fois", "Tous les 2 jours", "Toutes les semaines", "Tous les mois"], key="ev_repeat")

    if st.button("📌 Enregistrer l'événement", use_container_width=True):
        if ev_title:
            repeat_days = 1
            repeat_count = 1
            
            if ev_repeat == "Tous les 2 jours":
                repeat_days = 2
                repeat_count = 15
            elif ev_repeat == "Toutes les semaines":
                repeat_days = 7
                repeat_count = 12
            elif ev_repeat == "Tous les mois":
                repeat_days = 30
                repeat_count = 12

            for i in range(repeat_count):
                curr_d = ev_date + timedelta(days=i * repeat_days)
                new_ev = {
                    "title": ev_title,
                    "date": str(curr_d),
                    "time": str(ev_time)[:5],
                    "category": ev_cat
                }
                st.session_state.events.append(new_ev)

            save_data(AGENDA_FILE, st.session_state.events)
            st.success(f"{repeat_count} événement(s) enregistré(s) !")
            st.rerun()

    st.divider()

    mois_noms = [
        "Janvier", "Février", "Mars", "Avril", "Mai", "Juin", 
        "Juillet", "Août", "Septembre", "Octobre", "Novembre", "Décembre"
    ]
    
    annee_actuelle = datetime.now().year
    selected_month_num = st.session_state.get("selected_month", datetime.now().month)

    st.subheader("🗓️ Choisir le mois")
    cols_mois = st.columns(6)
    for idx, nom in enumerate(mois_noms):
        m_num = idx + 1
        with cols_mois[idx % 6]:
            is_selected = (m_num == selected_month_num)
            label = f"⭐ {nom}" if is_selected else nom
            if st.button(label, key=f"month_btn_{m_num}", use_container_width=True):
                st.session_state.selected_month = m_num
                st.rerun()

    st.divider()

    nom_mois_choisi = mois_noms[selected_month_num - 1]
    
    evs_mois = []
    for e in st.session_state.events:
        p_date = parse_event_date(e.get("date"))
        if p_date and p_date.month == selected_month_num:
            evs_mois.append(e)

    st.markdown(f"## 📖 **{nom_mois_choisi} {annee_actuelle}** ({len(evs_mois)} événement(s))")

    cal = calendar.Calendar(firstweekday=0)
    month_days = cal.monthdatescalendar(annee_actuelle, selected_month_num)

    jours_semaine = ["Lun", "Mar", "Mer", "Jeu", "Ven", "Sam", "Dim"]
    cols_header = st.columns(7)
    for i, h in enumerate(jours_semaine):
        cols_header[i].markdown(f"### **{h}**")

    for week in month_days:
        cols_day = st.columns(7)
        for i, day in enumerate(week):
            with cols_day[i]:
                if day.month == selected_month_num:
                    st.markdown(f"#### **{day.day}**")
                    evs_jour = [e for e in st.session_state.events if e.get("date") == str(day)]
                    for idx_e, e in enumerate(evs_jour):
                        border_color = CATEGORY_COLORS.get(e.get("category", "Général"), "#FF4B4B")
                        time_display = (e.get("time") or "00:00")[:5]
                        st.markdown(
                            f"""
                            <div style="background-color: #f0f2f6; padding: 6px; border-radius: 6px; margin-bottom: 5px; border-left: 5px solid {border_color};">
                                <strong style="color: #31333F;">🕒 {time_display}</strong><br/>
                                <span style="color: #111;">{e.get('title', 'Événement')}</span>
                            </div>
                            """, 
                            unsafe_allow_html=True
                        )
                        if st.button("🗑️", key=f"del_{day}_{idx_e}"):
                            st.session_state.events.remove(e)
                            save_data(AGENDA_FILE, st.session_state.events)
                            st.rerun()
                else:
                    st.caption(f"<span style='opacity: 0.3;'>{day.day}</span>", unsafe_allow_html=True)


# ==================== PAGE 3 : MES NOTES ====================
elif st.session_state.main_navigation == "📝 Mes Notes":
    st.title("📝 Mes Notes & Pense-bêtes")

    st.subheader("➕ Créer une nouvelle note")
    col_n1, col_n2 = st.columns([1, 2])
    with col_n1:
        note_title = st.text_input("Titre de la note :", key="note_title_input")
    with col_n2:
        note_content = st.text_area("Contenu de la note :", key="note_content_input", height=100)

    if st.button("📌 Enregistrer la note", use_container_width=True):
        if note_title:
            now_str = datetime.now().strftime("%d/%m/%Y à %H:%M")
            new_note = {
                "title": note_title,
                "content": note_content,
                "date": now_str
            }
            st.session_state.notes.append(new_note)
            save_data(NOTES_FILE, st.session_state.notes)
            st.success("Note enregistrée avec succès !")
            st.rerun()

    st.divider()

    st.subheader(f"📋 Vos Notes Enregistrées ({len(st.session_state.notes)})")

    if not st.session_state.notes:
        st.info("Vous n'avez pas encore de note enregistrée.")
    else:
        cols_notes = st.columns(2)
        for idx_n, note in enumerate(reversed(st.session_state.notes)):
            with cols_notes[idx_n % 2]:
                with st.expander(f"📌 **{note['title']}** (créée le {note['date']})", expanded=True):
                    st.write(note["content"])
                    if st.button("🗑️ Supprimer la note", key=f"del_note_{idx_n}"):
                        st.session_state.notes.remove(note)
                        save_data(NOTES_FILE, st.session_state.notes)
                        st.rerun()


# ==================== PAGE 4 : TÂCHES (TO-DO) ====================
elif st.session_state.main_navigation == "✅ Tâches (To-Do)":
    st.title("✅ Gestionnaire de Tâches")

    col_t1, col_t2 = st.columns([3, 1])
    with col_t1:
        new_task_title = st.text_input("Ajouter une tâche à accomplir :", key="new_task_input")
    with col_t2:
        st.write("")
        st.write("")
        if st.button("➕ Ajouter la tâche", use_container_width=True):
            if new_task_title:
                st.session_state.tasks.append({"title": new_task_title, "done": False})
                save_data(TASKS_FILE, st.session_state.tasks)
                st.rerun()

    st.divider()

    if not st.session_state.tasks:
        st.info("Aucune tâche en cours.")
    else:
        st.subheader("📋 Vos tâches")
        for idx_t, task in enumerate(st.session_state.tasks):
            col_check, col_txt, col_del = st.columns([1, 8, 1])
            
            with col_check:
                is_done = st.checkbox("", value=task.get("done", False), key=f"task_check_{idx_t}")
                if is_done != task.get("done"):
                    st.session_state.tasks[idx_t]["done"] = is_done
                    save_data(TASKS_FILE, st.session_state.tasks)
                    st.rerun()

            with col_txt:
                if task.get("done"):
                    st.markdown(f"~~{task['title']}~~")
                else:
                    st.markdown(f"**{task['title']}**")

            with col_del:
                if st.button("🗑️", key=f"del_task_{idx_t}"):
                    st.session_state.tasks.pop(idx_t)
                    save_data(TASKS_FILE, st.session_state.tasks)
                    st.rerun()


# ==================== PAGE 5 : RECETTES & COURSES ====================
elif st.session_state.main_navigation == "🛒 Recettes & Courses":
    st.title("🛒 Carnet de Recettes & Liste de Courses")

    tab_r1, tab_r2 = st.tabs(["🛒 Liste de Courses", "🍳 Mes Recettes"])

    with tab_r1:
        st.subheader("➕ Ajouter un article à la liste de courses")
        col_g1, col_g2 = st.columns([3, 1])
        with col_g1:
            new_grocery_item = st.text_input("Article :", key="new_grocery_input")
        with col_g2:
            st.write("")
            st.write("")
            if st.button("🛒 Ajouter l'article", use_container_width=True):
                if new_grocery_item:
                    add_ingredient_smart(st.session_state.grocery, new_grocery_item, "Manuel")
                    save_data(GROCERY_FILE, st.session_state.grocery)
                    st.rerun()

        st.divider()

        if not st.session_state.grocery:
            st.info("Votre liste de courses est vide.")
        else:
            col_head1, col_head2, col_head3 = st.columns([3, 1, 1])
            with col_head1:
                st.subheader("🛒 Votre Liste de Courses")
            with col_head2:
                if st.button("🔄 Regrouper doublons", use_container_width=True):
                    old_list = st.session_state.grocery.copy()
                    new_list = []
                    for item in old_list:
                        add_ingredient_smart(new_list, item["title"], item.get("recipe", ""))
                    st.session_state.grocery = new_list
                    save_data(GROCERY_FILE, st.session_state.grocery)
                    st.success("Doublons regroupés !")
                    st.rerun()
            with col_head3:
                if st.button("🧹 Vider cochés", use_container_width=True):
                    st.session_state.grocery = [g for g in st.session_state.grocery if not g.get("done")]
                    save_data(GROCERY_FILE, st.session_state.grocery)
                    st.rerun()

            for idx_g, item in enumerate(st.session_state.grocery):
                col_c, col_t, col_del = st.columns([1, 8, 1])
                with col_c:
                    chk = st.checkbox("", value=item.get("done", False), key=f"grocery_chk_{idx_g}")
                    if chk != item.get("done"):
                        st.session_state.grocery[idx_g]["done"] = chk
                        save_data(GROCERY_FILE, st.session_state.grocery)
                        st.rerun()
                with col_t:
                    tag = f" *(Recette: {item.get('recipe')})*" if item.get("recipe") else ""
                    if item.get("done"):
                        st.markdown(f"~~{item['title']}~~{tag}")
                    else:
                        st.markdown(f"**{item['title']}**{tag}")
                with col_del:
                    if st.button("🗑️", key=f"del_g_{idx_g}"):
                        st.session_state.grocery.pop(idx_g)
                        save_data(GROCERY_FILE, st.session_state.grocery)
                        st.rerun()

    with tab_r2:
        st.subheader("📖 Ajouter une nouvelle recette au carnet")
        rec_title = st.text_input("Nom du plat (ex: Lasagnes, Tarte aux pommes) :", key="rec_title_in")
        rec_ing = st.text_area("Ingrédients (un par ligne) :", key="rec_ing_in", placeholder="500g de viande hachée\nPâtes à lasagne\nSauce tomate\nMozzarella")
        
        if st.button("📌 Enregistrer la recette", use_container_width=True):
            if rec_title and rec_ing:
                ing_list = [i.strip() for i in rec_ing.splitlines() if i.strip()]
                st.session_state.recipes.append({"title": rec_title, "ingredients": ing_list})
                save_data(RECIPES_FILE, st.session_state.recipes)
                st.success(f"Recette '{rec_title}' enregistrée !")
                st.rerun()

        st.divider()

        st.subheader("📚 Vos Recettes Enregistrées")
        if not st.session_state.recipes:
            st.info("Aucune recette enregistrée pour le moment.")
        else:
            cols_r = st.columns(2)
            for idx_r, rec in enumerate(st.session_state.recipes):
                with cols_r[idx_r % 2]:
                    with st.expander(f"🍳 **{rec['title']}** ({len(rec['ingredients'])} ingrédients)", expanded=False):
                        for ing in rec["ingredients"]:
                            st.write(f"- {ing}")
                        
                        col_btn1, col_btn2 = st.columns(2)
                        with col_btn1:
                            if st.button("🛒 Envoyer aux courses", key=f"send_g_{idx_r}", use_container_width=True):
                                for ing in rec["ingredients"]:
                                    add_ingredient_smart(st.session_state.grocery, ing, rec["title"])

                                save_data(GROCERY_FILE, st.session_state.grocery)
                                st.success("Ingrédients fusionnés sans doublons !")
                                st.rerun()

                        with col_btn2:
                            if st.button("🗑️ Supprimer", key=f"del_r_{idx_r}", use_container_width=True):
                                st.session_state.recipes.pop(idx_r)
                                save_data(RECIPES_FILE, st.session_state.recipes)
                                st.rerun()


# ==================== PAGE 6 : RECHERCHE & EXPORT ====================
elif st.session_state.main_navigation == "🔍 Recherche & Export":
    st.title("🔍 Recherche Globale & Sauvegarde")

    search_query = st.text_input("🔍 Rechercher un événement, une note ou une recette :")

    if search_query:
        st.subheader("Résultats dans l'Agenda")
        found_events = [e for e in st.session_state.events if search_query.lower() in e.get('title', '').lower()]
        if found_events:
            for e in found_events:
                time_disp = (e.get("time") or "00:00")[:5]
                st.write(f"📅 **{e.get('date')}** à {time_disp} — {e.get('title')}")
        else:
            st.caption("Aucun événement correspondant.")

        st.subheader("Résultats dans les Notes")
        found_notes = [n for n in st.session_state.notes if search_query.lower() in n.get('title', '').lower() or search_query.lower() in n.get('content', '').lower()]
        if found_notes:
            for n in found_notes:
                st.write(f"📝 **{n.get('title')}** ({n.get('date')}) : {n.get('content')}")
        else:
            st.caption("Aucune note correspondante.")

    st.divider()

    st.subheader("💾 Exporter & Sauvegarder vos données")
    st.caption("Téléchargez l'ensemble de vos données au format JSON pour en garder une copie de sauvegarde.")

    col_exp1, col_exp2, col_exp3, col_exp4 = st.columns(4)
    
    with col_exp1:
        st.download_button(
            label="📥 Exporter l'Agenda",
            data=json.dumps(st.session_state.events, ensure_ascii=False, indent=2),
            file_name="agenda_backup.json",
            mime="application/json"
        )

    with col_exp2:
        st.download_button(
            label="📥 Exporter les Notes",
            data=json.dumps(st.session_state.notes, ensure_ascii=False, indent=2),
            file_name="notes_backup.json",
            mime="application/json"
        )

    with col_exp3:
        st.download_button(
            label="📥 Exporter les Tâches",
            data=json.dumps(st.session_state.tasks, ensure_ascii=False, indent=2),
            file_name="tasks_backup.json",
            mime="application/json"
        )

    with col_exp4:
        st.download_button(
            label="📥 Exporter les Recettes",
            data=json.dumps(st.session_state.recipes, ensure_ascii=False, indent=2),
            file_name="recipes_backup.json",
            mime="application/json"
        )
