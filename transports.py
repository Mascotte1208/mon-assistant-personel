# ==========================================================
# Transports - module autonome pour "Notre Assistant"
# ==========================================================
# Temps d'attente en direct des bus, trams et metros de la STIB.
# Les arrets se cherchent et s'ajoutent depuis l'application, et
# sont partages entre vous deux via Google Sheets.
#
# Source : portail Belgian Mobility Company (Azure API Management).
# Compte gratuit, puis une cle a placer dans les secrets Streamlit :
#
#     [stib]
#     partner_key = "votre cle"
#
# Branchement dans l'application principale, page d'accueil :
#
#     import transports
#     transports.carte({
#         "conteneur": conteneur, "entete_bloc": entete_bloc,
#         "rows": rows, "add_row": add_row, "delete_row": delete_row,
#         "pad": pad,
#     })
#
# Les arrets sont ranges dans la feuille "Listes" qui existe deja,
# sous la categorie "Arret STIB". Aucune migration necessaire.
#
# Note : les noms de champs du jeu de donnees ne sont pas documentes.
# Le module les detecte tout seul au premier appel, et le volet
# "Diagnostic" affiche ce qu'il a trouve.
# ==========================================================

import json
from datetime import datetime, timezone

import requests
import streamlit as st

VERSION_TRANSPORTS = "3.0"

BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb"
URL_ATTENTE = f"{BASE}/rt/WaitingTimes/"
# Le portail peut nommer ce jeu autrement : on essaie plusieurs pistes.
URLS_ARRETS = [f"{BASE}/rt/StopDetails/", f"{BASE}/StopDetails/", f"{BASE}/rt/StopsByLine/"]
ENTETE_CLE = "bmc-partner-key"

CATEGORIE = "Arrêt STIB"        # colonne 1 de la feuille Listes
RAFRAICHISSEMENT = 20           # secondes, en mode direct

# Noms de champs possibles, du plus probable au moins probable.
CANDIDATS = {
    "arret":       ["pointid", "point_id", "stop_id", "stopid", "id", "stop"],
    "ligne":       ["lineid", "line_id", "line", "route_id", "routeid", "route"],
    "destination": ["destination", "destination_fr", "direction", "headsign", "terminus"],
    "heure":       ["expectedarrivaltime", "expected_arrival_time", "arrivaltime",
                    "arrival_time", "expectedtime", "time", "passingtime"],
    "nom":         ["name", "stop_name", "stopname", "descr_fr", "nom", "label"],
}

CSS = """
<style>
.tr-arret{font-size:13px; font-weight:800; color:#be185d; background:#fdf2f8;
  display:inline-block; padding:4px 10px; border-radius:10px; margin:10px 0 6px;
  border:1.5px solid #f472b6;}
.tr-ligne{display:flex; align-items:center; gap:10px; padding:7px 2px;
  border-bottom:1px solid #fce7f3;}
.tr-ligne:last-child{border-bottom:none;}
.tr-num{flex:0 0 auto; min-width:34px; text-align:center; background:#9d174d; color:#fff;
  font-size:13px; font-weight:800; padding:4px 8px; border-radius:9px;}
.tr-dest{flex:1 1 auto; min-width:0; font-size:13.5px; font-weight:700; color:#311026;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.tr-min{flex:0 0 auto; font-size:14px; font-weight:800; color:#be185d;
  font-variant-numeric:tabular-nums; white-space:nowrap;}
.tr-min .prochain{color:#15803d;}
.tr-vide{font-size:13px; font-weight:700; color:#6b7280; padding:6px 2px; line-height:1.5;}
.tr-maj{font-size:11.5px; font-weight:700; color:#6b7280; padding-top:8px;}
.tr-live{display:inline-block; width:8px; height:8px; border-radius:50%;
  background:#15803d; margin-right:6px; vertical-align:middle;}
</style>
"""

_CTX = {}


def _f(nom):
    fonction = _CTX.get(nom)
    if fonction is None:
        raise RuntimeError(f"Contexte incomplet : « {nom} » manque.")
    return fonction


# ----------------------------------------------------------
# Appels à l'API
# ----------------------------------------------------------
def cle():
    """Clé partenaire, lue dans les secrets Streamlit."""
    try:
        bloc = st.secrets["stib"]
    except Exception:
        return None
    return bloc.get("partner_key") or bloc.get("key") or bloc.get("client_id")


