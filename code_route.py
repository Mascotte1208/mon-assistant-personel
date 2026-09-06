# ==========================================================
# Code de la Route Belge — Base Officielle & Rendu Visuel CSS
# ==========================================================
import random
import streamlit as st

PANNEAUX_OFFICIELS_BELGES = [
    # --- SÉRIE A : DANGER ---
    {"code": "A1a", "nom": "Virage dangereux à gauche", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé à gauche.", "forme": "triangle", "symbole": "↩️"},
    {"code": "A1b", "nom": "Virage dangereux à droite", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé à droite.", "forme": "triangle", "symbole": "↪️"},
    {"code": "A3", "nom": "Descente dangereuse", "cat": "Série A : Danger", "desc": "Indique une pente raide.", "forme": "triangle", "symbole": "📉"},
    {"code": "A5", "nom": "Montée à forte inclinaison", "cat": "Série A : Danger", "desc": "Indique une forte côte.", "forme": "triangle", "symbole": "📈"},
    {"code": "A7a", "nom": "Rétrécissement de la chaussée", "cat": "Série A : Danger", "desc": "Rétrécissement de la route des deux côtés.", "forme": "triangle", "symbole": "⮀"},
    {"code": "A15", "nom": "Chaussée glissante", "cat": "Série A : Danger", "desc": "Risque accru de glissade (pluie, verglas).", "forme": "triangle", "symbole": "💧"},
    {"code": "A21", "nom": "Passage pour piétons", "cat": "Série A : Danger", "desc": "Annonce un passage clouté à proximité.", "forme": "triangle", "symbole": "🚶"},
    {"code": "A23", "nom": "Endroit fréquenté par des enfants", "cat": "Série A : Danger", "desc": "Zone d'école ou aire de jeux à proximité.", "forme": "triangle", "symbole": "🚸"},
    {"code": "A31", "nom": "Travaux", "cat": "Série A : Danger", "desc": "Présence d'un chantier sur la voie publique.", "forme": "triangle", "symbole": "🚧"},
    {"code": "A33", "nom": "Feux de circulation", "cat": "Série A : Danger", "desc": "Annonce des feux tricolores en amont.", "forme": "triangle", "symbole": "🚦"},

    # --- SÉRIE B : PRIORITÉ ---
    {"code": "B1", "nom": "Cédez le passage", "cat": "Série B : Priorité", "desc": "Triangle blanc pointé vers le bas à bord rouge.", "forme": "triangle_inverse", "symbole": "🔻"},
    {"code": "B5", "nom": "Stop (Arrêt obligatoire)", "cat": "Série B : Priorité", "desc": "Obligation de marquer l'arrêt complet.", "forme": "octogone", "symbole": "STOP"},
    {"code": "B9", "nom": "Voie prioritaire", "cat": "Série B : Priorité", "desc": "Losange jaune : vous êtes prioritaire sur les intersections.", "forme": "losange", "symbole": "🔶"},
    {"code": "Général", "nom": "Priorité à droite", "cat": "Série B : Priorité", "desc": "Règle générale applicable à toute intersection.", "forme": "carre_blanc", "symbole": "➕"},

    # --- SÉRIE C : INTERDICTION ---
    {"code": "C1", "nom": "Interdiction de circuler dans les deux sens", "cat": "Série C : Interdiction", "desc": "Accès interdit à tout véhicule.", "forme": "cercle_rouge", "symbole": "⛔"},
    {"code": "C3", "nom": "Sens interdit", "cat": "Série C : Interdiction", "desc": "Interdiction de s'engager dans cette voie.", "forme": "cercle_rouge", "symbole": "🚫"},
    {"code": "C11", "nom": "Accès interdit aux cyclistes", "cat": "Série C : Interdiction", "desc": "Interdit aux vélos.", "forme": "cercle_rouge", "symbole": "❌ 🚲"},
    {"code": "C13", "nom": "Accès interdit aux piétons", "cat": "Série C : Interdiction", "desc": "Interdit aux piétons.", "forme": "cercle_rouge", "symbole": "❌ 🚶"},
    {"code": "C35", "nom": "Interdiction de dépasser", "cat": "Série C : Interdiction", "desc": "Interdiction de dépasser les véhicules à moteur.", "forme": "cercle_rouge", "symbole": "🚗 ⛔ 🚙"},
    {"code": "C43 (30)", "nom": "Vitesse limitée à 30 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 30 km/h.", "forme": "cercle_rouge", "symbole": "30"},
    {"code": "C43 (50)", "nom": "Vitesse limitée à 50 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée en agglomération.", "forme": "cercle_rouge", "symbole": "50"},
    {"code": "C45", "nom": "Fin de toutes les interdictions", "cat": "Série C : Interdiction", "desc": "Fin des limitations de vitesse ou interdictions de dépassement.", "forme": "cercle_blanc", "symbole": "FIN"},

    # --- SÉRIE D : OBLIGATION ---
    {"code": "D1a", "nom": "Direction obligatoire à droite", "cat": "Série D : Obligation", "desc": "Obligation de tourner à droite.", "forme": "cercle_bleu", "symbole": "➡️"},
    {"code": "D1b", "nom": "Direction obligatoire à gauche", "cat": "Série D : Obligation", "desc": "Obligation de tourner à gauche.", "forme": "cercle_bleu", "symbole": "⬅️"},
    {"code": "D3a", "nom": "Contournement obligatoire par la droite", "cat": "Série D : Obligation", "desc": "Obligation de passer à droite de l'îlot.", "forme": "cercle_bleu", "symbole": "↘️"},
    {"code": "D9", "nom": "Piste cyclable obligatoire", "cat": "Série D : Obligation", "desc": "Voie exclusive réservée aux cyclistes.", "forme": "cercle_bleu", "symbole": "🚲"},
    {"code": "D10", "nom": "Chemin pour piétons", "cat": "Série D : Obligation", "desc": "Voie réservée exclusivement aux piétons.", "forme": "cercle_bleu", "symbole": "🚶"},

    # --- SÉRIE E : STATIONNEMENT ---
    {"code": "E1", "nom": "Stationnement interdit", "cat": "Série E : Stationnement", "desc": "Interdiction de stationner du côté du panneau.", "forme": "cercle_bleu_barre", "symbole": "🅿️ ❌"},
    {"code": "E3", "nom": "Arrêt et stationnement interdits", "cat": "Série E : Stationnement", "desc": "Interdiction absolue de s'arrêter et de stationner.", "forme": "cercle_bleu_croix", "symbole": "🛑 ❌"},
    {"code": "E9a", "nom": "Stationnement autorisé (Parking)", "cat": "Série E : Stationnement", "desc": "Indique un emplacement ou un parking autorisé.", "forme": "carre_bleu", "symbole": "🅿️"},

    # --- SÉRIE F : INDICATION ---
    {"code": "F5", "nom": "Autoroute", "cat": "Série F : Indication", "desc": "Début d'autoroute.", "forme": "rectangle_bleu", "symbole": "🛣️"},
    {"code": "F12a", "nom": "Zone résidentielle / Zone de rencontre", "cat": "Série F : Indication", "desc": "Les piétons y ont la priorité absolue.", "forme": "rectangle_bleu", "symbole": "🏡"},
    {"code": "F19", "nom": "Sens unique", "cat": "Série F : Indication", "desc": "Indique une rue à sens unique.", "forme": "rectangle_bleu", "symbole": "➡️ SENS UNIQUE"},
    {"code": "F4a", "nom": "Zone 30", "cat": "Série F : Indication", "desc": "Entrée d'une zone limitée à 30 km/h.", "forme": "rectangle_blanc_bord_rouge", "symbole": "ZONE 30"},
]

def generer_visuel_css(forme, symbole):
    """Génère un composant graphique CSS simulant fidèlement la forme géométrique du panneau"""
    style_base = "display: flex; align-items: center; justify-content: center; margin: 0 auto; font-weight: 800; box-shadow: 0 4px 12px rgba(0,0,0,0.15);"
    
    if forme == "triangle":
        # Représentation stylisée d'un triangle de danger (fond blanc, bordure rouge)
        return f"<div style='{style_base} width: 130px; height: 110px; background: white; border-bottom: 90px solid #cc0000; border-left: 65px solid transparent; border-right: 65px solid transparent; position: relative;'><span style='position: absolute; top: 15px; font-size: 26px; z-index: 2;'>{symbole}</span></div>"
    
    elif forme == "triangle_inverse":
        return f"<div style='{style_base} width: 130px; height: 110px; background: white; border-top: 90px solid #cc0000; border-left: 65px solid transparent; border-right: 65px solid transparent; position: relative;'><span style='position: absolute; bottom: 15px; font-size: 26px; z-index: 2;'>{symbole}</span></div>"
    
    elif forme == "cercle_rouge":
        return f"<div style='{style_base} width: 110px; height: 110px; background: white; border: 12px solid #cc0000; border-radius: 50%; font-size: 24px; color: #111;'>{symbole}</div>"
    
    elif forme == "cercle_bleu":
        return f"<div style='{style_base} width: 110px; height: 110px; background: #0044cc; border: 4px solid white; border-radius: 50%; font-size: 30px; color: white;'>{symbole}</div>"
    
    elif forme == "losange":
        return f"<div style='{style_base} width: 90px; height: 90px; background: #ffcc00; border: 6px solid white; transform: rotate(45deg); font-size: 24px;'><span style='transform: rotate(-45deg);'>{symbole}</span></div>"
    
    elif forme == "octogone":
        return f"<div style='{style_base} width: 110px; height: 110px; background: #cc0000; color: white; border-radius: 15px; font-size: 20px; border: 4px solid white;'>{symbole}</div>"
    
    else: # Format rectangle / carré par défaut (Indications)
        return f"<div style='{style_base} width: 140px; height: 90px; background: #0044cc; color: white; border-radius: 8px; border: 3px solid white; font-size: 18px; text-align: center; padding: 5px;'>{symbole}</div>"

def carte(*args, **kwargs):
    mode = st.radio(
        "Mode de navigation",
        ["🎯 Lancer le Quiz", "📚 Répertoire Officiel Complet"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.write("")

    # --- MODE 1 : QUIZ INTERACTIF ---
    if mode == "🎯 Lancer le Quiz":
        if "quiz_version" not in st.session_state or st.session_state["quiz_version"] != "v8_css":
            st.session_state["quiz_version"] = "v8_css"
            st.session_state["quiz_index"] = 0
            st.session_state["quiz_score"] = 0
            st.session_state["quiz_panneaux"] = random.sample(PANNEAUX_OFFICIELS_BELGES, min(15, len(PANNEAUX_OFFICIELS_BELGES)))
            st.session_state["quiz_repondu"] = False

        panneaux_liste = st.session_state["quiz_panneaux"]
        idx = st.session_state["quiz_index"]

        st.markdown(f"### 🚦 Quiz Visuel Belge ({idx + 1} / {len(panneaux_liste)})")

        if idx >= len(panneaux_liste):
            score = st.session_state["quiz_score"]
            total = len(panneaux_liste)
            st.success(f"🎉 Série terminée ! Score final : {score} / {total}")
            if st.button("Recommencer une série", key="quiz_restart", type="primary"):
                st.session_state["quiz_index"] = 0
                st.session_state["quiz_score"] = 0
                st.session_state["quiz_panneaux"] = random.sample(PANNEAUX_OFFICIELS_BELGES, min(15, len(PANNEAUX_OFFICIELS_BELGES)))
                st.session_state["quiz_repondu"] = False
                st.rerun()
            return

        actuel = panneaux_liste[idx]

        if "quiz_options" not in st.session_state or st.session_state.get("quiz_current_idx") != idx:
            fausses = [p["nom"] for p in PANNEAUX_OFFICIELS_BELGES if p["nom"] != actuel["nom"]]
            choix_fausses = random.sample(fausses, min(2, len(fausses)))
            options = choix_fausses + [actuel["nom"]]
            random.shuffle(options)
            st.session_state["quiz_options"] = options
            st.session_state["quiz_current_idx"] = idx
            st.session_state["quiz_repondu"] = False

        # Affichage du panneau graphique CSS
        visuel_html = generer_visuel_css(actuel["forme"], actuel["symbole"])
        st.markdown(
            f"""
            <div style='text-align: center; padding: 25px; background: var(--surface); border: 2px solid var(--trait); border-radius: 16px; box-shadow: var(--ombre); margin-bottom: 15px;'>
                <div style='font-size: 12px; font-weight: 700; color: var(--gris); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 15px;'>Panneau Officiel : {actuel['code']}</div>
                {visuel_html}
            </div>
            """,
            unsafe_allow_html=True
        )

        st.markdown(f"<div style='text-align:center; font-weight:600; margin:10px 0; color:var(--encre);'>Indice : {actuel['desc']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;'><span class='tag'>Catégorie : {actuel['cat']}</span></div>", unsafe_allow_html=True)
        
        st.write("")
        st.markdown("**Quelle est la désignation exacte de ce panneau ?**")

        options = st.session_state["quiz_options"]
        repondu = st.session_state["quiz_repondu"]

        for opt in options:
            btn_type = "secondary"
            if repondu and opt == actuel["nom"]:
                btn_type = "primary"

            if st.button(opt, key=f"opt_{idx}_{opt}", disabled=repondu, type=btn_type):
                st.session_state["quiz_repondu"] = True
                if opt == actuel["nom"]:
                    st.session_state["quiz_score"] += 1
                    st.toast("Bonne réponse ! 🎯", icon="✅")
                else:
                    st.toast(f"Raté ! C'était : {actuel['nom']}", icon="❌")
                st.rerun()

        if repondu:
            st.write("")
            if st.button("Question suivante ➔", key=f"next_{idx}", type="primary"):
                st.session_state["quiz_index"] += 1
                st.session_state["quiz_repondu"] = False
                st.rerun()

    # --- MODE 2 : CATALOGUE DE RÉVISION COMPLET ---
    else:
        st.markdown("### 📚 Répertoire Officiel des Panneaux Belges")
        st.caption(f"Base complète ({len(PANNEAUX_OFFICIELS_BELGES)} panneaux répertoriés avec affichage visuel graphique).")

        recherche = st.text_input("🔍 Rechercher un panneau (ex: A1a, B1, Stop, Danger...)", placeholder="Tapez votre recherche...")

        resultats = PANNEAUX_OFFICIELS_BELGES
        if recherche.strip():
            m = recherche.strip().lower()
            resultats = [p for p in PANNEAUX_OFFICIELS_BELGES if m in p["nom"].lower() or m in p["cat"].lower() or m in p["code"].lower() or m in p["desc"].lower()]

        categories = sorted(list(set(p["cat"] for p in resultats)))

        for cat in categories:
            st.markdown(f"#### 📌 {cat}")
            sous_groupe = [p for p in resultats if p["cat"] == cat]
            
            for p in sous_groupe:
                with st.expander(f"[{p['code']}] — {p['nom']}"):
                    col_g, col_d = st.columns([1, 2])
                    with col_g:
                        st.markdown(generer_visuel_css(p["forme"], p["symbole"]), unsafe_allow_html=True)
                    with col_d:
                        st.markdown(f"**Signification :** {p['desc']}")
                        st.markdown(f"<span class='tag'>{p['cat']}</span>", unsafe_allow_html=True)
            st.write("")

        if not resultats:
            st.info("Aucun panneau ne correspond à votre recherche.")
