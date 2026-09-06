# ==========================================================
# Code de la Route (Panneaux) — module autonome
# ==========================================================
import random
import streamlit as st

VERSION_ROUTE = "1.0"

# Base de panneaux (tu pourras en rajouter autant que tu veux ici)
PANNEAUX = [
    {"nom": "Interdiction de circuler dans les deux sens", "cat": "Interdiction", "desc": "Panneau rond à bord rouge et fond blanc."},
    {"nom": "Sens unique", "cat": "Indication", "desc": "Panneau rectangulaire bleu avec une flèche blanche."},
    {"nom": "Cédez le passage", "cat": "Priorité", "desc": "Triangle blanc pointé vers le bas à bord rouge."},
    {"nom": "Priorité de passage", "cat": "Priorité", "desc": "Losange jaune à bord blanc."},
    {"nom": "Stationnement interdit", "cat": "Interdiction", "desc": "Cercle à bord rouge, fond bleu barré en diagonale."},
    {"nom": "Vitesse limitée à 30 km/h", "cat": "Interdiction", "desc": "Cercle blanc à bord rouge avec le chiffre 30."},
    {"nom": "Chemin réservé aux piétons", "cat": "Obligation", "desc": "Cercle bleu avec un pictogramme de piéton."},
    {"nom": "Piste cyclable obligatoire", "cat": "Obligation", "desc": "Cercle bleu avec un pictogramme de vélo."},
    {"nom": "Danger : Virage dangereux", "cat": "Danger", "desc": "Triangle à bord rouge avec un virage."},
    {"nom": "Intersection avec priorité à droite", "cat": "Danger", "desc": "Triangle à bord rouge avec une croix noire au centre."},
]

def carte(conteneur, entete_bloc):
    # Initialisation de l'état du quiz dans Streamlit
    if "quiz_index" not in st.session_state:
        st.session_state["quiz_index"] = 0
        st.session_state["quiz_score"] = 0
        st.session_state["quiz_panneaux"] = random.sample(PANNEAUX, len(PANNEAUX))
        st.session_state["quiz_repondu"] = False

    panneaux_liste = st.session_state["quiz_panneaux"]
    idx = st.session_state["quiz_index"]

    with conteneur("carte-code-route"):
        entete_bloc("🚦 Quiz Panneaux", f"{idx + 1} / {len(panneaux_liste)}")

        if idx >= len(panneaux_liste):
            # Fin du quiz
            score = st.session_state["quiz_score"]
            total = len(panneaux_liste)
            st.markdown(f"<div class='today-none'>🎉 Quiz terminé ! Score : {score} / {total}</div>", unsafe_allow_html=True)
            if st.button("Recommencer", key="quiz_restart", type="primary"):
                st.session_state["quiz_index"] = 0
                st.session_state["quiz_score"] = 0
                st.session_state["quiz_panneaux"] = random.sample(PANNEAUX, len(PANNEAUX))
                st.session_state["quiz_repondu"] = False
                st.rerun()
            return

        actuel = panneaux_liste[idx]

        # Générer 3 propositions (1 bonne, 2 fausses)
        if "quiz_options" not in st.session_state or st.session_state.get("quiz_current_idx") != idx:
            fausses = [p["nom"] for p in PANNEAUX if p["nom"] != actuel["nom"]]
            choix_fausses = random.sample(fausses, min(2, len(fausses)))
            options = choix_fausses + [actuel["nom"]]
            random.shuffle(options)
            st.session_state["quiz_options"] = options
            st.session_state["quiz_current_idx"] = idx
            st.session_state["quiz_repondu"] = False

        st.markdown(f"<div class='jour-titre'>Description : {actuel['desc']}</div>", unsafe_allow_html=True)
        st.markdown(f"<span class='tag'>Catégorie : {actuel['cat']}</span>", unsafe_allow_html=True)
        
        st.write("")
        st.markdown("**Quel est ce panneau ?**")

        options = st.session_state["quiz_options"]
        repondu = st.session_state["quiz_repondu"]

        for opt in options:
            btn_type = "secondary"
            if repondu:
                if opt == actuel["nom"]:
                    btn_type = "primary"  # Surligne la bonne réponse en vert/rose selon le thème

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
