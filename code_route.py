# ==========================================================
# Code de la Route Belge — Base Officielle & Quiz Interactif
# ==========================================================
import random
import streamlit as st

# Base de données exhaustive de tous les panneaux officiels belges
PANNEAUX_OFFICIELS_BELGES = [
    # --- SÉRIE A : SIGNAUX DE DANGER ---
    {"code": "A1a", "nom": "Virage dangereux à gauche", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé à gauche."},
    {"code": "A1b", "nom": "Virage dangereux à droite", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé à droite."},
    {"code": "A3", "nom": "Descente dangereuse", "cat": "Série A : Danger", "desc": "Indique une pente raide (le pourcentage y est souvent inscrit)."},
    {"code": "A5", "nom": "Montée à forte inclinaison", "cat": "Série A : Danger", "desc": "Indique une forte côte."},
    {"code": "A7a", "nom": "Rétrécissement de la chaussée", "cat": "Série A : Danger", "desc": "Rétrécissement de la route des deux côtés."},
    {"code": "A9", "nom": "Pont mobile", "cat": "Série A : Danger", "desc": "Approche d'un pont levant ou tournant."},
    {"code": "A11", "nom": "Débouché sur un quai ou une berge", "cat": "Série A : Danger", "desc": "La route mène vers de l'eau."},
    {"code": "A13", "nom": "Cassis ou dos d'âne", "cat": "Série A : Danger", "desc": "Ralentisseur ou bosse sur la chaussée."},
    {"code": "A15", "nom": "Chaussée glissante", "cat": "Série A : Danger", "desc": "Risque accru de glissade (pluie, verglas, gravillons)."},
    {"code": "A21", "nom": "Passage pour piétons", "cat": "Série A : Danger", "desc": "Annonce un passage clouté à proximité."},
    {"code": "A23", "nom": "Endroit fréquenté par des enfants", "cat": "Série A : Danger", "desc": "Zone d'école ou aire de jeux à proximité."},
    {"code": "A25", "nom": "Passage de cyclistes", "cat": "Série A : Danger", "desc": "Débouché de cyclistes ou piste cyclable."},
    {"code": "A27", "nom": "Traversée de gibier", "cat": "Série A : Danger", "desc": "Risque de traversée d'animaux sauvages."},
    {"code": "A31", "nom": "Travaux", "cat": "Série A : Danger", "desc": "Présence d'un chantier sur la voie publique."},
    {"code": "A33", "nom": "Feux de circulation", "cat": "Série A : Danger", "desc": "Annonce des feux tricolores en amont."},
    {"code": "A51", "nom": "Danger indéterminé", "cat": "Série A : Danger", "desc": "Danger particulier annoncé par un panneau additionnel."},

    # --- SÉRIE B : SIGNAUX DE PRIORITÉ ---
    {"code": "B1", "nom": "Cédez le passage", "cat": "Série B : Priorité", "desc": "Triangle blanc pointé vers le bas à bord rouge."},
    {"code": "B5", "nom": "Stop (Arrêt obligatoire)", "cat": "Série B : Priorité", "desc": "Obligation de marquer l'arrêt à la limite de la chaussée transversale."},
    {"code": "B9", "nom": "Voie prioritaire", "cat": "Série B : Priorité", "desc": "Losange jaune : vous avez la priorité sur les intersections traversées."},
    {"code": "B11", "nom": "Fin de voie prioritaire", "cat": "Série B : Priorité", "desc": "Losange barré : fin du statut de route prioritaire."},
    {"code": "Général", "nom": "Priorité à droite", "cat": "Série B : Priorité", "desc": "Règle générale applicable à toute intersection (sauf signalisation contraire)."},

    # --- SÉRIE C : SIGNAUX D'INTERDICTION ---
    {"code": "C1", "nom": "Interdiction de circuler dans les deux sens", "cat": "Série C : Interdiction", "desc": "Accès interdit à tout véhicule dans les deux sens."},
    {"code": "C3", "nom": "Sens interdit", "cat": "Série C : Interdiction", "desc": "Interdiction de s'engager dans cette voie."},
    {"code": "C5", "nom": "Accès interdit aux automobiles", "cat": "Série C : Interdiction", "desc": "Interdit aux voitures et véhicules à moteur à 4 roues."},
    {"code": "C7", "nom": "Accès interdit aux motocycles", "cat": "Série C : Interdiction", "desc": "Interdit aux motos."},
    {"code": "C11", "nom": "Accès interdit aux cyclistes", "cat": "Série C : Interdiction", "desc": "Interdit aux vélos."},
    {"code": "C13", "nom": "Accès interdit aux piétons", "cat": "Série C : Interdiction", "desc": "Interdit aux piétons."},
    {"code": "C23", "nom": "Accès interdit aux camions", "cat": "Série C : Interdiction", "desc": "Interdit aux véhicules de transport de marchandises de plus de X tonnes."},
    {"code": "C35", "nom": "Interdiction de dépasser", "cat": "Série C : Interdiction", "desc": "Interdiction de dépasser les véhicules à moteur (sauf 2 roues)."},
    {"code": "C43 (30)", "nom": "Vitesse limitée à 30 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 30 km/h."},
    {"code": "C43 (50)", "nom": "Vitesse limitée à 50 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée (agglomération)."},
    {"code": "C43 (70)", "nom": "Vitesse limitée à 70 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 70 km/h."},
    {"code": "C45", "nom": "Fin de toutes les interdictions locales", "cat": "Série C : Interdiction", "desc": "Fin des limitations de vitesse ou interdictions de dépassement."},

    # --- SÉRIE D : SIGNAUX D'OBLIGATION ---
    {"code": "D1a", "nom": "Direction obligatoire à droite", "cat": "Série D : Obligation", "desc": "Obligation de tourner à droite à l'intersection."},
    {"code": "D1b", "nom": "Direction obligatoire à gauche", "cat": "Série D : Obligation", "desc": "Obligation de tourner à gauche à l'intersection."},
    {"code": "D3a", "nom": "Contournement obligatoire par la droite", "cat": "Série D : Obligation", "desc": "Obligation de passer à droite de l'îlot central."},
    {"code": "D9", "nom": "Piste cyclable obligatoire", "cat": "Série D : Obligation", "desc": "Voie exclusive réservée aux cyclistes et utilisateurs assimilés."},
    {"code": "D10", "nom": "Chemin pour piétons", "cat": "Série D : Obligation", "desc": "Voie réservée exclusivement aux piétons."},

    # --- SÉRIE E : ARRÊT ET STATIONNEMENT ---
    {"code": "E1", "nom": "Stationnement interdit", "cat": "Série E : Stationnement", "desc": "Interdiction de stationner du côté du panneau (l'arrêt de courte durée pour chargement reste toléré selon les cas)."},
    {"code": "E3", "nom": "Arrêt et stationnement interdits", "cat": "Série E : Stationnement", "desc": "Interdiction absolue de s'arrêter et de stationner."},
    {"code": "E9a", "nom": "Stationnement autorisé (Parking)", "cat": "Série E : Stationnement", "desc": "Indique un emplacement ou un parking autorisé."},
    {"code": "E9b", "nom": "Parking réservé aux personnes handicapées", "cat": "Série E : Stationnement", "desc": "Emplacement réservé aux titulaires de la carte PMR."},

    # --- SÉRIE F : SIGNAUX D'INDICATION ---
    {"code": "F5", "nom": "Autoroute", "cat": "Série F : Indication", "desc": "Début d'autoroute (règles et vitesses autoroutières applicables)."},
    {"code": "F9", "nom": "Route pour automobiles", "cat": "Série F : Indication", "desc": "Voie réservée aux véhicules automobiles avec règles similaires."},
    {"code": "F12a", "nom": "Zone résidentielle / Zone de rencontre", "cat": "Série F : Indication", "desc": "Les piétons y ont la priorité absolue et peuvent utiliser toute la largeur de la voirie."},
    {"code": "F19", "nom": "Sens unique", "cat": "Série F : Indication", "desc": "Indique une rue à sens unique."},
    {"code": "Fg", "nom": "Passage pour piétons (Indication)", "cat": "Série F : Indication", "desc": "Indique l'emplacement exact d'un passage clouté."},
    {"code": "F4a", "nom": "Zone 30", "cat": "Série F : Indication", "desc": "Entrée d'une zone où la vitesse est limitée à 30 km/h sur tout le périmètre."},
    {"code": "F4b", "nom": "Fin de zone 30", "cat": "Série F : Indication", "desc": "Sortie de la zone 30."},
]

def carte(*args, **kwargs):
    # Sélecteur principal de l'onglet Code de la Route
    mode = st.radio(
        "Mode de navigation",
        ["🎯 Lancer le Quiz", "📚 Répertoire Officiel Complet"],
        horizontal=True,
        label_visibility="collapsed"
    )

    st.write("")

    # --- MODE 1 : QUIZ INTERACTIF ---
    if mode == "🎯 Lancer le Quiz":
        if "quiz_version" not in st.session_state or st.session_state["quiz_version"] != "v7_belgique_officiel":
            st.session_state["quiz_version"] = "v7_belgique_officiel"
            st.session_state["quiz_index"] = 0
            st.session_state["quiz_score"] = 0
            st.session_state["quiz_panneaux"] = random.sample(PANNEAUX_OFFICIELS_BELGES, min(15, len(PANNEAUX_OFFICIELS_BELGES)))
            st.session_state["quiz_repondu"] = False

        panneaux_liste = st.session_state["quiz_panneaux"]
        idx = st.session_state["quiz_index"]

        st.markdown(f"### 🚦 Quiz Officiel Belge ({idx + 1} / {len(panneaux_liste)})")

        if idx >= len(panneaux_liste):
            score = st.session_state["quiz_score"]
            total = len(panneaux_liste)
            st.success(f"🎉 Série de révision terminée ! Score final : {score} / {total}")
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

        # Affichage du panneau
        st.markdown(
            f"""
            <div style='text-align: center; padding: 30px; background: var(--surface); border: 2px solid var(--accent); border-radius: 16px; box-shadow: var(--ombre); margin-bottom: 15px;'>
                <div style='font-size: 13px; font-weight: 700; color: var(--gris); text-transform: uppercase; letter-spacing: 1px; margin-bottom: 8px;'>Panneau Officiel : {actuel['code']}</div>
                <div style='font-size: 24px; font-weight: 800; color: var(--accent-fonce);'>{actuel['nom']}</div>
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
        st.caption(f"Base officielle complète ({len(PANNEAUX_OFFICIELS_BELGES)} panneaux enregistrés). Idéal pour vos révisions.")

        # Barre de recherche textuelle
        recherche = st.text_input("🔍 Rechercher un panneau par mot-clé, code (ex: A1a, B1, Stop...)", placeholder="Tapez votre recherche...")

        # Filtrage dynamique
        resultats = PANNEAUX_OFFICIELS_BELGES
        if recherche.strip():
            m = recherche.strip().lower()
            resultats = [p for p in PANNEAUX_OFFICIELS_BELGES if m in p["nom"].lower() or m in p["cat"].lower() or m in p["code"].lower() or m in p["desc"].lower()]

        # Regroupement par catégorie officielle
        categories = sorted(list(set(p["cat"] for p in resultats)))

        for cat in categories:
            st.markdown(f"#### 📌 {cat}")
            sous_groupe = [p for p in resultats if p["cat"] == cat]
            
            for p in sous_groupe:
                with st.expander(f"[{p['code']}] — {p['nom']}"):
                    st.markdown(f"**Signification officielle :** {p['desc']}")
                    st.markdown(f"<span class='tag'>{p['cat']}</span>", unsafe_allow_html=True)
            st.write("")

        if not resultats:
            st.info("Aucun panneau ne correspond à votre recherche.")