@st.cache_data(ttl=RAFRAICHISSEMENT, show_spinner=False)
def interroger(url, parametres, cle_partenaire):
    """Un appel générique au portail. Renvoie (json, erreur)."""
    try:
        reponse = requests.get(
            url,
            params={k: v for k, v in (parametres or {}).items() if v is not None},
            headers={ENTETE_CLE: cle_partenaire, "Accept": "application/json"},
            timeout=10,
        )
        if reponse.status_code in (401, 403):
            return None, "Clé refusée par le portail (401/403)."
        if reponse.status_code == 404:
            return None, "Jeu de données introuvable (404)."
        reponse.raise_for_status()
        return reponse.json(), None
    except Exception as err:
        return None, str(err)[:130]


@st.cache_data(ttl=3600, show_spinner=False)
def champs_disponibles(url, cle_partenaire):
    """Liste des colonnes du jeu de données, et un enregistrement témoin."""
    donnees, err = interroger(url, {"limit": 1}, cle_partenaire)
    if err or not donnees:
        return [], None, err or "Réponse vide."
    resultats = donnees.get("results") or []
    champs = (donnees.get("metadata") or {}).get("fields") or []
    if not champs and resultats:
        champs = list(resultats[0].keys())
    return champs, (resultats[0] if resultats else None), None


def choisir(champs, role):
    """Retrouve le nom réel d'un champ à partir de son rôle."""
    bas = {c.lower(): c for c in (champs or [])}
    for candidat in CANDIDATS.get(role, []):
        if candidat in bas:
            return bas[candidat]
    # Repli : un champ dont le nom contient le mot-clé.
    for candidat in CANDIDATS.get(role, []):
        for minuscule, original in bas.items():
            if candidat in minuscule:
                return original
    return None


# ----------------------------------------------------------
# Arrêts enregistrés (feuille Listes)
# ----------------------------------------------------------
def arrets():
    """[{idx, nom, ids}] lus dans la feuille Listes."""
    sortie = []
    try:
        lignes = _f("rows")("Listes")
    except Exception:
        return sortie
    for index, ligne in lignes:
        categorie, element, notes = _f("pad")(ligne, 3)
        if categorie != CATEGORIE:
            continue
        ids = [i.strip() for i in str(notes or "").split(",") if i.strip()]
        if element and ids:
            sortie.append({"idx": index, "nom": element, "ids": ids})
    return sortie


def ajouter_arret(nom, ids):
    _f("add_row")("Listes", [CATEGORIE, nom.strip(), ",".join(str(i).strip() for i in ids)])


def retirer_arret(index):
    _f("delete_row")("Listes", index, True, "Arrêt retiré")


# ----------------------------------------------------------
# Lecture des valeurs
# ----------------------------------------------------------
def texte_lisible(valeur):
    """Le portail renvoie tantôt une chaîne, tantôt un couple fr/nl."""
    if isinstance(valeur, str) and valeur.strip().startswith("{"):
        try:
            valeur = json.loads(valeur)
        except ValueError:
            return valeur
    if isinstance(valeur, list) and valeur:
        return texte_lisible(valeur[0])
    if isinstance(valeur, dict):
        return valeur.get("fr") or valeur.get("nl") or valeur.get("en") or ""
    return str(valeur or "")


def minutes_avant(horodatage):
    """Minutes restantes, ou None si la valeur est illisible."""
    if horodatage in (None, ""):
        return None
    brut = texte_lisible(horodatage)
    try:
        arrivee = datetime.fromisoformat(brut.replace("Z", "+00:00"))
    except ValueError:
        try:                              # certains flux donnent un horodatage Unix
            arrivee = datetime.fromtimestamp(float(brut), tz=timezone.utc)
        except (ValueError, OSError):
            return None
    if arrivee.tzinfo is None:
        arrivee = arrivee.replace(tzinfo=timezone.utc)
    return max(0, int(round((arrivee - datetime.now(timezone.utc)).total_seconds() / 60)))


def regrouper(resultats, champs):
    """[(ligne, destination, [minutes])] trié du plus imminent au plus lointain."""
    c_ligne = choisir(champs, "ligne")
    c_dest = choisir(champs, "destination")
    c_heure = choisir(champs, "heure")
    groupes = {}
    for enregistrement in resultats or []:
        minutes = minutes_avant(enregistrement.get(c_heure)) if c_heure else None
        if minutes is None:
            continue
        ligne = texte_lisible(enregistrement.get(c_ligne)) if c_ligne else "?"
        destination = texte_lisible(enregistrement.get(c_dest)) if c_dest else ""
        groupes.setdefault((ligne or "?", destination or "—"), []).append(minutes)
    listes = [(ligne, dest, sorted(m)) for (ligne, dest), m in groupes.items()]
    listes.sort(key=lambda e: (e[2][0] if e[2] else 999, e[0]))
    return listes


