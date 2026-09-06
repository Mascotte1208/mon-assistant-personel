# ==========================================================
# Code de la Route (Panneaux) — module autonome avec images
# ==========================================================
import random
import streamlit as st

VERSION_ROUTE = "2.0"

# Liste complète de panneaux officiels (avec images Wikimedia publiques)
PANNEAUX = [
    {
        "nom": "Cédez le passage",
        "cat": "Priorité",
        "desc": "Triangle blanc pointé vers le bas à bord rouge.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/12/Belgian_road_sign_B1.svg/300px-Belgian_road_sign_B1.svg.png"
    },
    {
        "nom": "Priorité de passage",
        "cat": "Priorité",
        "desc": "Losange jaune à bord blanc.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/e/e4/Belgian_road_sign_B9.svg/300px-Belgian_road_sign_B9.svg.png"
    },
    {
        "nom": "Sens unique",
        "cat": "Indication",
        "desc": "Panneau rectangulaire bleu avec une flèche blanche horizontale.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/73/Belgian_road_sign_F19.svg/300px-Belgian_road_sign_F19.svg.png"
    },
    {
        "nom": "Interdiction de circuler dans les deux sens",
        "cat": "Interdiction",
        "desc": "Panneau rond à bord rouge et fond blanc.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/87/Belgian_road_sign_C1.svg/300px-Belgian_road_sign_C1.svg.png"
    },
    {
        "nom": "Stationnement interdit",
        "cat": "Interdiction",
        "desc": "Cercle à bord rouge, fond bleu barré en diagonale.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/9/9f/Belgian_road_sign_C3.svg/300px-Belgian_road_sign_C3.svg.png"
    },
    {
        "nom": "Vitesse limitée à 30 km/h",
        "cat": "Interdiction",
        "desc": "Cercle blanc à bord rouge avec le chiffre 30.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/Belgian_road_sign_C43_%2830%29.svg/300px-Belgian_road_sign_C43_%2830%29.svg.png"
    },
    {
        "nom": "Piste cyclable obligatoire",
        "cat": "Obligation",
        "desc": "Cercle bleu avec un pictogramme de vélo.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/8c/Belgian_road_sign_D9.svg/300px-Belgian_road_sign_D9.svg.png"
    },
    {
        "nom": "Danger : Virage dangereux",
        "cat": "Danger",
        "desc": "Triangle à bord rouge avec un virage.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/7/7b/Belgian_road_sign_A1a.svg/300px-Belgian_road_sign_A1a.svg.png"
    },
    {
        "nom": "Intersection avec priorité à droite",
        "cat": "Danger",
        "desc": "Triangle à bord rouge avec une croix noire au centre.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/1/15/Belgian_road_sign_A15.svg/300px-Belgian_road_sign_A15.svg.png"
    },
    {
        "nom": "Passage pour piétons",
        "cat": "Danger / Indication",
        "desc": "Triangle à bord rouge annonçant un passage clouté.",
        "image": "https://upload.wikimedia.org/wikipedia/commons/thumb/6/6b/Belgian_road_sign_A23.svg/300px-Belgian_road_sign_A23.svg.png"
    },
]

def carte(conteneur, entete_bloc):
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

        if "quiz_options" not in st.session_state or st.session_state.get("quiz_current_idx") != idx:
            fausses = [p["nom"] for p in PANNEAUX if p["nom"] != actuel["nom"]]
            choix_fausses = random.sample(fausses, min(2, len(fausses)))
            options = choix_fausses + [actuel["nom"]]
            random.shuffle(options)
            st.session_state["quiz_options"] = options
            st.session_state["quiz_current_idx"] = idx
            st.session_state["quiz_repondu"] = False

        # Affichage de l'image du panneau
        col_img1, col_img2, col_img3 = st.columns([1, 2, 1])
        with col_img2:
            st.image(actuel["image"], width=160)

        st.markdown(f"<div class='jour-titre' style='text-align:center;'>Description : {actuel['desc']}</div>", unsafe_allow_html=True)
        st.markdown(f"<div style='text-align:center;'><span class='tag'>Catégorie : {actuel['cat']}</span></div>", unsafe_allow_html=True)
        
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
