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
import unicodedata
from datetime import datetime, timezone

import requests
import streamlit as st

VERSION_TRANSPORTS = "4.1"

BASE = "https://api-management-opendata-production.azure-api.net/api/datasets/stibmivb"
URL_ATTENTE = f"{BASE}/rt/WaitingTimes"
# Adresses relevees sur le portail : les arrets sont dans "static", pas "rt",
# et la casse compte (stopDetails, pas StopDetails).
URLS_ARRETS = [f"{BASE}/static/stopDetails", f"{BASE}/static/stopsByLine"]
ENTETE_CLE = "bmc-partner-key"

# Metro et tram sont des listes fermees : tout le reste roule sur pneus.
METRO = {"1", "2", "5", "6"}
TRAMS = {"3", "4", "7", "8", "9", "10", "18", "19", "25", "39", "44", "51",
         "55", "62", "81", "82", "92", "93", "94", "97"}
MODES = {"metro": ("🚇", "métro"), "tram": ("🚊", "tram"), "bus": ("🚌", "bus")}

CATEGORIE = "Arrêt STIB"        # colonne 1 de la feuille Listes

# ----------------------------------------------------------
# VOS ARRETS HABITUELS
# ----------------------------------------------------------
# Completez les numeros, un par sens de circulation, et ils
# s'ajouteront tout seuls au premier lancement. Laissez une liste
# vide et l'arret est simplement ignore.
#
# Pour trouver un numero : stib-mivb.be, rubrique Horaires, choisir
# la ligne, puis la direction, puis l'arret. Le numero se lit a la
# fin de l'adresse du navigateur, apres "_stop=". Recommencez avec
# l'autre direction pour obtenir le second numero.
ARRETS_PAR_DEFAUT = {
    "Langeveld":   [],      # ex : ["1234", "1235"]
    "René Gobert": [],
    "Defré":       [],
}
RAFRAICHISSEMENT = 20           # secondes, en mode direct

# Noms de champs possibles, du plus probable au moins probable.
CANDIDATS = {
    "arret":       ["pointid", "point_id", "stop_id", "stopid", "id", "stop"],
    "ligne":       ["lineid", "line_id", "line", "route_id", "routeid", "route"],
    "passages":    ["passingtimes", "passing_times", "passages", "times"],
    "destination": ["destination", "destination_fr", "direction", "headsign", "terminus"],
    "heure":       ["expectedarrivaltime", "expected_arrival_time", "arrivaltime",
                    "arrival_time", "expectedtime", "time", "passingtime"],
    "nom":         ["name", "stop_name", "stopname", "descr_fr", "descr_nl", "nom",
                    "label", "stopname_fr", "namefr", "name_fr", "title"],
}