def libelle(minutes):
    if not minutes:
        return "—"
    morceaux = []
    for i, m in enumerate(minutes[:3]):
        texte = "à quai" if m == 0 else f"{m} min"
        morceaux.append(f"<span class='prochain'>{texte}</span>" if i == 0 else texte)
    return " · ".join(morceaux)


# ----------------------------------------------------------
# Affichage
# ----------------------------------------------------------
def _tableau(mes_arrets, cle_partenaire, champs, c_arret):
    """Le bloc qui se rafraîchit tout seul en mode direct."""
    if not c_arret:
        st.markdown("<div class='tr-vide'>Le champ identifiant l'arrêt n'a pas été reconnu. "
                    "Ouvrez le volet Diagnostic ci-dessous.</div>", unsafe_allow_html=True)
        return

    for arret in mes_arrets:
        st.markdown(f"<div class='tr-arret'>{arret['nom']}</div>", unsafe_allow_html=True)
        resultats, souci = [], None
        for identifiant in arret["ids"]:
            donnees, err = interroger(
                URL_ATTENTE,
                {"where": f'{c_arret}="{identifiant}"', "limit": 40},
                cle_partenaire,
            )
            if err:
                souci = err
                continue
            resultats.extend(donnees.get("results") or [])
        if souci and not resultats:
            st.markdown(f"<div class='tr-vide'>Indisponible : {souci}</div>",
                        unsafe_allow_html=True)
            continue
        lignes = regrouper(resultats, champs)
        if not lignes:
            st.markdown("<div class='tr-vide'>Aucun passage annoncé.</div>",
                        unsafe_allow_html=True)
            continue
        st.markdown("".join(
            f"<div class='tr-ligne'><span class='tr-num'>{ligne}</span>"
            f"<span class='tr-dest'>{destination}</span>"
            f"<span class='tr-min'>{libelle(minutes)}</span></div>"
            for ligne, destination, minutes in lignes[:6]
        ), unsafe_allow_html=True)

    st.markdown(f"<div class='tr-maj'><span class='tr-live'></span>"
                f"Mis à jour à {datetime.now().strftime('%H:%M:%S')} · données STIB</div>",
                unsafe_allow_html=True)


# Version rafraîchie automatiquement, si la version de Streamlit le permet.
# Définie une seule fois au chargement : un fragment recréé à chaque passage
# perdrait son identité et ne se rafraîchirait jamais.
try:
    _tableau_direct = st.fragment(run_every=RAFRAICHISSEMENT)(_tableau)
except Exception:
    _tableau_direct = _tableau


def _chercher_arret(texte, cle_partenaire):
    """Cherche un arrêt par son nom dans le jeu Stop Details."""
    texte = (texte or "").strip()
    if len(texte) < 2:
        return [], None
    dernier = "Aucun résultat."
    for url in URLS_ARRETS:
        champs, _, err = champs_disponibles(url, cle_partenaire)
        if err or not champs:
            dernier = err or "Jeu de données vide."
            continue
        c_nom, c_id = choisir(champs, "nom"), choisir(champs, "arret")
        if not (c_nom and c_id):
            dernier = "Champs nom/identifiant non reconnus."
            continue
        donnees, err = interroger(
            url, {"where": f'{c_nom} LIKE "%{texte}%"', "limit": 20}, cle_partenaire)
        if err:
            dernier = err
            continue
        trouves, vus = [], set()
        for enregistrement in donnees.get("results") or []:
            identifiant = str(enregistrement.get(c_id) or "")
            nom = texte_lisible(enregistrement.get(c_nom))
            if not identifiant or not nom or identifiant in vus:
                continue
            vus.add(identifiant)
            trouves.append((identifiant, nom))
        if trouves:
            return trouves, None
    return [], dernier


