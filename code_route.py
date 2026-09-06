# ==========================================================
# Code de la Route Belge — Module officiel de révision & quiz
# ==========================================================
import random
import streamlit as st

PANNEAUX_OFFICIELS = [
    # --- SÉRIE A : DANGERS ---
    {"code": "A1a", "nom": "Virage dangereux à gauche", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé vers la gauche."},
    {"code": "A1b", "nom": "Virage dangereux à droite", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé vers la droite."},
    {"code": "A3", "nom": "Succession de virages", "cat": "Série A : Danger", "desc": "Annonce plusieurs virages successifs, le premier étant à gauche ou à droite."},
    {"code": "A5", "nom": "Descente dangereuse", "cat": "Série A : Danger", "desc": "Indique une pente raide (le pourcentage est indiqué sur le panneau)."},
    {"code": "A7", "nom": "Montée à forte inclinaison", "cat": "Série A : Danger", "desc": "Indique une forte côte."},
    {"code": "A9", "nom": "Chaussée rétrécie", "cat": "Série A : Danger", "desc": "Rétrécissement de la route des deux côtés ou d'un côté précis."},
    {"code": "A15", "nom": "Chaussée glissante", "cat": "Série A : Danger", "desc": "Risque accru de glissade (pluie, verglas, boue)."},
    {"code": "A21", "nom": "Passage pour piétons", "cat": "Série A : Danger", "desc": "Annonce un passage clouté à proximité."},
    {"code": "A23", "nom": "Endroit fréquenté par des enfants", "cat": "Série A : Danger", "desc": "Présence potentielle d'enfants (écoles, aires de jeux)."},
    {"code": "A31", "nom": "Travaux", "cat": "Série A : Danger", "desc": "Présence d'un chantier sur ou le long de la voie publique."},
    {"code": "A33", "nom": "Feux de circulation", "cat": "Série A : Danger", "desc": "Annonce des feux tricolores en amont."},

    # --- SÉRIE B : PRIORITÉS ---
    {"code": "B1", "nom": "Cédez le passage", "cat": "Série B : Priorité", "desc": "Triangle blanc pointé vers le bas à bord rouge. Céder le passage aux usagers de la route prioritaire."},
    {"code": "B5", "nom": "Stop (Arrêt obligatoire)", "cat": "Série B : Priorité", "desc": "Obligation de marquer l'arrêt complet à la limite de la chaussée transversale."},
    {"code": "B9", "nom": "Voie prioritaire", "cat": "Série B : Priorité", "desc": "Losange jaune : vous êtes prioritaire aux intersections de cette route."},
    {"code": "B11", "nom": "Fin de voie prioritaire", "cat": "Série B : Priorité", "desc": "Losange barré : fin du statut de route prioritaire."},
    {"code": "Général", "nom": "Priorité à droite", "cat": "Série B : Priorité", "desc": "Règle générale de l'intersection : céder le passage à tout venant de droite."},

    # --- SÉRIE C : INTERDICTIONS ---
    {"code": "C1", "nom": "Interdiction de circuler dans les deux sens", "cat": "Série C : Interdiction", "desc": "Accès interdit à tout véhicule dans les deux sens."},
    {"code": "C3", "nom": "Sens interdit", "cat": "Série C : Interdiction", "desc": "Interdiction de s'engager dans cette voie."},
    {"code": "C11", "nom": "Accès interdit aux cyclistes", "cat": "Série C : Interdiction", "desc": "Interdit aux vélos."},
    {"code": "C13", "nom": "Accès interdit aux piétons", "cat": "Série C : Interdiction", "desc": "Interdit aux piétons."},
    {"code": "C35", "nom": "Interdiction de dépasser", "cat": "Série C : Interdiction", "desc": "Interdiction de dépasser les véhicules à moteur (autres que les deux-roues rapides)."},
    {"code": "C43-30", "nom": "Vitesse limitée à 30 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 30 km/h."},
    {"code": "C43-50", "nom": "Vitesse limitée à 50 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 50 km/h (agglomération)."},
    {"code": "C43-70", "nom": "Vitesse limitée à 70 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 70 km/h."},
    {"code": "C45", "nom": "Fin de toutes les interdictions locales", "cat": "Série C : Interdiction", "desc": "Fin des limitations de vitesse ou interdictions de dépassement précédentes."},

    # --- SÉRIE D : OBLIGATIONS ---
    {"code": "D1a", "nom": "Direction obligatoire à droite", "cat": "Série D : Obligation", "desc": "Obligation de tourner à droite à l'intersection."},
    {"code": "D1b", "nom": "Direction obligatoire à gauche", "cat": "Série D : Obligation", "desc": "Obligation de tourner à gauche à l'intersection."},
    {"code": "D3a", "nom": "Contournement obligatoire par la droite", "cat": "Série D : Obligation", "desc": "Obligation de passer à droite de l'îlot ou de l'obstacle."},
    {"code": "D9", "nom": "Piste cyclable obligatoire", "cat": "Série D : Obligation", "desc": "Voie exclusive réservée aux cyclistes et conducteurs de trottinettes rapides."},
    {"code": "D10", "nom": "Chemin pour piétons", "cat": "Série D : Obligation", "desc": "Voie réservée exclusivement aux piétons."},

    # --- SÉRIE E : STATIONNEMENT ---
    {"code": "E1", "nom": "Stationnement interdit", "cat": "Série E : Stationnement", "desc": "Interdiction de stationner du côté du panneau."},
    {"code": "E3", "nom": "Arrêt et stationnement interdits", "cat": "Série E : Stationnement", "desc": "Interdiction absolue de s'arrêter et de stationner."},
    {"code": "E9a", "nom": "Stationnement autorisé (Parking)", "cat": "Série E : Stationnement", "desc": "Indique un emplacement ou un parking autorisé."},

    # --- SÉRIE F : INDICATIONS ---
    {"code": "F5", "nom": "Autoroute", "cat": "Série F : Indication", "desc": "Début d'autoroute (règles et vitesses autoroutières applicables)."},
    {"code": "F12a", "nom": "Zone résidentielle / Zone de rencontre", "cat": "Série F : Indication", "desc": "Les piétons y ont la priorité absolue sur toute la largeur de la voirie."},
    {"code": "F19", "nom": "Sens unique", "cat": "Série F : Indication", "desc": "Indique une rue à sens unique."},
    {"code": "F4a", "nom": "Zone 30", "cat": "Série F : Indication", "desc": "Entrée d'une zone où la vitesse est limitée à 30 km/h sur tout le périmètre."},
]

def afficher_fiche_panneau(code_panneau, categorie):
    """Affiche une carte officielle design représentant le panneau par son code réglementaire officiel."""
    st.markdown(
        f"""
        <div style='text-align: center; padding: 35px 20px; background: var(--surface); border: 2px solid var(--accent); border-radius: 18px; box-shadow: var(--ombre); margin: 10px auto; max-width: 320px;'>
            <div style='font-size: 12px; font-weight: 700; color: var(--gris); text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;'>Panneau Officiel Belge</div>
            <div style='font-size: 42px; font-weight: 800; color: var(--accent-fonce); letter-spacing: 1px; margin: 5px 0;'>{code_panneau}</div>
            <div style='font-size: 11.5px; font-weight: 600; color: var(--encre-2); margin-top: 6px;'>{categorie}</div>
        </div>
        """,
        unsafe_allow_html=True
    )

def carte(*args, **kwargs):
    mode = st.radio(
        "Navigation Panneaux",
        ["🎯 Mode Quiz", "📚 Répertoire & Révisions"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.write("")

    # --- MODE 1 : QUIZ ---
    if mode == "🎯 Mode Quiz":
        if "quiz_version" not in st.session_state or st.session_state["quiz_version"] != "v12_pro":
            st.session_state["quiz_version"] = "v12_pro"
            st.session_state["quiz_index"] = 0
            st.session_state["quiz_score"] = 0
            st.session_state["quiz_panneaux"] = random.sample(PANNEAUX_OFFICIELS, min(15, len(PANNEAUX_OFFICIELS)))
            st.session_state["quiz_repondu"] = False

        panneaux_liste = st.session_state["quiz_panneaux"]
        idx = st.session_state["quiz_index"]

        st.markdown(f"### 🚦 Entraînement Code Belge ({idx + 1} / {len(panneaux_liste)})")

        if idx >= len(panneaux_liste):
            score = st.session_state["quiz_score"]
            total = len(panneaux_liste)
            st.success(f"🎉 Série terminée ! Score final : {score} / {total}")
            if st.button("Recommencer une série", key="quiz_restart", type="primary"):
                st.session_state["quiz_index"] = 0
                st.session_state["quiz_score"] = 0
                st.session_state["quiz_panneaux"] = random.sample(PANNEAUX_OFFICIELS, min(15, len(PANNEAUX_OFFICIELS)))
                st.session_state["quiz_repondu"] = False
                st.rerun()
            return

        actuel = panneaux_liste[idx]

        if "quiz_options" not in st.session_state or st.session_state.get("quiz_current_idx") != idx:
            fausses = [p["nom"] for p in PANNEAUX_OFFICIELS if p["nom"] != actuel["nom"]]
            choix_fausses = random.sample(fausses, min(2, len(fausses)))
            options = choix_fausses + [actuel["nom"]]
            random.shuffle(options)
            st.session_state["quiz_options"] = options
            st.session_state["quiz_current_idx"] = idx
            st.session_state["quiz_repondu"] = False

        # Affichage de la fiche officielle du panneau
        afficher_fiche_panneau(actuel["code"], actuel["cat"])

        st.markdown(f"<div style='text-align:center; font-weight:600; margin:15px 0 5px; color:var(--encre); font-size:15px;'>Règle : {actuel['desc']}</div>", unsafe_allow_html=True)
        
        st.write("")
        st.markdown("**Quel est ce panneau ?**")

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

    # --- MODE 2 : RÉPERTOIRE DE RÉVISION ---
    else:
        st.markdown("### 📚 Répertoire Officiel des Panneaux")
        st.caption(f"Catalogue complet ({len(PANNEAUX_OFFICIELS)} fiches réglementaires officielles).")

        recherche = st.text_input("🔍 Rechercher un panneau (code, mot-clé...)", placeholder="Ex: B1, Stop, Vitesse...")

        resultats = PANNEAUX_OFFICIELS
        if recherche.strip():
            m = recherche.strip().lower()
            resultats = [p for p in PANNEAUX_OFFICIELS if m in p["nom"].lower() or m in p["cat"].lower() or m in p["code"].lower() or m in p["desc"].lower()]

        categories = sorted(list(set(p["cat"] for p in resultats)))

        for cat in categories:
            st.markdown(f"#### 📌 {cat}")
            sous_groupe = [p for p in resultats if p["cat"] == cat]
            
            for p in sous_groupe:
                with st.expander(f"[{p['code']}] — {p['nom']}"):
                    st.markdown(f"**Signification réglementaire :** {p['desc']}")
                    st.markdown(f"<span class='tag'>{p['cat']}</span>", unsafe_allow_html=True)
            st.write("")

        if not resultats:
            st.info("Aucun panneau ne correspond à votre recherche.")
