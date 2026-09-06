# ==========================================================
# Code de la Route (Panneaux) — module autonome robuste
# ==========================================================
import random
import streamlit as st

PANNEAUX = [
    {
        "nom": "Cédez le passage",
        "cat": "Priorité",
        "desc": "Triangle blanc pointé vers le bas à bord rouge.",
        "icone": "🔻"
    },
    {
        "nom": "Priorité de passage",
        "cat": "Priorité",
        "desc": "Losange jaune à bord blanc.",
        "icone": "🔶"
    },
    {
        "nom": "Sens unique",
        "cat": "Indication",
        "desc": "Panneau rectangulaire bleu avec une flèche blanche.",
        "icone": "➡️"
    },
    {
        "nom": "Interdiction de circuler",
        "cat": "Interdiction",
        "desc": "Panneau rond à bord rouge et fond blanc.",
        "icone": "⛔"
    },
    {
        "nom": "Stationnement interdit",
        "cat": "Interdiction",
        "desc": "Cercle à bord rouge, fond bleu barré en diagonale.",
        "icone": "❌"
    },
    {
        "nom": "Vitesse limitée à 30 km/h",
        "cat": "Interdiction",
        "desc": "Cercle blanc à bord rouge avec limitation.",
        "icone": "⏱️"
    },
    {
        "nom": "Piste cyclable obligatoire",
        "cat": "Obligation",
        "desc": "Cercle bleu avec un pictogramme de vélo.",
        "icone": "🚲"
    },
    {
        "nom": "Danger : Virage dangereux",
        "cat": "Danger",
        "desc": "Triangle à bord rouge annonçant un virage.",
        "icone": "⚠️"
    },
    {
        "nom": "Intersection avec priorité à droite",
        "cat": "Danger",
        "desc": "Triangle à bord rouge avec une intersection.",
        "icone": "🔀"
    },
    {
        "nom": "Passage pour piétons",
        "cat": "Danger / Indication",
        "desc": "Triangle à bord rouge annonçant un passage clouté.",
        "icone": "🚶"
    },
]

def carte(*args, **kwargs):
    if "quiz_index" not in st.session_state:
        st.session_state["quiz_index"] = 0
        st.session_state["quiz_score"] = 0
        st.session_state["quiz_panneaux"] = random.sample(PANNEAUX, len(PANNEAUX))
        st.session_state["quiz_repondu"] = False

    panneaux_liste = st.session_state["quiz_panneaux"]
    idx = st.session_state["quiz_index"]

    st.markdown(f"### 🚦 Quiz Panneaux ({idx + 1} / {len(panneaux_liste)})")

    if idx >= len(panneaux_liste):
        score = st.session_state["quiz_score"]
        total = len(panneaux_liste)
        st.success(f"🎉 Quiz terminé ! Score : {score} / {total}")
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

    # Affichage de l'icône/illustration visuelle grand format
    st.markdown(
        f"""
        <div style='text-align: center; font-size: 70px; margin: 15px 0; padding: 20px; background: var(--surface); border: 1.5px solid var(--trait); border-radius: 16px; box-shadow: var(--ombre);'>
            {actuel['icone']}
        </div>
        """,
        unsafe_allow_html=True
    )

    st.markdown(f"<div style='text-align:center; font-weight:600; margin:10px 0; color:var(--encre);'>Description : {actuel['desc']}</div>", unsafe_allow_html=True)
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