CSS = """
<style>
.tr-carte{background:var(--surface,#fff); border:1px solid var(--trait,#ECE0E5);
  border-radius:var(--r,16px); padding:14px 16px 6px; margin:0 0 12px;
  box-shadow:var(--ombre,0 1px 2px rgba(36,27,34,.04));}
.tr-tete{display:flex; align-items:baseline; justify-content:space-between; gap:10px;
  padding-bottom:10px; margin-bottom:2px; border-bottom:1px solid var(--trait,#ECE0E5);}
.tr-nom{font-size:15px; font-weight:700; color:var(--encre,#241B22); letter-spacing:-.01em;
  text-transform:capitalize; overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.tr-compte{font-size:11.5px; font-weight:600; color:var(--gris,#8A7C82); white-space:nowrap;}

.tr-ligne{display:flex; align-items:center; gap:12px; padding:10px 0;
  border-bottom:1px solid var(--trait,#ECE0E5);}
.tr-ligne:last-child{border-bottom:none;}
.tr-badge{flex:0 0 auto; display:flex; align-items:center; gap:5px; min-width:50px;
  justify-content:center; color:#fff; font-size:13px; font-weight:700;
  padding:5px 9px; border-radius:9px; font-variant-numeric:tabular-nums;}
.tr-badge.metro{background:#164C9E;}
.tr-badge.tram{background:#6D3BAF;}
.tr-badge.bus{background:var(--accent,#B0184F);}
.tr-badge .m{font-size:12px;}

.tr-mid{flex:1 1 auto; min-width:0;}
.tr-dest{font-size:14px; font-weight:600; color:var(--encre,#241B22); text-transform:capitalize;
  overflow:hidden; text-overflow:ellipsis; white-space:nowrap;}
.tr-suite{font-size:11.5px; font-weight:500; color:var(--gris,#8A7C82); margin-top:2px;
  font-variant-numeric:tabular-nums;}

.tr-temps{flex:0 0 auto; text-align:right; min-width:52px;}
.tr-temps .n{font-size:21px; font-weight:700; color:var(--encre,#241B22); line-height:1;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em;}
.tr-temps .u{font-size:10px; font-weight:600; color:var(--gris,#8A7C82); display:block;
  margin-top:3px;}
.tr-temps.imminent .n{color:var(--vert,#17683D); font-size:14px;}
.tr-temps.proche .n{color:var(--accent,#B0184F);}

.tr-vide{font-size:13px; font-weight:500; color:var(--gris,#8A7C82); padding:14px 2px;
  line-height:1.5; text-align:center;}
.tr-maj{font-size:11.5px; font-weight:500; color:var(--gris,#8A7C82); text-align:center;
  padding:0 0 10px;}
.tr-live{display:inline-block; width:6px; height:6px; border-radius:50%;
  background:var(--vert,#17683D); margin-right:6px; vertical-align:middle;
  animation:trpouls 2.4s ease-in-out infinite;}
@keyframes trpouls{0%,100%{opacity:1;} 50%{opacity:.3;}}
@media (prefers-reduced-motion:reduce){ .tr-live{animation:none;} }
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


def installer_defauts(existants):
    """Ajoute les arrêts habituels, une seule fois, s'ils manquent.

    Protégé par un drapeau de session : sans lui, un échec d'écriture
    relancerait l'ajout à chaque passage.
    """
    if st.session_state.get("tr_defauts_faits"):
        return False
    st.session_state["tr_defauts_faits"] = True
    connus = {a["nom"].strip().lower() for a in existants}
    ajoutes = False
    for nom, ids in ARRETS_PAR_DEFAUT.items():
        if ids and nom.strip().lower() not in connus:
            try:
                ajouter_arret(nom, ids)
                ajoutes = True
            except Exception:
                pass
    return ajoutes


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


def normaliser_id(identifiant):
    """Le portail écrit les arrêts sur quatre chiffres : 821 devient 0821."""
    brut = str(identifiant or "").strip()
    return brut.zfill(4) if brut.isdigit() and len(brut) < 4 else brut


def _valeur(dico, noms):
    """Première valeur trouvée parmi plusieurs orthographes possibles."""
    if not isinstance(dico, dict):
        return None
    bas = {str(c).lower(): v for c, v in dico.items()}
    for nom in noms:
        if nom in bas:
            return bas[nom]
    return None


def liste_passages(enregistrement, c_passages):
    """Les passages d'un enregistrement.

    Le portail range les prochains véhicules dans un champ « passingtimes »
    qui contient du JSON encodé en texte : il faut le décoder avant de lire
    l'heure et la destination.
    """
    brut = enregistrement.get(c_passages) if c_passages else None
    if brut in (None, ""):
        return [enregistrement]          # jeu de données à plat : un passage par ligne
    if isinstance(brut, str):
        try:
            brut = json.loads(brut)
        except ValueError:
            return []
    if isinstance(brut, dict):
        return [brut]
    return list(brut) if isinstance(brut, list) else []


def regrouper(resultats, champs):
    """[(ligne, destination, [minutes])] trié du plus imminent au plus lointain."""
    c_passages = choisir(champs, "passages")
    c_ligne = choisir(champs, "ligne")
    c_heure = choisir(champs, "heure")
    groupes = {}
    for enregistrement in resultats or []:
        defaut_ligne = texte_lisible(enregistrement.get(c_ligne)) if c_ligne else ""
        for passage in liste_passages(enregistrement, c_passages):
            heure = _valeur(passage, ["expectedarrivaltime", "expected_arrival_time",
                                      "arrivaltime", "arrival_time", "time"])
            if heure is None and c_heure:
                heure = passage.get(c_heure)
            minutes = minutes_avant(heure)
            if minutes is None:
                continue
            ligne = texte_lisible(_valeur(passage, ["lineid", "line_id", "line"])) \
                or defaut_ligne or "?"
            destination = texte_lisible(_valeur(
                passage, ["destination", "direction", "headsign", "terminus"]))
            groupes.setdefault((ligne, destination or "—"), []).append(minutes)
    listes = [(ligne, dest, sorted(m)) for (ligne, dest), m in groupes.items()]
    listes.sort(key=lambda e: (e[2][0] if e[2] else 999, e[0]))
    return listes


def mode_de(ligne):
    """Métro, tram ou bus, d'après le numéro de la ligne."""
    numero = str(ligne or "").strip().upper().lstrip("T")
    if numero in METRO:
        return "metro"
    if numero in TRAMS:
        return "tram"
    return "bus"


