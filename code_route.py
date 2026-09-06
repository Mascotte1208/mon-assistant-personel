# ==========================================================
# Code de la Route Belge — Module Haute Performance (avec images)
# ==========================================================
import os
import random
import urllib.parse
import uuid

import streamlit as st

# Base réglementaire officielle complète (Séries A à F)
BASE_PANNEAUX = [
    # Série A : Dangers
    {"code": "A1a", "nom": "Virage dangereux à gauche", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé vers la gauche."},
    {"code": "A1b", "nom": "Virage dangereux à droite", "cat": "Série A : Danger", "desc": "Annonce un virage prononcé vers la droite."},
    {"code": "A1c", "nom": "Succession de virages", "cat": "Série A : Danger", "desc": "Annonce plusieurs virages successifs, le premier à gauche ou à droite."},
    {"code": "A3", "nom": "Descente dangereuse", "cat": "Série A : Danger", "desc": "Indique une pente raide (le pourcentage est indiqué)."},
    {"code": "A5", "nom": "Montée à forte inclinaison", "cat": "Série A : Danger", "desc": "Indique une forte côte."},
    {"code": "A7a", "nom": "Chaussée rétrécie", "cat": "Série A : Danger", "desc": "Rétrécissement de la route des deux côtés ou d'un côté précis."},
    {"code": "A9", "nom": "Pont mobile", "cat": "Série A : Danger", "desc": "Approche d'un pont levant ou tournant."},
    {"code": "A13", "nom": "Cassis ou dos d'âne", "cat": "Série A : Danger", "desc": "Ralentisseur ou bosse sur la chaussée."},
    {"code": "A15", "nom": "Chaussée glissante", "cat": "Série A : Danger", "desc": "Risque accru de glissade (pluie, verglas, gravillons)."},
    {"code": "A21", "nom": "Passage pour piétons", "cat": "Série A : Danger", "desc": "Annonce un passage clouté à proximité."},
    {"code": "A23", "nom": "Endroit fréquenté par des enfants", "cat": "Série A : Danger", "desc": "Présence potentielle d'enfants (écoles, aires de jeux)."},
    {"code": "A25", "nom": "Passage de cyclistes", "cat": "Série A : Danger", "desc": "Débouché de cyclistes ou piste cyclable."},
    {"code": "A31", "nom": "Travaux", "cat": "Série A : Danger", "desc": "Présence d'un chantier sur ou le long de la voie publique."},
    {"code": "A33", "nom": "Feux de circulation", "cat": "Série A : Danger", "desc": "Annonce des feux tricolores en amont."},
    {"code": "A51", "nom": "Danger indéterminé", "cat": "Série A : Danger", "desc": "Danger particulier annoncé par un panneau additionnel."},

    # Série B : Priorités
    {"code": "B1", "nom": "Cédez le passage", "cat": "Série B : Priorité", "desc": "Triangle blanc pointé vers le bas à bord rouge. Céder le passage aux usagers de la route prioritaire."},
    {"code": "B5", "nom": "Stop (Arrêt obligatoire)", "cat": "Série B : Priorité", "desc": "Obligation de marquer l'arrêt complet à la limite de la chaussée transversale."},
    {"code": "B9", "nom": "Voie prioritaire", "cat": "Série B : Priorité", "desc": "Losange jaune : vous êtes prioritaire aux intersections de cette route."},
    {"code": "B11", "nom": "Fin de voie prioritaire", "cat": "Série B : Priorité", "desc": "Losange barré : fin du statut de route prioritaire."},
    {"code": "B15", "nom": "Priorité à l'approche d'une intersection", "cat": "Série B : Priorité", "desc": "Indique que vous avez la priorité à la prochaine intersection."},
    {"code": "B17", "nom": "Priorité à droite", "cat": "Série B : Priorité", "desc": "Règle générale de l'intersection : céder le passage à tout venant de droite."},

    # Série C : Interdictions
    {"code": "C1", "nom": "Interdiction de circuler dans les deux sens", "cat": "Série C : Interdiction", "desc": "Accès interdit à tout véhicule dans les deux sens."},
    {"code": "C3", "nom": "Sens interdit", "cat": "Série C : Interdiction", "desc": "Interdiction de s'engager dans cette voie."},
    {"code": "C5", "nom": "Accès interdit aux automobiles", "cat": "Série C : Interdiction", "desc": "Interdit aux voitures et camions."},
    {"code": "C7", "nom": "Accès interdit aux motocycles", "cat": "Série C : Interdiction", "desc": "Interdit aux motos."},
    {"code": "C11", "nom": "Accès interdit aux cyclistes", "cat": "Série C : Interdiction", "desc": "Interdit aux vélos."},
    {"code": "C19", "nom": "Accès interdit aux piétons", "cat": "Série C : Interdiction", "desc": "Interdit aux piétons."},
    {"code": "C23", "nom": "Accès interdit aux camions", "cat": "Série C : Interdiction", "desc": "Interdit aux véhicules de transport de marchandises."},
    {"code": "C35", "nom": "Interdiction de dépasser", "cat": "Série C : Interdiction", "desc": "Interdiction de dépasser les véhicules à moteur."},
    {"code": "C43 30", "nom": "Vitesse limitée à 30 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 30 km/h."},
    {"code": "C43 50", "nom": "Vitesse limitée à 50 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 50 km/h (agglomération)."},
    {"code": "C43 70", "nom": "Vitesse limitée à 70 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 70 km/h."},
    {"code": "C43 90", "nom": "Vitesse limitée à 90 km/h", "cat": "Série C : Interdiction", "desc": "Vitesse maximale autorisée de 90 km/h."},
    {"code": "C45", "nom": "Fin de toutes les interdictions locales", "cat": "Série C : Interdiction", "desc": "Fin des limitations de vitesse ou interdictions de dépassement précédentes."},

    # Série D : Obligations
    {"code": "D1a", "nom": "Direction obligatoire à droite", "cat": "Série D : Obligation", "desc": "Obligation de tourner à droite à l'intersection."},
    {"code": "D1b", "nom": "Direction obligatoire à gauche", "cat": "Série D : Obligation", "desc": "Obligation de tourner à gauche à l'intersection."},
    {"code": "D9a", "nom": "Piste cyclable obligatoire", "cat": "Série D : Obligation", "desc": "Voie exclusive réservée aux cyclistes."},
    {"code": "D10", "nom": "Chemin pour piétons", "cat": "Série D : Obligation", "desc": "Voie réservée exclusivement aux piétons."},

    # Série E : Stationnement
    {"code": "E1", "nom": "Stationnement interdit", "cat": "Série E : Stationnement", "desc": "Interdiction de stationner du côté du panneau."},
    {"code": "E3", "nom": "Arrêt et stationnement interdits", "cat": "Série E : Stationnement", "desc": "Interdiction absolue de s'arrêter et de stationner."},
    {"code": "E9a", "nom": "Stationnement autorisé (Parking)", "cat": "Série E : Stationnement", "desc": "Indique un emplacement ou un parking autorisé."},

    # Série F : Indications
    {"code": "F5", "nom": "Autoroute", "cat": "Série F : Indication", "desc": "Début d'autoroute (règles et vitesses autoroutières applicables)."},
    {"code": "F9", "nom": "Route pour automobiles", "cat": "Série F : Indication", "desc": "Voie réservée aux véhicules automobiles."},
    {"code": "F12a", "nom": "Zone résidentielle / Zone de rencontre", "cat": "Série F : Indication", "desc": "Les piétons y ont la priorité absolue sur toute la largeur de la voirie."},
    {"code": "F19", "nom": "Sens unique", "cat": "Série F : Indication", "desc": "Indique une rue à sens unique."},
    {"code": "F4a", "nom": "Zone 30", "cat": "Série F : Indication", "desc": "Entrée d'une zone où la vitesse est limitée à 30 km/h sur tout le périmètre."},
    {"code": "F4b", "nom": "Fin de zone 30", "cat": "Série F : Indication", "desc": "Sortie de la zone 30."},
]

WIKIMEDIA_FILEPATH = "https://commons.wikimedia.org/wiki/Special:FilePath/"

# Dossier local (dans ton projet Streamlit) où tu peux déposer tes propres
# images pour les panneaux dont le nom de fichier Wikimedia est incertain
# ou introuvable (ex. la série D). Nomme le fichier avec le "code" exact,
# ex: assets/panneaux/D1a.svg, assets/panneaux/D9a.png, etc.
LOCAL_ASSETS_DIR = "assets/panneaux"

# Wikimedia Commons n'utilise pas un nom de fichier cohérent pour tous les
# panneaux (parfois "road sign", parfois "traffic sign", parfois un suffixe
# comme "rechts"/"(2)"). Cette table corrige les cas connus où le schéma
# par défaut ("Belgian road sign {code}.svg") ne correspond à aucun fichier.
IMAGE_FILENAME_OVERRIDES = {
    "D1a": "Belgian traffic sign D1c.svg",       # direction obligatoire à droite
    "D1b": "Belgian traffic sign D1e.svg",       # direction obligatoire à gauche
    # D9a : aucune image officielle correspondante trouvée sur Commons à ce jour.
}


def local_image_path(code: str):
    """Renvoie le chemin d'une image locale pour ce code si elle existe, sinon None."""
    for ext in (".svg", ".png", ".jpg", ".jpeg"):
        path = os.path.join(LOCAL_ASSETS_DIR, f"{code}{ext}")
        if os.path.isfile(path):
            return path
    return None


def image_url_for(code: str) -> str:
    """Construit l'URL de l'image officielle (Wikimedia Commons) pour un code de panneau."""
    filename = IMAGE_FILENAME_OVERRIDES.get(code, f"Belgian road sign {code}.svg")
    return WIKIMEDIA_FILEPATH + urllib.parse.quote(filename)


def carte_texte_html(actuel, message="Référence officielle"):
    """Carte de repli (texte + code) utilisée quand aucune image n'est trouvée."""
    return f"""
        <div style="text-align: center; padding: 40px 20px;
                    background: var(--surface, #ffffff);
                    border: 2px solid var(--accent, #1f6feb);
                    border-radius: 18px;
                    box-shadow: var(--ombre, 0 2px 10px rgba(0,0,0,0.08));
                    margin: 10px auto;">
            <div style="font-size: 12.5px; font-weight: 700; color: var(--gris, #6b7280);
                        text-transform: uppercase; letter-spacing: 1.5px; margin-bottom: 8px;">
                {message}
            </div>
            <div style="font-size: 46px; font-weight: 800; color: var(--accent-fonce, #0b3d91);
                        letter-spacing: 1px; margin: 5px 0;">
                {actuel['code']}
            </div>
            <div style="font-size: 13px; font-weight: 600; color: var(--encre-2, #374151); margin-top: 8px;">
                {actuel['cat']}
            </div>
        </div>
        """


def afficher_panneau(actuel, taille_px=180):
    """Affiche l'image du panneau. Ordre de priorité :
    1) image locale dans assets/panneaux/{code}.(svg|png|jpg) si elle existe (100% fiable)
    2) image Wikimedia Commons, chargée par le NAVIGATEUR (pas le serveur)
    3) si ça échoue aussi (onerror JS), carte texte de repli
    """
    local_path = local_image_path(actuel["code"])
    if local_path:
        col1, col2, col3 = st.columns([1, 1, 1])
        with col2:
            st.image(local_path, width=taille_px)
        st.markdown(
            f"<div style='text-align:center; font-size:12px; color:var(--gris, #6b7280); "
            f"letter-spacing:1px; text-transform:uppercase; margin-top:4px;'>{actuel['code']} — {actuel['cat']}</div>",
            unsafe_allow_html=True,
        )
        return

    url = image_url_for(actuel["code"])
    uid = uuid.uuid4().hex[:8]
    fallback_html = carte_texte_html(actuel, message="Référence officielle (image indisponible)").replace("'", "\\'").replace("\n", "")

    st.markdown(
        f"""
        <div id="panneau-wrap-{uid}" style="text-align:center; margin: 10px auto;">
            <img
                src="{url}"
                style="width:{taille_px}px; max-width:90%; display:block; margin:0 auto;"
                onerror="document.getElementById('panneau-wrap-{uid}').innerHTML = '{fallback_html}';"
            />
            <div style="font-size:12px; color:var(--gris, #6b7280); letter-spacing:1px;
                        text-transform:uppercase; margin-top:6px;">
                {actuel['code']} — {actuel['cat']}
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def carte(*args, **kwargs):
    mode = st.radio(
        "Navigation Panneaux",
        ["🎯 Mode Quiz Interactif", "📚 Répertoire Officiel Complet"],
        horizontal=True,
        label_visibility="collapsed",
        key="carte_mode_radio",
    )

    st.write("")

    # --- MODE 1 : QUIZ HAUTE PERFORMANCE ---
    if mode == "🎯 Mode Quiz Interactif":
        if "quiz_version" not in st.session_state or st.session_state["quiz_version"] != "v15_images":
            st.session_state["quiz_version"] = "v15_images"
            st.session_state["quiz_index"] = 0
            st.session_state["quiz_score"] = 0
            st.session_state["quiz_panneaux"] = random.sample(BASE_PANNEAUX, min(20, len(BASE_PANNEAUX)))
            st.session_state["quiz_repondu"] = False
            st.session_state.pop("quiz_options", None)
            st.session_state.pop("quiz_current_idx", None)

        panneaux_liste = st.session_state["quiz_panneaux"]
        idx = st.session_state["quiz_index"]

        st.markdown(f"### 🚦 Quiz Code de la Route Belge ({idx + 1} / {len(panneaux_liste)})")

        if idx >= len(panneaux_liste):
            score = st.session_state["quiz_score"]
            total = len(panneaux_liste)
            st.success(f"🎉 Session terminée ! Score final : {score} / {total}")
            if st.button("Lancer une nouvelle série", key="quiz_restart", type="primary"):
                st.session_state["quiz_index"] = 0
                st.session_state["quiz_score"] = 0
                st.session_state["quiz_panneaux"] = random.sample(BASE_PANNEAUX, min(20, len(BASE_PANNEAUX)))
                st.session_state["quiz_repondu"] = False
                st.session_state.pop("quiz_options", None)
                st.session_state.pop("quiz_current_idx", None)
                st.rerun()
            return

        actuel = panneaux_liste[idx]

        if "quiz_options" not in st.session_state or st.session_state.get("quiz_current_idx") != idx:
            faux_panneaux = [p for p in BASE_PANNEAUX if p["code"] != actuel["code"]]
            choix_faux = random.sample(faux_panneaux, min(3, len(faux_panneaux)))
            options = [p["nom"] for p in choix_faux] + [actuel["nom"]]
            random.shuffle(options)
            st.session_state["quiz_options"] = options
            st.session_state["quiz_current_idx"] = idx
            st.session_state["quiz_repondu"] = False

        # --- Affichage du panneau : image officielle si dispo, sinon carte de repli ---
        afficher_panneau(actuel)

        st.write("")
        st.markdown("**Quelle est la désignation exacte de ce panneau ?**")

        options = st.session_state["quiz_options"]
        repondu = st.session_state["quiz_repondu"]

        for i, opt in enumerate(options):
            btn_type = "secondary"
            if repondu and opt == actuel["nom"]:
                btn_type = "primary"

            if st.button(opt, key=f"opt_{idx}_{i}", disabled=repondu, type=btn_type):
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

    # --- MODE 2 : RÉPERTOIRE & RÉVISIONS ---
    else:
        st.markdown("### 📚 Répertoire Officiel Complet")
        st.caption(f"Base de données de référence ({len(BASE_PANNEAUX)} panneaux officiels belges répertoriés).")

        recherche = st.text_input(
            "🔍 Filtrer les panneaux (code, nom, catégorie, mot-clé...)",
            placeholder="Ex: A1a, Stop, Vitesse, Priorité...",
            key="repertoire_recherche",
        )

        resultats = BASE_PANNEAUX
        if recherche.strip():
            m = recherche.strip().lower()
            resultats = [
                p for p in BASE_PANNEAUX
                if m in p["nom"].lower() or m in p["cat"].lower() or m in p["code"].lower() or m in p["desc"].lower()
            ]

        categories = sorted(set(p["cat"] for p in resultats))

        for cat in categories:
            st.markdown(f"#### 📌 {cat}")
            sous_groupe = [p for p in resultats if p["cat"] == cat]

            for p in sous_groupe:
                with st.expander(f"[{p['code']}] — {p['nom']}"):
                    col_img, col_txt = st.columns([1, 3])
                    with col_img:
                        local_path = local_image_path(p["code"])
                        if local_path:
                            st.image(local_path, width=90)
                        else:
                            url = image_url_for(p["code"])
                            uid = uuid.uuid4().hex[:8]
                            st.markdown(
                                f"""
                                <img id="thumb-{uid}" src="{url}" style="width:90px;"
                                     onerror="this.replaceWith(Object.assign(document.createElement('div'),
                                        {{innerText:'Image indisponible', style:'font-size:11px;color:var(--gris,#6b7280);'}}));" />
                                """,
                                unsafe_allow_html=True,
                            )
                    with col_txt:
                        st.markdown(f"**Signification réglementaire :** {p['desc']}")
                        st.markdown(f"<span class='tag'>{p['cat']}</span>", unsafe_allow_html=True)
            st.write("")

        if not resultats:
            st.info("Aucun panneau ne correspond à votre recherche.")