def _gestion(mes_arrets, cle_partenaire):
    """Recherche et suppression d'arrêts, directement dans l'application."""
    with st.expander("Mes arrêts"):
        for arret in mes_arrets:
            colonne_a, colonne_b = st.columns([4, 1])
            with colonne_a:
                st.markdown(f"**{arret['nom']}** · {', '.join(arret['ids'])}")
            with colonne_b:
                if st.button("🗑️", key=f"tr_del_{arret['idx']}"):
                    retirer_arret(arret["idx"])
                    st.rerun()

        st.markdown("**Ajouter un arrêt**")
        recherche = st.text_input("Nom de l'arrêt", key="tr_q",
                                  placeholder="Ex : Flagey, Gare Centrale…")
        if recherche.strip():
            trouves, err = _chercher_arret(recherche, cle_partenaire)
            if err and not trouves:
                st.caption(f"Recherche indisponible : {err}")
            deja = {i for a in mes_arrets for i in a["ids"]}
            for identifiant, nom in trouves[:12]:
                marque = "✅ " if identifiant in deja else "＋ "
                if st.button(f"{marque}{nom} · {identifiant}", key=f"tr_add_{identifiant}"):
                    ajouter_arret(nom, [identifiant])
                    st.rerun()

        st.caption("Un même arrêt porte un numéro différent dans chaque sens : "
                   "ajoutez les deux pour voir les deux directions.")
        colonne_a, colonne_b = st.columns([2, 1])
        with colonne_a:
            nom_libre = st.text_input("Nom", key="tr_nom", placeholder="Nom de votre choix")
        with colonne_b:
            ids_libres = st.text_input("Numéros", key="tr_ids", placeholder="8301,8302")
        if st.button("Ajouter à la main", key="tr_add_manuel"):
            if nom_libre.strip() and ids_libres.strip():
                ajouter_arret(nom_libre, ids_libres.split(","))
                st.rerun()
            else:
                st.warning("Indiquez un nom et au moins un numéro.")


def _diagnostic(champs, temoin, err, c_arret):
    """Montre ce que le module a compris du jeu de données."""
    with st.expander("Diagnostic"):
        if err:
            st.error(err)
        st.caption(f"Module version {VERSION_TRANSPORTS} · en-tête {ENTETE_CLE}")
        st.write("**Champs annoncés par le portail**")
        st.code(", ".join(champs) if champs else "aucun")
        st.write("**Champs reconnus par le module**")
        st.code("\n".join(f"{role:<12} → {choisir(champs, role) or '(non trouvé)'}"
                          for role in ("arret", "ligne", "destination", "heure")))
        if temoin:
            st.write("**Premier enregistrement reçu**")
            st.json(temoin)
        if not c_arret:
            st.caption("Envoyez-moi le contenu de ces trois blocs et j'ajuste le module.")


def carte(ctx):
    """Dessine la carte transports. Ne lève jamais."""
    global _CTX
    _CTX = ctx
    st.markdown(CSS, unsafe_allow_html=True)

    conteneur = ctx["conteneur"]
    entete_bloc = ctx["entete_bloc"]
    cle_partenaire = cle()
    mes_arrets = arrets()

    with conteneur("carte-transports"):
        entete_bloc("🚋 Prochains passages", len(mes_arrets) or None)

        if not cle_partenaire:
            st.markdown(
                "<div class='tr-vide'>Clé absente. Créez un compte gratuit sur le portail "
                "Belgian Mobility Company, abonnez-vous au jeu WaitingTimes, puis ajoutez "
                "la clé dans les secrets de l'application sous <b>[stib] partner_key</b>.</div>",
                unsafe_allow_html=True)
            return

        champs, temoin, err = champs_disponibles(URL_ATTENTE, cle_partenaire)
        c_arret = choisir(champs, "arret")

        if not mes_arrets:
            st.markdown("<div class='tr-vide'>Aucun arrêt enregistré. Ouvrez « Mes arrêts » "
                        "ci-dessous pour en chercher un.</div>", unsafe_allow_html=True)
            _gestion(mes_arrets, cle_partenaire)
            _diagnostic(champs, temoin, err, c_arret)
            return

        colonne_a, colonne_b = st.columns([2, 1])
        with colonne_a:
            direct = st.toggle("En direct", value=True, key="tr_direct")
        with colonne_b:
            if st.button("🔄", key="tr_refresh"):
                interroger.clear()
                st.rerun()

        if direct:
            _tableau_direct(mes_arrets, cle_partenaire, champs, c_arret)
        else:
            _tableau(mes_arrets, cle_partenaire, champs, c_arret)

        _gestion(mes_arrets, cle_partenaire)
        _diagnostic(champs, temoin, err, c_arret)