def libelle(minutes):
    """Texte simple, pour les cas où l'habillage n'est pas disponible."""
    if not minutes:
        return "—"
    return " · ".join("à quai" if m == 0 else f"{m} min" for m in minutes[:3])


def rendu_ligne(ligne, destination, minutes):
    """Une rangée : badge coloré, destination, minutes en évidence."""
    mode = mode_de(ligne)
    icone, _ = MODES[mode]
    prochain = minutes[0] if minutes else None
    suite = minutes[1:3]

    if prochain is None:
        temps = "<div class='tr-temps'><span class='n'>—</span></div>"
    elif prochain == 0:
        temps = "<div class='tr-temps imminent'><span class='n'>à quai</span></div>"
    else:
        classe = "tr-temps proche" if prochain <= 2 else "tr-temps"
        temps = (f"<div class='{classe}'><span class='n'>{prochain}</span>"
                 f"<span class='u'>min</span></div>")

    apres = ("<div class='tr-suite'>puis "
             + ", ".join(f"{m} min" for m in suite) + "</div>") if suite else ""

    return (f"<div class='tr-ligne'>"
            f"<span class='tr-badge {mode}'><span class='m'>{icone}</span>{ligne}</span>"
            f"<div class='tr-mid'><div class='tr-dest'>{destination.lower()}</div>{apres}</div>"
            f"{temps}</div>")


# ----------------------------------------------------------
# Affichage
# ----------------------------------------------------------
def _tableau(mes_arrets, cle_partenaire, champs, c_arret):
    """Le bloc qui se rafraîchit tout seul en mode direct."""
    if not c_arret:
        st.markdown("<div class='tr-vide'>Le champ identifiant l'arrêt n'a pas été reconnu. "
                    "Ouvrez le volet Diagnostic ci-dessous.</div>", unsafe_allow_html=True)
        return

    st.markdown(f"<div class='tr-maj'><span class='tr-live'></span>"
                f"en direct · {datetime.now().strftime('%H:%M:%S')}</div>",
                unsafe_allow_html=True)

    for arret in mes_arrets:
        resultats, souci = [], None
        for identifiant in arret["ids"]:
            donnees, err = interroger(
                URL_ATTENTE,
                {"where": f'{c_arret}="{normaliser_id(identifiant)}"', "limit": 40},
                cle_partenaire,
            )
            if err:
                souci = err
                continue
            resultats.extend(donnees.get("results") or [])

        lignes = regrouper(resultats, champs)
        if lignes:
            modes = {mode_de(ligne) for ligne, _, _ in lignes}
            compte = " · ".join(MODES[m][0] for m in ("metro", "tram", "bus") if m in modes)
            compte += f"  {len(lignes)} ligne" + ("s" if len(lignes) > 1 else "")
        else:
            compte = "—"

        corps = "".join(rendu_ligne(ligne, destination, minutes)
                        for ligne, destination, minutes in lignes[:6])
        if not corps:
            message = f"Indisponible : {souci}" if souci else "Aucun passage annoncé."
            corps = f"<div class='tr-vide'>{message}</div>"

        st.markdown(
            f"<div class='tr-carte'><div class='tr-tete'>"
            f"<span class='tr-nom'>{arret['nom'].lower()}</span>"
            f"<span class='tr-compte'>{compte}</span></div>{corps}</div>",
            unsafe_allow_html=True,
        )


# Version rafraîchie automatiquement, si la version de Streamlit le permet.
# Définie une seule fois au chargement : un fragment recréé à chaque passage
# perdrait son identité et ne se rafraîchirait jamais.
try:
    _tableau_direct = st.fragment(run_every=RAFRAICHISSEMENT)(_tableau)
except Exception:
    _tableau_direct = _tableau


def sans_accents(texte):
    """« Defré » et « defre » doivent se retrouver l'un l'autre."""
    plat = unicodedata.normalize("NFKD", str(texte or ""))
    return "".join(c for c in plat if not unicodedata.combining(c)).lower().strip()


@st.cache_data(ttl=86400, show_spinner=False)
def catalogue_arrets(cle_partenaire):
    """Tous les arrêts du réseau : [(identifiant, nom)], url utilisée, erreur.

    Le catalogue est chargé une fois par jour et fouillé ensuite en local :
    c'est plus fiable que de filtrer côté serveur, dont la syntaxe et les noms
    de champs ne sont pas documentés.
    """
    dernier = "Catalogue des arrêts introuvable."
    for url in URLS_ARRETS:
        champs, _, err = champs_disponibles(url, cle_partenaire)
        if err or not champs:
            dernier = err or "Jeu de données vide."
            continue
        c_id, c_nom = choisir(champs, "arret"), choisir(champs, "nom")
        if not (c_id and c_nom):
            dernier = f"Champs non reconnus dans {url.rsplit('/', 2)[-2]}."
            continue
        tous, vus = [], set()
        for page in range(6):                      # 6 000 arrêts au maximum
            donnees, err = interroger(
                url, {"limit": 1000, "offset": page * 1000}, cle_partenaire)
            if err or not donnees:
                break
            resultats = donnees.get("results") or []
            for enregistrement in resultats:
                identifiant = str(enregistrement.get(c_id) or "").strip()
                nom = texte_lisible(enregistrement.get(c_nom)).strip()
                if identifiant and nom and identifiant not in vus:
                    vus.add(identifiant)
                    tous.append((identifiant, nom))
            if len(resultats) < 1000:
                break
        if tous:
            return tous, url, None
    return [], None, dernier


def chercher_par_nom(texte, cle_partenaire):
    """{nom d'arrêt: [identifiants]} — un identifiant par sens de circulation."""
    tous, _, err = catalogue_arrets(cle_partenaire)
    if err:
        return {}, err
    cherche = sans_accents(texte)
    if len(cherche) < 2:
        return {}, None
    groupes = {}
    for identifiant, nom in tous:
        if cherche in sans_accents(nom):
            groupes.setdefault(nom, []).append(identifiant)
    return {nom: sorted(ids) for nom, ids in sorted(groupes.items())}, None


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
            groupes, err = chercher_par_nom(recherche, cle_partenaire)
            if err:
                st.caption(f"Recherche indisponible : {err}")
            elif not groupes:
                st.caption("Aucun arrêt de ce nom.")
            deja = {i for a in mes_arrets for i in a["ids"]}
            for nom, ids in list(groupes.items())[:8]:
                marque = "✅ " if set(ids) <= deja else "＋ "
                sens = "les deux sens" if len(ids) == 2 else f"{len(ids)} quai(s)"
                if st.button(f"{marque}{nom} · {sens}", key=f"tr_add_{'_'.join(ids)}"):
                    ajouter_arret(nom, ids)
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
                          for role in ("arret", "ligne", "passages", "destination", "heure")))
        if temoin:
            st.write("**Premier enregistrement reçu**")
            st.json(temoin)
        tous, url, err_cat = catalogue_arrets(cle())
        st.write("**Catalogue des arrêts**")
        st.code(f"{len(tous)} arrêts chargés"
                + (f"\nsource : {url}" if url else "\nadresses tentées :\n  "
                   + "\n  ".join(URLS_ARRETS))
                + (f"\n{err_cat}" if err_cat else ""))
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
    if installer_defauts(mes_arrets):
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
