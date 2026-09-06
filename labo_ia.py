# ==========================================================
# Labo IA & Marches - module autonome pour "Notre Assistant"
# Version 5.0
# ==========================================================
# Cinq onglets, reserves aux personnes qui connaissent le code :
#
#   Marches   tableau de bord : cours, performances par horizon,
#             mesures de risque, comparaison base 100, correlations,
#             lecture automatique de la seance.
#   Analyse   etude d'un actif : chandeliers, moyennes mobiles,
#             bandes de Bollinger, RSI, MACD, volumes, niveaux,
#             fiche d'identite, lecture automatique detaillee.
#   Actus     les dernieres depeches liees a un actif.
#   Alertes   des seuils de prix, verifies a chaque chargement.
#   Notes     le carnet, avec recherche, filtres et export.
#
# Ni journal de positions, ni conseil, ni simulation : le module
# decrit des cours passes, rien de plus.
#
# Branchement dans l'application principale (inchange) :
#
#     elif page_cle == "ialab" and st.session_state.get("mode_ia"):
#         import labo_ia
#         labo_ia.render({ ... })
#
# Le module n'ecrit que dans la feuille "IA_Lab" (4 colonnes :
# Date, Sujet, Contenu, Type). Aucune migration necessaire.
#
# Options facultatives, dans les secrets Streamlit :
#
#     [anthropic]
#     api_key = "sk-ant-..."      # active le commentaire redige
#     modele  = "claude-sonnet-5" # facultatif
#
# Sections :
#   1. Constantes            6. Reglages, notes, alertes
#   2. Acces a l'app         7. Lectures automatiques & IA
#   3. Mise en forme         8. Onglets
#   4. Donnees de marche     9. render()
#   5. Graphiques
# ==========================================================

import json
import math
import re
import traceback
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

# ==========================================================
# 1. CONSTANTES
# ==========================================================
VERSION_LABO = "5.0"

CFG_SUJET = "Paramètres du labo"
TYPE_CONFIG = "Config"
TYPE_ALERTE = "Alerte"

ONGLETS = ["📈 Marchés", "🔬 Analyse", "📰 Actus", "🔔 Alertes", "📚 Notes"]

# nom lisible : (ticker, famille, symbole de cotation)
UNIVERS = {
    "Bitcoin":        ("BTC-USD",   "Crypto", "$"),
    "Ethereum":       ("ETH-USD",   "Crypto", "$"),
    "Solana":         ("SOL-USD",   "Crypto", "$"),
    "Cardano":        ("ADA-USD",   "Crypto", "$"),
    "Or":             ("GC=F",      "Matières premières", "$"),
    "Argent":         ("SI=F",      "Matières premières", "$"),
    "Cuivre":         ("HG=F",      "Matières premières", "$"),
    "Pétrole WTI":    ("CL=F",      "Matières premières", "$"),
    "Gaz naturel":    ("NG=F",      "Matières premières", "$"),
    "S&P 500":        ("^GSPC",     "Indices", "pts"),
    "Nasdaq 100":     ("^NDX",      "Indices", "pts"),
    "Dow Jones":      ("^DJI",      "Indices", "pts"),
    "CAC 40":         ("^FCHI",     "Indices", "pts"),
    "BEL 20":         ("^BFX",      "Indices", "pts"),
    "DAX":            ("^GDAXI",    "Indices", "pts"),
    "Euro Stoxx 50":  ("^STOXX50E", "Indices", "pts"),
    "Nikkei 225":     ("^N225",     "Indices", "pts"),
    "VIX (peur)":     ("^VIX",      "Indices", "pts"),
    "Apple":          ("AAPL",      "Actions", "$"),
    "Nvidia":         ("NVDA",      "Actions", "$"),
    "Microsoft":      ("MSFT",      "Actions", "$"),
    "Alphabet":       ("GOOGL",     "Actions", "$"),
    "Amazon":         ("AMZN",      "Actions", "$"),
    "Meta":           ("META",      "Actions", "$"),
    "Tesla":          ("TSLA",      "Actions", "$"),
    "ASML":           ("ASML.AS",   "Actions", "€"),
    "AB InBev":       ("ABI.BR",    "Actions", "€"),
    "UCB":            ("UCB.BR",    "Actions", "€"),
    "Solvay":         ("SOLB.BR",   "Actions", "€"),
    "KBC":            ("KBC.BR",    "Actions", "€"),
    "LVMH":           ("MC.PA",     "Actions", "€"),
    "TotalEnergies":  ("TTE.PA",    "Actions", "€"),
    "EUR/USD":        ("EURUSD=X",  "Devises", ""),
    "EUR/GBP":        ("EURGBP=X",  "Devises", ""),
    "USD/JPY":        ("USDJPY=X",  "Devises", ""),
}
NOM_PAR_TICKER = {t: n for n, (t, _, _) in UNIVERS.items()}
FAMILLES = ["Crypto", "Indices", "Actions", "Matières premières", "Devises"]

# Sélections toutes prêtes, un appui suffit.
BOUQUETS = {
    "Nos favoris":   ["Bitcoin", "Or", "S&P 500", "Nvidia"],
    "Crypto":        ["Bitcoin", "Ethereum", "Solana"],
    "Indices":       ["S&P 500", "Nasdaq 100", "CAC 40", "BEL 20", "Euro Stoxx 50"],
    "Belgique":      ["BEL 20", "AB InBev", "UCB", "Solvay", "KBC"],
    "Tech US":       ["Apple", "Nvidia", "Microsoft", "Alphabet", "Amazon"],
    "Refuges":       ["Or", "Argent", "EUR/USD", "VIX (peur)"],
}

# libellé : (période yfinance, intervalle, barres par an pour l'annualisation)
PERIODES = {
    "1J":  ("1d",  "5m",  252 * 78),
    "5J":  ("5d",  "15m", 252 * 26),
    "1M":  ("1mo", "1h",  252 * 7),
    "6M":  ("6mo", "1d",  252),
    "YTD": ("ytd", "1d",  252),
    "1A":  ("1y",  "1d",  252),
    "5A":  ("5y",  "1wk", 52),
}

# libellé : nombre de séances en arrière (None = depuis le 1er janvier)
HORIZONS = [("1 j", 1), ("1 sem", 5), ("1 mois", 21), ("3 mois", 63),
            ("6 mois", 126), ("YTD", None), ("1 an", 252)]

REFERENCE = "S&P 500"          # utilisé pour la sensibilité (bêta)

PALETTE = ["#C2185B", "#6D3BAF", "#0E7490", "#A65B12", "#17683D", "#164C9E",
           "#B3261E", "#0F766E"]

TYPES_NOTE = ["Note", "À retenir", "Idée", "Suivi"]

MODELE_IA_DEFAUT = "claude-sonnet-5"

# ==========================================================
# 2. ACCÈS À L'APPLICATION HÔTE
# ==========================================================
_CTX = {}

REQUIS = ["rows", "add_row", "delete_row", "set_cell", "pad",
          "conteneur", "titre", "vide", "pills"]


def _f(nom):
    fonction = _CTX.get(nom)
    if fonction is None:
        raise RuntimeError(f"Contexte incomplet : « {nom} » n'a pas été transmis à labo_ia.render().")
    return fonction


def rows(feuille):
    return _f("rows")(feuille)


def add_row(feuille, ligne):
    return _f("add_row")(feuille, ligne)


def delete_row(feuille, index, libelle="Élément supprimé"):
    return _f("delete_row")(feuille, index, True, libelle)


def set_cell(feuille, index, colonne, valeur):
    return _f("set_cell")(feuille, index, colonne, valeur)


def pad(ligne, n):
    return _f("pad")(ligne, n)


def conteneur(cle=None, bordure=True):
    return _f("conteneur")(cle, bordure)


def titre(texte):
    return _f("titre")(texte)


def vide(texte):
    return _f("vide")(texte)


def pills(cle, options, defaut=None, cols=3):
    """Un défaut est toujours transmis : sans lui, certaines implémentations
    renvoient None et la suite de la page part en erreur."""
    if defaut is None and options:
        defaut = options[0]
    return _f("pills")(cle, options, defaut, cols)


def reset_after(**champs):
    """Applique des valeurs au prochain rerun : seule façon sûre de vider un
    widget déjà instancié, Streamlit refusant l'affectation directe."""
    fonction = _CTX.get("reset_after")
    if fonction:
        fonction(**champs)
        return True
    return False


def _defaut(cle, valeur):
    """Valeur initiale d'un widget, posée avant sa création."""
    if cle not in st.session_state:
        st.session_state[cle] = valeur

# ==========================================================
# 3. MISE EN FORME & COMPOSANTS
# ==========================================================
FINE = "\u202f"  # espace fine insécable : jamais de nombre coupé en deux lignes


def _nan(valeur):
    if valeur is None:
        return True
    try:
        f = float(valeur)
    except (TypeError, ValueError):
        return True
    return math.isnan(f) or math.isinf(f)


def fnum(valeur, dec=2, suffixe=""):
    if _nan(valeur):
        return "—"
    brut = f"{float(valeur):,.{dec}f}".replace(",", "§").replace(".", ",").replace("§", FINE)
    return f"{brut}{FINE}{suffixe}" if suffixe else brut


def fprix(valeur, devise="$"):
    """Décimales adaptées à l'ordre de grandeur : 68 420 $ mais 0,4213 $."""
    if _nan(valeur):
        return "—"
    amplitude = abs(float(valeur))
    dec = 0 if amplitude >= 1000 else (2 if amplitude >= 5 else 4)
    return fnum(valeur, dec, devise)


def fpct(valeur, dec=2, signe=True):
    if _nan(valeur):
        return "—"
    valeur = float(valeur)
    prefixe = ("+" if valeur >= 0 else "-") if signe else ("-" if valeur < 0 else "")
    return f"{prefixe}{fnum(abs(valeur), dec)}{FINE}%"


def fgros(valeur):
    """Capitalisations et volumes : 1,42 Md au lieu de 1 420 000 000."""
    if _nan(valeur):
        return "—"
    valeur = float(valeur)
    for seuil, unite in ((1e12, "Bn"), (1e9, "Md"), (1e6, "M"), (1e3, "k")):
        if abs(valeur) >= seuil:
            return fnum(valeur / seuil, 2, unite)
    return fnum(valeur, 0)


def devise(nom):
    return UNIVERS.get(nom, ("", "", "$"))[2]


def ton(valeur, seuil=1e-9):
    if _nan(valeur) or abs(float(valeur)) < seuil:
        return "flat"
    return "up" if float(valeur) > 0 else "down"


def cell_pct(valeur, dec=2):
    """Une cellule de tableau colorée selon le signe."""
    return f"<span class='{ton(valeur)}'>{fpct(valeur, dec)}</span>"


def kpis(cartes, largeur=152):
    """cartes : liste de dicts {label, valeur, delta, delta_ton, aide}."""
    blocs = []
    for carte in cartes:
        bas = ""
        if carte.get("delta"):
            bas = f"<div class='d {carte.get('delta_ton', 'flat')}'>{carte['delta']}</div>"
        elif carte.get("aide"):
            bas = f"<div class='d flat'>{carte['aide']}</div>"
        blocs.append(
            f"<div class='lab-kpi'><div class='l'>{carte['label']}</div>"
            f"<div class='v'>{carte['valeur']}</div>{bas}</div>"
        )
    st.markdown(f"<div class='lab-grid' style='--mini:{largeur}px'>{''.join(blocs)}</div>",
                unsafe_allow_html=True)


def table(colonnes, lignes):
    """colonnes : liste de (titre, classe 'txt' ou 'num').

    Tableau défilable, en-tête et première colonne figées : sur téléphone,
    aucune valeur n'est tronquée, on fait glisser horizontalement.
    """
    if not lignes:
        return
    entete = "".join(f"<th class='{cls}'>{lib}</th>" for lib, cls in colonnes)
    corps = []
    for ligne in lignes:
        cellules = "".join(
            f"<td class='{colonnes[i][1] if i < len(colonnes) else 'txt'}'>{valeur}</td>"
            for i, valeur in enumerate(ligne)
        )
        corps.append(f"<tr>{cellules}</tr>")
    st.markdown(
        "<div class='lab-tablewrap'><table class='lab-table'>"
        f"<thead><tr>{entete}</tr></thead><tbody>{''.join(corps)}</tbody></table></div>",
        unsafe_allow_html=True,
    )


def note(texte, style="info"):
    st.markdown(f"<div class='lab-note {style}'>{texte}</div>", unsafe_allow_html=True)


def sous_titre(texte):
    st.markdown(f"<div class='lab-sec'>{texte}</div>", unsafe_allow_html=True)


def puces(phrases, style=""):
    """La lecture automatique : une idée par ligne, pas un pavé."""
    if not phrases:
        return
    items = "".join(f"<li>{p}</li>" for p in phrases)
    st.markdown(f"<ul class='lab-liste {style}'>{items}</ul>", unsafe_allow_html=True)


def jauge(pourcent, gauche="", droite=""):
    """Barre de position : où se situe le cours dans son couloir."""
    if _nan(pourcent):
        return
    valeur = max(0.0, min(100.0, float(pourcent)))
    st.markdown(
        f"<div class='lab-jauge'><div class='piste'><div class='curseur' "
        f"style='left:{valeur:.1f}%'></div></div>"
        f"<div class='bords'><span>{gauche}</span><span>{droite}</span></div></div>",
        unsafe_allow_html=True)


CSS = """
<style>
@media (min-width:760px){ .block-container{max-width:940px !important;} }

.lab-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(var(--mini,148px),1fr));
  gap:8px; margin:4px 0 16px;}
.lab-kpi{background:var(--surface,#fff); border:1.5px solid var(--trait,#F3C7DA);
  border-radius:var(--r,16px); padding:12px 14px; min-width:0; overflow:hidden;}
.lab-kpi .l{font-size:11.5px; font-weight:600; color:var(--gris,#9B7F8C);
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:5px;}
.lab-kpi .v{font-size:clamp(16px,4vw,21px); font-weight:700; color:var(--accent-fonce,#8C1444);
  line-height:1.1; letter-spacing:-.02em; font-variant-numeric:tabular-nums; white-space:nowrap;}
.lab-kpi .d{font-size:11.5px; font-weight:600; margin-top:4px; white-space:nowrap;
  font-variant-numeric:tabular-nums;}
.lab-kpi .up{color:var(--vert,#17683D);} .lab-kpi .down{color:var(--rouge,#B3261E);}
.lab-kpi .d.flat{color:var(--gris,#9B7F8C);}

.lab-tablewrap{border:1.5px solid var(--trait,#F3C7DA); border-radius:var(--r,16px);
  background:var(--surface,#fff); overflow:auto; max-height:460px; margin:4px 0 16px;
  -webkit-overflow-scrolling:touch;}
.lab-table{border-collapse:separate; border-spacing:0; width:100%; font-size:13px;}
.lab-table th{position:sticky; top:0; z-index:3; background:var(--surface,#fff);
  color:var(--gris,#9B7F8C); text-align:left; font-size:11.5px; font-weight:600;
  padding:11px 13px; white-space:nowrap; border-bottom:1px solid var(--trait,#F3C7DA);}
.lab-table td{padding:10px 13px; white-space:nowrap; font-weight:600;
  color:var(--encre,#3A1A28); font-variant-numeric:tabular-nums;
  border-bottom:1px solid var(--trait-doux,#FBE7F0);}
.lab-table td.num, .lab-table th.num{text-align:right;}
.lab-table tbody tr:last-child td{border-bottom:none;}
.lab-table td:first-child{position:sticky; left:0; z-index:2; background:var(--surface,#fff);
  box-shadow:1px 0 0 var(--trait,#F3C7DA);}
.lab-table th:first-child{left:0; z-index:4;}
.lab-table .up{color:var(--vert,#17683D);} .lab-table .down{color:var(--rouge,#B3261E);}
.lab-table .flat{color:var(--gris,#9B7F8C);}

.lab-note{border-radius:12px; padding:12px 14px; font-size:13px; font-weight:500;
  margin:6px 0 14px; line-height:1.55; background:var(--accent-doux,#FDF0F6);
  border:1px solid var(--accent-bord,#F3C7DA); color:var(--accent,#C2185B);}
.lab-note.warn{background:#FDF4EA; border-color:#EBD3B4; color:var(--ambre,#A65B12);}
.lab-note.calme{background:transparent; border-color:var(--trait,#F3C7DA);
  color:var(--gris,#9B7F8C);}
.lab-sec{font-weight:700; font-size:15px; color:var(--accent-fonce,#8C1444); margin:22px 0 8px;
  letter-spacing:-.01em;}

.lab-liste{margin:2px 0 14px; padding:12px 16px 12px 30px; border-radius:12px;
  background:var(--surface,#fff); border:1.5px solid var(--trait,#F3C7DA);}
.lab-liste li{font-size:13.5px; font-weight:500; line-height:1.6; color:var(--encre,#3A1A28);
  margin:3px 0;}
.lab-liste li b{color:var(--accent-fonce,#8C1444);}
.lab-liste.calme li{color:var(--gris,#9B7F8C);}

.lab-jauge{margin:2px 0 16px;}
.lab-jauge .piste{position:relative; height:8px; border-radius:999px;
  background:linear-gradient(90deg,#B3261E22,#F3C7DA55,#17683D22);
  border:1px solid var(--trait,#F3C7DA);}
.lab-jauge .curseur{position:absolute; top:-4px; width:14px; height:14px; border-radius:50%;
  background:var(--accent,#C2185B); border:2px solid var(--surface,#fff); transform:translateX(-50%);
  box-shadow:0 2px 6px rgba(0,0,0,.18);}
.lab-jauge .bords{display:flex; justify-content:space-between; margin-top:5px;
  font-size:11px; font-weight:600; color:var(--gris,#9B7F8C);}

.lab-actu{display:block; background:var(--surface,#fff); border:1.5px solid var(--trait,#F3C7DA);
  border-radius:12px; padding:11px 13px; margin-bottom:8px; text-decoration:none !important;}
.lab-actu .t{font-size:13.5px; font-weight:700; color:var(--encre,#3A1A28); line-height:1.4;}
.lab-actu .s{font-size:11.5px; font-weight:600; color:var(--gris,#9B7F8C); margin-top:4px;}

[class*="st-key-labrow"] [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important;
  gap:10px !important;}
[class*="st-key-labrow"] [data-testid="stHorizontalBlock"] > div{min-width:150px !important;}
</style>
"""

# ==========================================================
# 4. DONNÉES DE MARCHÉ
# ==========================================================
@st.cache_data(ttl=180, show_spinner=False)
def _telecharger(tickers, periode, intervalle):
    """Renvoie {ticker: DataFrame OHLCV}, message d'erreur."""
    try:
        import yfinance as yf
    except ImportError:
        return {}, "Le module yfinance n'est pas installé (pip install yfinance)."
    try:
        brut = yf.download(list(tickers), period=periode, interval=intervalle,
                           progress=False, auto_adjust=False, group_by="column", threads=True)
    except Exception as err:
        return {}, f"Téléchargement impossible : {str(err)[:120]}"
    if brut is None or brut.empty:
        return {}, "Aucune donnée pour cette période — le marché est peut-être fermé."

    paquets = {}
    if isinstance(brut.columns, pd.MultiIndex):
        for ticker in tickers:
            try:
                sous = brut.xs(ticker, axis=1, level=-1).dropna(how="all")
            except Exception:
                continue
            if not sous.empty:
                paquets[ticker] = sous
    else:
        sous = brut.dropna(how="all")
        if not sous.empty:
            paquets[list(tickers)[0]] = sous

    if not paquets:
        return {}, "Aucune série exploitable pour cette sélection."
    return paquets, None


def marche(noms, periode_label):
    """noms : libellés de UNIVERS. Renvoie {nom: DataFrame}, barres/an, erreur.

    Ne lève jamais : une panne réseau doit afficher un message, pas casser la page.
    """
    periode, intervalle, barres_an = PERIODES.get(periode_label, PERIODES["1J"])
    tickers = tuple(sorted({UNIVERS[n][0] for n in noms if n in UNIVERS}))
    if not tickers:
        return {}, barres_an, "Sélectionnez au moins un actif."
    try:
        paquets, err = _telecharger(tickers, periode, intervalle)
    except Exception as erreur:
        return {}, barres_an, f"Marchés injoignables : {str(erreur)[:120]}"
    return {NOM_PAR_TICKER.get(t, t): df for t, df in paquets.items()}, barres_an, err


@st.cache_data(ttl=900, show_spinner=False)
def _historique(tickers):
    """Deux ans de cours quotidiens : la base des performances et du risque."""
    paquets, err = _telecharger(tuple(tickers), "2y", "1d")
    series = {}
    for ticker, df in paquets.items():
        if "Close" in df:
            cloture = df["Close"].dropna()
            if len(cloture) > 5:
                series[ticker] = cloture
    return series, err


def historique(noms, avec_reference=True):
    """{nom: série de clôtures quotidiennes} sur deux ans."""
    voulus = list(noms) + ([REFERENCE] if avec_reference and REFERENCE not in noms else [])
    tickers = tuple(sorted({UNIVERS[n][0] for n in voulus if n in UNIVERS}))
    if not tickers:
        return {}, "Sélectionnez au moins un actif."
    try:
        series, err = _historique(tickers)
    except Exception as erreur:
        return {}, f"Historique injoignable : {str(erreur)[:120]}"
    return {NOM_PAR_TICKER.get(t, t): s for t, s in series.items()}, err


# --- Indicateurs ------------------------------------------------------------
def moyenne_mobile(serie, n):
    return serie.rolling(n).mean()


def rsi(serie, n=14):
    """Force relative : au-dessus de 70 le mouvement de hausse est tendu,
    en dessous de 30 c'est la baisse qui l'est."""
    variation = serie.diff()
    hausses = variation.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    baisses = (-variation.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    ratio = hausses / baisses.replace(0, float("nan"))
    return 100 - (100 / (1 + ratio))


def macd(serie, court=12, long=26, signal=9):
    rapide = serie.ewm(span=court, adjust=False).mean()
    lente = serie.ewm(span=long, adjust=False).mean()
    ligne = rapide - lente
    ligne_signal = ligne.ewm(span=signal, adjust=False).mean()
    return ligne, ligne_signal, ligne - ligne_signal


def bollinger(serie, n=20, k=2):
    milieu = serie.rolling(n).mean()
    ecart = serie.rolling(n).std()
    return milieu + k * ecart, milieu, milieu - k * ecart


def volatilite(serie, barres_an):
    """Amplitude typique des variations, ramenée à une échelle annuelle."""
    variations = serie.pct_change(fill_method=None).dropna()
    if len(variations) < 3:
        return float("nan")
    return float(variations.std() * math.sqrt(barres_an) * 100)


def repli_max(serie):
    """La pire chute depuis un sommet, en pourcentage."""
    if serie is None or len(serie) < 2:
        return float("nan")
    return float((serie / serie.cummax() - 1).min() * 100)


def beta(serie, reference):
    """Sensibilité : 1,2 = bouge environ 20 % plus fort que la référence."""
    try:
        paire = pd.concat([serie, reference], axis=1).dropna()
        if len(paire) < 30:
            return float("nan")
        variations = paire.pct_change(fill_method=None).dropna()
        variance = variations.iloc[:, 1].var()
        if not variance:
            return float("nan")
        return float(variations.iloc[:, 0].cov(variations.iloc[:, 1]) / variance)
    except Exception:
        return float("nan")


def performances(cloture):
    """Rendements sur chaque horizon, en pourcentage."""
    sortie = {}
    if cloture is None or len(cloture) < 2:
        return {libelle: float("nan") for libelle, _ in HORIZONS}
    dernier = float(cloture.iloc[-1])
    for libelle, seances in HORIZONS:
        if seances is None:                       # depuis le 1er janvier
            debut_annee = pd.Timestamp(date(date.today().year, 1, 1))
            try:
                index = cloture.index
                if getattr(index, "tz", None) is not None:
                    debut_annee = debut_annee.tz_localize(index.tz)
                avant = cloture[index >= debut_annee]
                reference = float(avant.iloc[0]) if len(avant) else float("nan")
            except Exception:
                reference = float("nan")
        elif len(cloture) > seances:
            reference = float(cloture.iloc[-1 - seances])
        else:
            reference = float("nan")
        sortie[libelle] = (dernier / reference - 1) * 100 if reference else float("nan")
    return sortie


def niveaux(cloture, fenetre=5, maxi=3):
    """Sommets et creux locaux : les paliers que le cours a déjà testés."""
    if cloture is None or len(cloture) < fenetre * 3:
        return [], []
    valeurs = cloture.tail(260)
    hauts = valeurs[(valeurs == valeurs.rolling(fenetre * 2 + 1, center=True).max())]
    bas = valeurs[(valeurs == valeurs.rolling(fenetre * 2 + 1, center=True).min())]
    dernier = float(valeurs.iloc[-1])
    resistances = sorted({round(float(v), 6) for v in hauts if float(v) > dernier * 1.002})
    supports = sorted({round(float(v), 6) for v in bas if float(v) < dernier * 0.998}, reverse=True)
    return supports[:maxi], resistances[:maxi]


def profil(df, barres_an, reference=None):
    """Photo d'un actif sur la période chargée : que des lectures de cours."""
    if df is None or "Close" not in df:
        return None
    cloture = df["Close"].dropna()
    if len(cloture) < 2:
        return None
    dernier, premier = float(cloture.iloc[-1]), float(cloture.iloc[0])
    p = {
        "serie": cloture,
        "dernier": dernier,
        "premier": premier,
        "var": (dernier / premier - 1) * 100 if premier else float("nan"),
        "haut": float(cloture.max()),
        "bas": float(cloture.min()),
        "moyenne": float(cloture.mean()),
        "vol": volatilite(cloture, barres_an),
        "repli": repli_max(cloture),
    }
    amplitude = p["haut"] - p["bas"]
    # Position du dernier cours dans le couloir de la période, en pourcentage.
    p["position"] = ((dernier - p["bas"]) / amplitude * 100) if amplitude else float("nan")
    for n in (20, 50, 200):
        p[f"mm{n}"] = float(moyenne_mobile(cloture, n).iloc[-1]) if len(cloture) >= n else float("nan")
    p["ecart20"] = (dernier / p["mm20"] - 1) * 100 if not _nan(p["mm20"]) else float("nan")
    p["ecart50"] = (dernier / p["mm50"] - 1) * 100 if not _nan(p["mm50"]) else float("nan")
    p["ecart200"] = (dernier / p["mm200"] - 1) * 100 if not _nan(p["mm200"]) else float("nan")
    try:
        p["rsi"] = float(rsi(cloture).iloc[-1])
    except Exception:
        p["rsi"] = float("nan")
    try:
        ligne, signal, _ = macd(cloture)
        p["macd"] = float(ligne.iloc[-1])
        p["macd_signal"] = float(signal.iloc[-1])
    except Exception:
        p["macd"] = p["macd_signal"] = float("nan")
    if "Volume" in df:
        volumes = df["Volume"].dropna()
        p["volume"] = float(volumes.iloc[-1]) if len(volumes) else float("nan")
        p["volume_moyen"] = float(volumes.tail(20).mean()) if len(volumes) >= 5 else float("nan")
    else:
        p["volume"] = p["volume_moyen"] = float("nan")
    p["beta"] = beta(cloture, reference) if reference is not None else float("nan")
    return p


# --- Fiche d'identité & dépêches -------------------------------------------
@st.cache_data(ttl=3600, show_spinner=False)
def fiche(ticker):
    """Quelques repères sur l'actif, quand la source en fournit."""
    try:
        import yfinance as yf
    except ImportError:
        return {}
    donnees = {}
    try:
        objet = yf.Ticker(ticker)
        try:
            brut = objet.get_info()
        except Exception:
            brut = getattr(objet, "info", {}) or {}
        if isinstance(brut, dict):
            donnees = brut
    except Exception:
        return {}
    garde = {
        "Secteur": donnees.get("sector"),
        "Industrie": donnees.get("industry"),
        "Pays": donnees.get("country"),
        "Capitalisation": donnees.get("marketCap"),
        "Bénéfice par action": donnees.get("trailingEps"),
        "PER": donnees.get("trailingPE"),
        "PER estimé": donnees.get("forwardPE"),
        "Rendement du dividende": donnees.get("dividendYield"),
        "Plus haut 52 sem.": donnees.get("fiftyTwoWeekHigh"),
        "Plus bas 52 sem.": donnees.get("fiftyTwoWeekLow"),
        "Volume moyen": donnees.get("averageVolume"),
        "Employés": donnees.get("fullTimeEmployees"),
        "Description": donnees.get("longBusinessSummary"),
        "Site": donnees.get("website"),
    }
    return {k: v for k, v in garde.items() if v not in (None, "", 0)}


@st.cache_data(ttl=1800, show_spinner=False)
def depeches(ticker, maxi=10):
    """Les dernières actualités liées à l'actif : titre, source, date, lien."""
    try:
        import yfinance as yf
    except ImportError:
        return [], "Le module yfinance n'est pas installé."
    try:
        brutes = yf.Ticker(ticker).news or []
    except Exception as err:
        return [], f"Actualités indisponibles : {str(err)[:110]}"

    sortie = []
    for element in brutes[:maxi]:
        if not isinstance(element, dict):
            continue
        # Deux formats coexistent selon la version de yfinance.
        contenu = element.get("content") if isinstance(element.get("content"), dict) else element
        titre_ = contenu.get("title") or element.get("title")
        if not titre_:
            continue
        fournisseur = contenu.get("provider")
        source = fournisseur.get("displayName") if isinstance(fournisseur, dict) \
            else contenu.get("publisher")
        adresse = contenu.get("canonicalUrl")
        lien = element.get("link") or (adresse.get("url") if isinstance(adresse, dict) else "")
        moment = element.get("providerPublishTime") or contenu.get("pubDate")
        quand = ""
        if isinstance(moment, (int, float)):
            try:
                quand = datetime.fromtimestamp(float(moment)).strftime("%d/%m %H:%M")
            except (ValueError, OSError):
                quand = ""
        elif isinstance(moment, str):
            quand = moment[:16].replace("T", " ")
        sortie.append({"titre": titre_, "source": source or "—",
                       "lien": lien or "", "quand": quand})
    if not sortie:
        return [], "Aucune dépêche pour cet actif."
    return sortie, None

# ==========================================================
# 5. GRAPHIQUES
# ==========================================================
def _plotly():
    try:
        import plotly.graph_objects as go
        return go
    except Exception:
        return None


def _mise_en_page(fig, hauteur=360, titre_y=""):
    fig.update_layout(
        margin=dict(l=8, r=8, t=26, b=8), height=hauteur, template="plotly_white",
        hovermode="x unified", xaxis_title="", yaxis_title=titre_y,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0, font=dict(size=11)),
        font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#6E4A5B"),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


_LARGEUR_MODERNE = None


def afficher_figure(fig):
    """`use_container_width` disparaît des versions récentes de Streamlit,
    et `width='stretch'` n'existe pas dans les anciennes : on regarde une
    fois pour toutes ce que la version installée accepte."""
    global _LARGEUR_MODERNE
    if _LARGEUR_MODERNE is None:
        try:
            import inspect
            _LARGEUR_MODERNE = "use_container_width" not in \
                inspect.signature(st.plotly_chart).parameters
        except Exception:
            _LARGEUR_MODERNE = False
    if _LARGEUR_MODERNE:
        st.plotly_chart(fig, width="stretch")
    else:
        st.plotly_chart(fig, use_container_width=True)


def courbe(df, titre_y="", hauteur=360):
    go = _plotly()
    if go is None:
        st.line_chart(df)
        return
    try:
        fig = go.Figure()
        for i, colonne in enumerate(df.columns):
            fig.add_trace(go.Scatter(
                x=df.index, y=df[colonne], name=str(colonne), mode="lines",
                line=dict(width=2.6, color=PALETTE[i % len(PALETTE)]),
            ))
        afficher_figure(_mise_en_page(fig, hauteur, titre_y))
    except Exception:
        st.line_chart(df)


def graphique_complet(nom, df, options):
    """Chandeliers, moyennes, Bollinger, volumes, RSI et MACD empilés.

    Chaque bloc est facultatif : sur téléphone, on n'affiche que l'utile.
    """
    go = _plotly()
    cloture = df["Close"].dropna()
    if go is None:
        courbe(pd.DataFrame({nom: cloture}), "Prix", hauteur=380)
        return
    try:
        from plotly.subplots import make_subplots

        avec_volume = options.get("volume") and "Volume" in df.columns \
            and float(df["Volume"].fillna(0).sum()) > 0
        avec_rsi = options.get("rsi") and len(cloture) >= 20
        avec_macd = options.get("macd") and len(cloture) >= 35

        blocs = ["prix"] + (["volume"] if avec_volume else []) \
            + (["rsi"] if avec_rsi else []) + (["macd"] if avec_macd else [])
        poids = [1.0] + [0.34] * (len(blocs) - 1)
        total = sum(poids)
        fig = make_subplots(rows=len(blocs), cols=1, shared_xaxes=True,
                            row_heights=[p / total for p in poids], vertical_spacing=0.04)

        if options.get("chandeliers") and {"Open", "High", "Low", "Close"}.issubset(df.columns):
            fig.add_trace(go.Candlestick(
                x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                name="Cours", increasing_line_color="#15803d",
                decreasing_line_color="#b91c1c", showlegend=False), row=1, col=1)
        else:
            fig.add_trace(go.Scatter(x=cloture.index, y=cloture, name="Cours",
                                     line=dict(color="#C2185B", width=2.4)), row=1, col=1)

        if options.get("moyennes"):
            for n, couleur, trait in ((20, "#C2185B", "solid"), (50, "#6D3BAF", "dot"),
                                      (200, "#0E7490", "dash")):
                if len(cloture) >= n:
                    fig.add_trace(go.Scatter(
                        x=cloture.index, y=moyenne_mobile(cloture, n), name=f"Moyenne {n}",
                        line=dict(color=couleur, width=1.9, dash=trait)), row=1, col=1)

        if options.get("bollinger") and len(cloture) >= 20:
            haut, milieu, bas = bollinger(cloture)
            fig.add_trace(go.Scatter(x=cloture.index, y=haut, name="Bollinger haut",
                                     line=dict(color="#D9A8BE", width=1.2)), row=1, col=1)
            fig.add_trace(go.Scatter(x=cloture.index, y=bas, name="Bollinger bas",
                                     line=dict(color="#D9A8BE", width=1.2),
                                     fill="tonexty", fillcolor="rgba(217,168,190,.16)"),
                          row=1, col=1)

        rang = 2
        if avec_volume:
            fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                                 marker_color="#D9A8BE", showlegend=False), row=rang, col=1)
            fig.update_yaxes(title_text="Volume", row=rang, col=1)
            rang += 1
        if avec_rsi:
            fig.add_trace(go.Scatter(x=cloture.index, y=rsi(cloture), name="RSI",
                                     line=dict(color="#6D3BAF", width=1.9),
                                     showlegend=False), row=rang, col=1)
            for seuil, couleur in ((70, "#B3261E"), (30, "#17683D")):
                fig.add_hline(y=seuil, line=dict(color=couleur, width=1, dash="dot"),
                              row=rang, col=1)
            fig.update_yaxes(title_text="RSI", range=[0, 100], row=rang, col=1)
            rang += 1
        if avec_macd:
            ligne, signal, histogramme = macd(cloture)
            couleurs = ["#17683D" if v >= 0 else "#B3261E" for v in histogramme.fillna(0)]
            fig.add_trace(go.Bar(x=cloture.index, y=histogramme, name="Écart",
                                 marker_color=couleurs, showlegend=False), row=rang, col=1)
            fig.add_trace(go.Scatter(x=cloture.index, y=ligne, name="MACD",
                                     line=dict(color="#C2185B", width=1.7),
                                     showlegend=False), row=rang, col=1)
            fig.add_trace(go.Scatter(x=cloture.index, y=signal, name="Signal",
                                     line=dict(color="#0E7490", width=1.5, dash="dot"),
                                     showlegend=False), row=rang, col=1)
            fig.update_yaxes(title_text="MACD", row=rang, col=1)

        fig.update_xaxes(rangeslider_visible=False)
        hauteur = 380 + 120 * (len(blocs) - 1)
        afficher_figure(_mise_en_page(fig, hauteur, "Prix"))
    except Exception:
        courbe(pd.DataFrame({nom: cloture}), "Prix", hauteur=380)

# ==========================================================
# 6. RÉGLAGES, NOTES & ALERTES
# ==========================================================
def _config_par_defaut():
    return {"watchlist": ["Bitcoin", "Or", "S&P 500", "Nvidia"]}


def config():
    """Réglages du labo, lus une seule fois par session.

    L'index de la ligne « Config » est mémorisé pour que les enregistrements
    suivants soient des mises à jour, jamais de nouvelles lignes.
    """
    if "lab_cfg" in st.session_state:
        return st.session_state["lab_cfg"]

    base = _config_par_defaut()
    try:
        for index, ligne in rows("IA_Lab"):
            _, sujet, contenu, type_ = pad(ligne, 4)
            if type_ == TYPE_CONFIG and sujet == CFG_SUJET:
                try:
                    charge = json.loads(contenu)
                    if isinstance(charge, dict):
                        base.update(charge)
                except Exception:
                    pass
                st.session_state["lab_cfg_idx"] = index
                break
    except Exception:
        pass  # feuille absente ou illisible : on démarre sur les valeurs par défaut

    base["watchlist"] = [n for n in base.get("watchlist", []) if n in UNIVERS][:8]
    st.session_state["lab_cfg"] = base
    return base


def sauver_config(cfg):
    """Écrit les réglages sans relire la feuille dans la foulée.

    Relire juste après une écriture faisait diverger la configuration, ce qui
    relançait une écriture à chaque rerun : l'app bouclait sur l'API Google et
    ne finissait jamais de s'afficher.
    """
    st.session_state["lab_cfg"] = cfg
    charge = json.dumps(cfg, ensure_ascii=False)
    index = st.session_state.get("lab_cfg_idx")
    try:
        if index:
            set_cell("IA_Lab", index, 3, charge)
            return
        add_row("IA_Lab", [str(date.today()), CFG_SUJET, charge, TYPE_CONFIG])
        for i, ligne in rows("IA_Lab"):          # on retient l'index tout de suite
            _, sujet, _, type_ = pad(ligne, 4)
            if type_ == TYPE_CONFIG and sujet == CFG_SUJET:
                st.session_state["lab_cfg_idx"] = i
                break
    except Exception as err:
        st.warning(f"Réglages non enregistrés : {str(err)[:120]}")


def notes_utilisateur():
    """Toutes les notes, sauf la configuration et les alertes."""
    sortie = []
    try:
        lignes = rows("IA_Lab")
    except Exception:
        return sortie
    for index, ligne in lignes:
        d, sujet, contenu, type_ = pad(ligne, 4)
        if type_ in (TYPE_CONFIG, TYPE_ALERTE):
            continue
        sortie.append({"idx": index, "date": d, "sujet": sujet,
                       "contenu": contenu, "type": type_ or TYPES_NOTE[0]})
    return sortie


def alertes():
    """Les seuils enregistrés : [{idx, actif, sens, seuil, note, date}]."""
    sortie = []
    try:
        lignes = rows("IA_Lab")
    except Exception:
        return sortie
    for index, ligne in lignes:
        d, _, contenu, type_ = pad(ligne, 4)
        if type_ != TYPE_ALERTE:
            continue
        try:
            charge = json.loads(contenu)
        except Exception:
            continue
        if charge.get("actif") in UNIVERS and charge.get("seuil") is not None:
            charge.update({"idx": index, "date": d})
            sortie.append(charge)
    return sortie


def ajouter_alerte(actif, sens, seuil, commentaire=""):
    charge = json.dumps({"actif": actif, "sens": sens, "seuil": float(seuil),
                         "note": commentaire.strip()}, ensure_ascii=False)
    add_row("IA_Lab", [str(date.today()), f"Alerte — {actif}", charge, TYPE_ALERTE])


def etat_alerte(alerte, prix):
    """(déclenchée ?, écart au seuil en %)"""
    if _nan(prix):
        return False, float("nan")
    seuil = float(alerte["seuil"])
    ecart = (float(prix) / seuil - 1) * 100 if seuil else float("nan")
    declenchee = float(prix) >= seuil if alerte.get("sens") == "Au-dessus de" \
        else float(prix) <= seuil
    return declenchee, ecart


@st.cache_data(ttl=300, show_spinner=False)
def _derniers_cours(tickers):
    paquets, err = _telecharger(tuple(tickers), "5d", "1h")
    prix = {}
    for ticker, df in paquets.items():
        if "Close" in df:
            cloture = df["Close"].dropna()
            if len(cloture):
                prix[ticker] = float(cloture.iloc[-1])
    return prix, err


def derniers_cours(noms):
    """{nom: dernier cours connu} — utilisé par les alertes."""
    tickers = tuple(sorted({UNIVERS[n][0] for n in noms if n in UNIVERS}))
    if not tickers:
        return {}, None
    try:
        prix, err = _derniers_cours(tickers)
    except Exception as erreur:
        return {}, str(erreur)[:110]
    return {NOM_PAR_TICKER.get(t, t): v for t, v in prix.items()}, err

# ==========================================================
# 7. LECTURES AUTOMATIQUES & COMMENTAIRE RÉDIGÉ
# ==========================================================
def lecture_actif(nom, p, perfs=None):
    """Des phrases simples, déduites des chiffres. Aucune recommandation."""
    phrases = []
    unite = devise(nom)

    if not _nan(p.get("var")):
        sens = "progresse" if p["var"] > 0 else ("recule" if p["var"] < 0 else "fait du surplace")
        phrases.append(f"Sur la période affichée, <b>{nom}</b> {sens} de "
                       f"{fpct(p['var'])}, à {fprix(p['dernier'], unite)}.")

    if not _nan(p.get("ecart20")) and not _nan(p.get("ecart50")):
        if p["ecart20"] > 0 and p["ecart50"] > 0:
            phrases.append(f"Le cours est au-dessus de ses moyennes 20 et 50 séances "
                           f"(+{fnum(abs(p['ecart20']), 1)} % et +{fnum(abs(p['ecart50']), 1)} %) : "
                           "la tendance récente est orientée à la hausse.")
        elif p["ecart20"] < 0 and p["ecart50"] < 0:
            phrases.append(f"Le cours est sous ses moyennes 20 et 50 séances "
                           f"({fpct(p['ecart20'], 1)} et {fpct(p['ecart50'], 1)}) : "
                           "la tendance récente est orientée à la baisse.")
        else:
            phrases.append("Le cours est d'un côté de sa moyenne 20 et de l'autre de sa "
                           "moyenne 50 : la tendance hésite.")

    if not _nan(p.get("ecart200")):
        cote = "au-dessus" if p["ecart200"] > 0 else "en dessous"
        phrases.append(f"Il évolue {cote} de sa moyenne 200 séances "
                       f"({fpct(p['ecart200'], 1)}), le repère de fond.")

    r = p.get("rsi")
    if not _nan(r):
        if r >= 70:
            etat = "très tendu à la hausse — ce genre de niveau précède souvent une pause"
        elif r >= 55:
            etat = "du côté des acheteurs, sans excès"
        elif r > 45:
            etat = "à l'équilibre"
        elif r > 30:
            etat = "du côté des vendeurs"
        else:
            etat = "très tendu à la baisse — les mouvements de ce type finissent souvent " \
                   "par un rebond technique"
        phrases.append(f"Le RSI est à {fnum(r, 0)} : {etat}.")

    if not _nan(p.get("macd")) and not _nan(p.get("macd_signal")):
        if p["macd"] > p["macd_signal"]:
            phrases.append("Le MACD est repassé au-dessus de sa ligne de signal : "
                           "l'élan de court terme est favorable.")
        else:
            phrases.append("Le MACD reste sous sa ligne de signal : "
                           "l'élan de court terme est défavorable.")

    if not _nan(p.get("position")):
        if p["position"] >= 85:
            phrases.append(f"Il se tient tout en haut du couloir de la période "
                           f"({fnum(p['position'], 0)} %), près de son plus haut à "
                           f"{fprix(p['haut'], unite)}.")
        elif p["position"] <= 15:
            phrases.append(f"Il se tient tout en bas du couloir de la période "
                           f"({fnum(p['position'], 0)} %), près de son plus bas à "
                           f"{fprix(p['bas'], unite)}.")
        else:
            phrases.append(f"Il se situe à {fnum(p['position'], 0)} % du couloir "
                           f"{fprix(p['bas'], unite)} – {fprix(p['haut'], unite)}.")

    if not _nan(p.get("vol")):
        if p["vol"] >= 60:
            calme = "très agité"
        elif p["vol"] >= 30:
            calme = "nerveux"
        elif p["vol"] >= 15:
            calme = "dans une agitation ordinaire"
        else:
            calme = "calme"
        phrases.append(f"L'actif est {calme} : {fpct(p['vol'], 0, signe=False)} d'agitation "
                       "annualisée.")

    if not _nan(p.get("repli")) and p["repli"] < -3:
        phrases.append(f"La pire chute depuis un sommet, sur la période, atteint "
                       f"{fpct(p['repli'], 1)}.")

    if not _nan(p.get("beta")) and nom != REFERENCE:
        b = p["beta"]
        if b > 1.15:
            phrases.append(f"Il bouge plus fort que le {REFERENCE} (sensibilité {fnum(b, 2)}).")
        elif b < 0:
            phrases.append(f"Il a plutôt tendance à aller à l'inverse du {REFERENCE} "
                           f"(sensibilité {fnum(b, 2)}).")
        elif b < 0.6:
            phrases.append(f"Il bouge moins fort que le {REFERENCE} (sensibilité {fnum(b, 2)}).")

    if perfs:
        bons = [f"{lib} {fpct(v, 1)}" for lib, v in perfs.items() if not _nan(v)]
        if bons:
            phrases.append("Performances : " + " · ".join(bons) + ".")

    return phrases


def lecture_marche(profils, perfs_par_actif, correlations=None):
    """Ce qu'on peut dire de l'ensemble de la sélection."""
    phrases = []
    valides = {n: p for n, p in profils.items() if p and not _nan(p.get("var"))}
    if not valides:
        return phrases

    classement = sorted(valides.items(), key=lambda c: -c[1]["var"])
    meilleur, pire = classement[0], classement[-1]
    phrases.append(f"En tête sur la période : <b>{meilleur[0]}</b> "
                   f"({fpct(meilleur[1]['var'])}). En queue : <b>{pire[0]}</b> "
                   f"({fpct(pire[1]['var'])}).")

    hausses = sum(1 for _, p in valides.items() if p["var"] > 0)
    total = len(valides)
    if hausses == total:
        phrases.append("Toute la sélection monte : le mouvement est large.")
    elif hausses == 0:
        phrases.append("Toute la sélection baisse : le mouvement est large.")
    else:
        phrases.append(f"{hausses} actif(s) sur {total} en hausse : le marché est partagé.")

    agitees = [n for n, p in valides.items() if not _nan(p.get("vol")) and p["vol"] >= 45]
    if agitees:
        phrases.append("Le plus remuant du lot : " + ", ".join(agitees[:3]) + ".")

    tendus = [f"{n} (RSI {fnum(p['rsi'], 0)})" for n, p in valides.items()
              if not _nan(p.get("rsi")) and (p["rsi"] >= 70 or p["rsi"] <= 30)]
    if tendus:
        phrases.append("Situation tendue sur : " + ", ".join(tendus[:3]) + ".")

    if correlations is not None and len(correlations) >= 2:
        try:
            paires = []
            noms = list(correlations.columns)
            for i, a in enumerate(noms):
                for b in noms[i + 1:]:
                    valeur = correlations.loc[a, b]
                    if not _nan(valeur):
                        paires.append((abs(float(valeur)), float(valeur), a, b))
            if paires:
                paires.sort(reverse=True)
                _, valeur, a, b = paires[0]
                lien = "bougent presque ensemble" if valeur > 0 else "bougent en sens inverse"
                phrases.append(f"{a} et {b} {lien} sur la période "
                               f"(corrélation {fnum(valeur, 2)}).")
        except Exception:
            pass

    if perfs_par_actif:
        annee = {n: v.get("YTD") for n, v in perfs_par_actif.items() if not _nan(v.get("YTD"))}
        if annee:
            gagnant = max(annee, key=annee.get)
            phrases.append(f"Depuis le 1er janvier, le meilleur de la sélection est "
                           f"<b>{gagnant}</b> ({fpct(annee[gagnant], 1)}).")
    return phrases


def cle_ia():
    """Clé d'API facultative, lue dans les secrets Streamlit."""
    for section, champ in (("anthropic", "api_key"), ("ia", "api_key")):
        try:
            bloc = st.secrets[section]
            valeur = bloc.get(champ) or bloc.get("key")
            if valeur:
                return str(valeur)
        except Exception:
            continue
    return None


def modele_ia():
    try:
        return str(st.secrets["anthropic"].get("modele") or MODELE_IA_DEFAUT)
    except Exception:
        return MODELE_IA_DEFAUT


def commentaire_redige(contexte, question=""):
    """Un paragraphe écrit à partir des chiffres déjà calculés.

    Les chiffres sont envoyés tels quels : le modèle rédige, il n'invente
    ni cours ni prévision. Sans clé dans les secrets, la fonction se tait.
    """
    api = cle_ia()
    if not api:
        return None, "Aucune clé d'API dans les secrets — le commentaire rédigé est désactivé."
    try:
        import requests
    except ImportError:
        return None, "Le module requests n'est pas disponible."

    consigne = (
        "Tu commentes des chiffres de marché pour deux personnes qui apprennent. "
        "Écris en français, 120 mots maximum, ton clair et posé. "
        "Décris uniquement ce que montrent les chiffres fournis. "
        "N'invente aucune donnée, ne donne aucune prévision, "
        "aucun conseil d'achat ou de vente, aucun objectif de prix. "
        "Termine par une phrase rappelant qu'il s'agit d'une lecture de cours passés."
    )
    contenu = f"Chiffres relevés :\n{contexte}"
    if question.strip():
        contenu += f"\n\nCe que nous aimerions comprendre : {question.strip()}"

    try:
        reponse = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={"x-api-key": api, "anthropic-version": "2023-06-01",
                     "content-type": "application/json"},
            json={"model": modele_ia(), "max_tokens": 600, "system": consigne,
                  "messages": [{"role": "user", "content": contenu}]},
            timeout=45,
        )
        if reponse.status_code != 200:
            return None, f"Service indisponible ({reponse.status_code})."
        blocs = reponse.json().get("content") or []
        texte = "\n".join(b.get("text", "") for b in blocs if b.get("type") == "text").strip()
        return (texte or None), (None if texte else "Réponse vide.")
    except Exception as err:
        return None, f"Commentaire impossible : {str(err)[:110]}"


def bloc_commentaire_ia(cle_widget, contexte):
    """Le bouton facultatif, affiché seulement si une clé est configurée."""
    if not cle_ia():
        return
    sous_titre("Commentaire rédigé")
    with conteneur(f"labrow-ia-{cle_widget}"):
        question = st.text_input("Une question sur ces chiffres (facultatif)",
                                 key=f"lab_ia_q_{cle_widget}",
                                 placeholder="Ex : pourquoi l'or et le Nasdaq divergent ?")
        if st.button("✍️ Rédiger un commentaire", key=f"lab_ia_go_{cle_widget}"):
            with st.spinner("Rédaction…"):
                texte, err = commentaire_redige(contexte, question)
            st.session_state[f"lab_ia_txt_{cle_widget}"] = texte or ""
            st.session_state[f"lab_ia_err_{cle_widget}"] = err or ""
    texte = st.session_state.get(f"lab_ia_txt_{cle_widget}")
    err = st.session_state.get(f"lab_ia_err_{cle_widget}")
    if texte:
        note(texte.replace("\n", "<br>"))
        if st.button("📚 Garder dans mes notes", key=f"lab_ia_save_{cle_widget}"):
            add_row("IA_Lab", [str(date.today()), "Commentaire du labo", texte, "Note"])
            st.toast("Commentaire enregistré", icon="✅")
    elif err:
        note(err, "calme")

# ==========================================================
# 8. ONGLETS
# ==========================================================
def _selection(cle_widget, cfg, maxi=8):
    """Sélecteur d'actifs qui n'écrit la configuration qu'à un vrai changement."""
    _defaut(cle_widget, [n for n in cfg["watchlist"] if n in UNIVERS][:maxi] or ["Bitcoin", "Or"])

    with st.expander("Sélections toutes prêtes"):
        colonnes = st.columns(3)
        for i, (nom_bouquet, contenu) in enumerate(BOUQUETS.items()):
            with colonnes[i % 3]:
                if st.button(nom_bouquet, key=f"lab_bq_{cle_widget}_{i}"):
                    st.session_state[cle_widget] = contenu[:maxi]
                    st.rerun()

    choix = st.multiselect("Actifs suivis", list(UNIVERS), max_selections=maxi, key=cle_widget)

    deja = st.session_state.get("lab_watch_saved")
    if deja is None:
        deja = tuple(cfg["watchlist"])
    if choix and tuple(choix) != tuple(deja):
        st.session_state["lab_watch_saved"] = tuple(choix)
        cfg["watchlist"] = list(choix)
        sauver_config(cfg)
    return choix


def _bouton_chargement(cle_bouton):
    """Le premier chargement est volontaire : sur téléphone, télécharger
    plusieurs séries avant le premier affichage laissait un spinner sans fin."""
    if st.session_state.get("lab_live"):
        return True
    note("Les cours ne sont pas encore chargés — appuyez pour interroger les marchés.")
    if st.button("📡 Charger les cours", type="primary", key=cle_bouton):
        st.session_state["lab_live"] = True
        st.rerun()
    return False


def _bandeau_alertes(prix_connus):
    """Les seuils franchis, montrés en haut de page."""
    mes_alertes = alertes()
    if not mes_alertes:
        return
    manquants = [a["actif"] for a in mes_alertes if a["actif"] not in prix_connus]
    if manquants:
        complement, _ = derniers_cours(sorted(set(manquants)))
        prix_connus = {**complement, **prix_connus}
    touchees = []
    for alerte in mes_alertes:
        prix = prix_connus.get(alerte["actif"])
        declenchee, _ = etat_alerte(alerte, prix)
        if declenchee:
            touchees.append(f"{alerte['actif']} {alerte['sens'].lower()} "
                            f"{fprix(alerte['seuil'], devise(alerte['actif']))} "
                            f"— maintenant {fprix(prix, devise(alerte['actif']))}")
    if touchees:
        note("🔔 <b>Seuil atteint</b><br>" + "<br>".join(touchees), "warn")


def onglet_marches(cfg):
    with conteneur("labrow-sel"):
        choix = _selection("lab_cmp", cfg)
        colonne_a, colonne_b = st.columns(2)
        with colonne_a:
            periode = pills("lab_periode", list(PERIODES), defaut="5J", cols=4)
        with colonne_b:
            base = pills("lab_base", ["Base 100", "Prix réels"], defaut="Base 100", cols=2)

    if not choix:
        note("Sélectionnez au moins un actif pour afficher les cours.")
        return
    if not _bouton_chargement("lab_go"):
        return

    with st.spinner("Lecture des marchés…"):
        donnees, barres_an, err = marche(choix, periode)
    if err:
        note(f"⚠️ {err}", "warn")
        if st.button("Réessayer", key="lab_retry"):
            st.cache_data.clear()
            st.rerun()
        return

    with st.spinner("Historique long…"):
        longues, _ = historique(choix)
    reference = longues.get(REFERENCE)

    valides = {}
    for nom in choix:
        p = profil(donnees.get(nom), barres_an, reference)
        if p:
            longue = longues.get(nom)
            p["perfs"] = performances(longue) if longue is not None else {}
            p["repli_1a"] = repli_max(longue.tail(252)) if longue is not None else float("nan")
            p["vol_30j"] = volatilite(longue.tail(30), 252) if longue is not None else float("nan")
            if longue is not None and len(longue) > 30:
                p["beta"] = beta(longue, reference) if reference is not None else float("nan")
                haut52 = float(longue.tail(252).max())
                p["dist_haut52"] = (p["dernier"] / haut52 - 1) * 100 if haut52 else float("nan")
            else:
                p["dist_haut52"] = float("nan")
            valides[nom] = p
    if not valides:
        note("Aucune donnée exploitable sur cette période.", "warn")
        return

    _bandeau_alertes({n: p["dernier"] for n, p in valides.items()})

    kpis([{"label": nom, "valeur": fprix(p["dernier"], devise(nom)),
           "delta": fpct(p["var"]), "delta_ton": ton(p["var"])}
          for nom, p in valides.items()], largeur=160)

    sous_titre("Les cours sur la période")
    table([("Actif", "txt"), ("Dernier", "num"), ("Variation", "num"), ("Plus haut", "num"),
           ("Plus bas", "num"), ("Moyenne", "num"), ("Amplitude", "num")],
          [[nom, fprix(p["dernier"], devise(nom)), cell_pct(p["var"]),
            fprix(p["haut"], devise(nom)), fprix(p["bas"], devise(nom)),
            fprix(p["moyenne"], devise(nom)),
            fpct((p["haut"] / p["bas"] - 1) * 100 if p["bas"] else float("nan"), 1, signe=False)]
           for nom, p in valides.items()])

    sous_titre("Performances par horizon")
    table([("Actif", "txt")] + [(lib, "num") for lib, _ in HORIZONS],
          [[nom] + [cell_pct(p["perfs"].get(lib), 1) for lib, _ in HORIZONS]
           for nom, p in valides.items()])
    st.caption("Calculé sur les clôtures quotidiennes des deux dernières années. "
               "Le tableau défile horizontalement.")

    sous_titre("Ce que ça coûte en nerfs")
    table([("Actif", "txt"), ("Agitation 30 j", "num"), ("Agitation période", "num"),
           ("Pire chute (1 an)", "num"), ("Sous le plus haut 52 s.", "num"),
           (f"Sensibilité {REFERENCE}", "num"), ("RSI", "num")],
          [[nom, fpct(p.get("vol_30j"), 0, signe=False), fpct(p["vol"], 0, signe=False),
            cell_pct(p.get("repli_1a"), 1), cell_pct(p.get("dist_haut52"), 1),
            fnum(p.get("beta"), 2), fnum(p.get("rsi"), 0)]
           for nom, p in valides.items()])
    st.caption("Agitation = amplitude typique des variations, ramenée à l'année. "
               "Sensibilité = 1,00 signifie « bouge comme le " + REFERENCE + " ».")

    sous_titre("Évolution comparée")
    series = pd.DataFrame({nom: p["serie"] for nom, p in valides.items()})
    if base == "Base 100":
        series = series.apply(lambda c: c / c.dropna().iloc[0] * 100 if not c.dropna().empty else c)
        courbe(series, "Base 100 au départ de la période")
        st.caption("Chaque actif part de 100 : les courbes se comparent malgré des prix "
                   "très différents.")
    else:
        courbe(series, "Prix, dans la devise de cotation")

    correlations = None
    if len(valides) >= 2 and len(series.dropna()) > 5:
        sous_titre("Est-ce que ça bouge ensemble ?")
        correlations = series.pct_change(fill_method=None).corr()
        colonnes = [("", "txt")] + [(nom, "num") for nom in correlations.columns]
        lignes = []
        for nom in correlations.index:
            cellules = [f"<b>{nom}</b>"]
            for autre in correlations.columns:
                valeur = correlations.loc[nom, autre]
                classe = "up" if valeur > 0.5 else ("down" if valeur < -0.2 else "flat")
                cellules.append(f"<span class='{classe}'>{fnum(valeur, 2)}</span>")
            lignes.append(cellules)
        table(colonnes, lignes)
        st.caption("1,00 = les deux actifs montent et descendent ensemble · 0,00 = aucun lien · "
                   "négatif = quand l'un monte, l'autre baisse.")

    sous_titre("Lecture de la séance")
    puces(lecture_marche(valides, {n: p["perfs"] for n, p in valides.items()}, correlations))

    resume = " · ".join(f"{nom} {fprix(p['dernier'], devise(nom))} ({fpct(p['var'])}), "
                        f"RSI {fnum(p.get('rsi'), 0)}, agitation "
                        f"{fpct(p['vol'], 0, signe=False)}"
                        for nom, p in valides.items())
    bloc_commentaire_ia("marche", f"Période {periode}. {resume}")

    note("Ces chiffres décrivent des cours passés. Ils ne prédisent rien et ne constituent "
         "pas un conseil en investissement.", "calme")

    sous_titre("Garder une trace")
    with conteneur("labrow-note-marche"):
        commentaire = st.text_area("Ce que vous retenez de cette séance",
                                   key="lab_note_marche", height=90,
                                   placeholder="Ex : l'or tient pendant que le Nasdaq recule…")
        if st.button("Enregistrer dans mes notes", type="primary", key="lab_save_marche"):
            if commentaire.strip():
                court = " · ".join(f"{nom} {fpct(p['var'])}" for nom, p in valides.items())
                add_row("IA_Lab", [str(date.today()), f"Marchés ({periode})",
                                   f"{court}\n\n{commentaire.strip()}", "Suivi"])
                reset_after(lab_note_marche="")
                st.toast("Note enregistrée", icon="✅")
                st.rerun()
            else:
                st.warning("Écrivez d'abord ce que vous retenez.")


def onglet_analyse(cfg):
    with conteneur("labrow-ana"):
        colonne_a, colonne_b = st.columns([2, 1])
        with colonne_a:
            actif = st.selectbox("Actif étudié", list(UNIVERS), key="lab_ana_actif")
        with colonne_b:
            periode = pills("lab_ana_periode", list(PERIODES), defaut="1M", cols=4)
        options = {
            "chandeliers": st.checkbox("Chandeliers", value=True, key="lab_opt_chand"),
            "moyennes": st.checkbox("Moyennes mobiles", value=True, key="lab_opt_mm"),
            "bollinger": st.checkbox("Bandes de Bollinger", value=False, key="lab_opt_boll"),
            "volume": st.checkbox("Volumes", value=True, key="lab_opt_vol"),
            "rsi": st.checkbox("RSI", value=True, key="lab_opt_rsi"),
            "macd": st.checkbox("MACD", value=False, key="lab_opt_macd"),
        }

    if not _bouton_chargement("lab_go_ana"):
        return

    with st.spinner("Lecture des marchés…"):
        donnees, barres_an, err = marche([actif], periode)
    if err:
        note(f"⚠️ {err}", "warn")
        return
    df = donnees.get(actif)

    with st.spinner("Historique long…"):
        longues, _ = historique([actif])
    longue = longues.get(actif)
    reference = longues.get(REFERENCE)

    p = profil(df, barres_an, reference)
    if not p:
        note("Pas assez de données pour cet actif sur cette période.", "warn")
        return
    perfs = performances(longue) if longue is not None else {}
    if longue is not None and len(longue) > 30:
        p["beta"] = beta(longue, reference) if reference is not None else float("nan")

    unite = devise(actif)
    kpis([
        {"label": "Dernier cours", "valeur": fprix(p["dernier"], unite),
         "delta": fpct(p["var"]), "delta_ton": ton(p["var"])},
        {"label": "Plus haut", "valeur": fprix(p["haut"], unite), "aide": "sommet de la période"},
        {"label": "Plus bas", "valeur": fprix(p["bas"], unite), "aide": "creux de la période"},
        {"label": "RSI (14)", "valeur": fnum(p.get("rsi"), 0),
         "aide": "70 = tendu à la hausse · 30 = tendu à la baisse"},
        {"label": "Écart moyenne 20", "valeur": fpct(p["ecart20"], 2),
         "delta_ton": ton(p["ecart20"])},
        {"label": "Écart moyenne 200", "valeur": fpct(p["ecart200"], 2),
         "delta_ton": ton(p["ecart200"])},
        {"label": "Agitation annualisée", "valeur": fpct(p["vol"], 1, signe=False),
         "aide": "amplitude typique des variations"},
        {"label": f"Sensibilité {REFERENCE}", "valeur": fnum(p.get("beta"), 2),
         "aide": "1,00 = bouge comme l'indice"},
    ])

    jauge(p.get("position"), f"plus bas {fprix(p['bas'], unite)}",
          f"plus haut {fprix(p['haut'], unite)}")

    graphique_complet(actif, df, options)

    if perfs:
        sous_titre("Performances")
        table([(lib, "num") for lib, _ in HORIZONS],
              [[cell_pct(perfs.get(lib), 1) for lib, _ in HORIZONS]])

    sous_titre("Repères de la période")
    reperes = [
        ("Plus haut", p["haut"]),
        ("Moyenne mobile 20", p["mm20"]),
        ("Moyenne mobile 50", p["mm50"]),
        ("Moyenne mobile 200", p["mm200"]),
        ("Moyenne des cours", p["moyenne"]),
        ("Premier cours de la période", p["premier"]),
        ("Plus bas", p["bas"]),
    ]
    dernier = p["dernier"]
    table([("Repère", "txt"), ("Cours", "num"), ("Écart au dernier", "num")],
          [[libelle, fprix(valeur, unite),
            cell_pct((dernier / valeur - 1) * 100) if not _nan(valeur) and valeur else "—"]
           for libelle, valeur in reperes])

    supports, resistances = niveaux(longue if longue is not None else p["serie"])
    if supports or resistances:
        sous_titre("Paliers déjà testés")
        lignes = [["Résistance", fprix(v, unite), cell_pct((v / dernier - 1) * 100, 1)]
                  for v in reversed(resistances)]
        lignes += [["Support", fprix(v, unite), cell_pct((v / dernier - 1) * 100, 1)]
                   for v in supports]
        table([("Type", "txt"), ("Niveau", "num"), ("Distance", "num")], lignes)
        st.caption("Sommets et creux repérés sur un an de clôtures. Ce sont des constats, "
                   "pas des barrières.")

    identite = fiche(UNIVERS[actif][0])
    if identite:
        sous_titre("Fiche d'identité")
        lignes = []
        for libelle in ("Secteur", "Industrie", "Pays", "Employés"):
            if identite.get(libelle):
                lignes.append([libelle, str(identite[libelle])])
        if identite.get("Capitalisation"):
            lignes.append(["Capitalisation", fgros(identite["Capitalisation"]) + FINE + unite])
        for libelle in ("PER", "PER estimé", "Bénéfice par action"):
            if identite.get(libelle):
                lignes.append([libelle, fnum(identite[libelle], 2)])
        if identite.get("Rendement du dividende"):
            valeur = float(identite["Rendement du dividende"])
            valeur = valeur * 100 if valeur < 1 else valeur   # selon la source, 0,021 ou 2,1
            lignes.append(["Rendement du dividende", fpct(valeur, 2, signe=False)])
        for libelle in ("Plus haut 52 sem.", "Plus bas 52 sem."):
            if identite.get(libelle):
                lignes.append([libelle, fprix(identite[libelle], unite)])
        if identite.get("Volume moyen"):
            lignes.append(["Volume moyen", fgros(identite["Volume moyen"])])
        table([("Repère", "txt"), ("Valeur", "num")], lignes)
        if identite.get("Description"):
            with st.expander("En quelques mots"):
                st.write(identite["Description"][:1200])

    sous_titre("Lecture automatique")
    puces(lecture_actif(actif, p, perfs))

    contexte = (f"{actif} sur {periode} : dernier {fprix(p['dernier'], unite)}, "
                f"variation {fpct(p['var'])}, RSI {fnum(p.get('rsi'), 0)}, "
                f"écart moyenne 20 {fpct(p['ecart20'])}, écart moyenne 200 "
                f"{fpct(p['ecart200'])}, agitation {fpct(p['vol'], 0, signe=False)}, "
                f"pire chute {fpct(p['repli'], 1)}, position dans le couloir "
                f"{fnum(p.get('position'), 0)} %. Performances : "
                + ", ".join(f"{lib} {fpct(v, 1)}" for lib, v in perfs.items() if not _nan(v)))
    bloc_commentaire_ia("analyse", contexte)

    note("Ces chiffres décrivent des cours passés. Ils ne prédisent rien et ne constituent "
         "pas un conseil en investissement.", "calme")

    sous_titre("Noter cette observation")
    with conteneur("labrow-note-ana"):
        obs = st.text_area(f"Ce que vous observez sur {actif}", key="lab_note_ana", height=90,
                           placeholder="Ex : le cours reste au-dessus de sa moyenne 20 depuis…")
        colonne_a, colonne_b = st.columns(2)
        with colonne_a:
            if st.button("Enregistrer dans mes notes", type="primary", key="lab_save_ana"):
                if obs.strip():
                    entete = (f"{actif} · {fprix(p['dernier'], unite)} ({fpct(p['var'])}) "
                              f"sur {periode}")
                    add_row("IA_Lab", [str(date.today()), f"Observation — {actif}",
                                       f"{entete}\n\n{obs.strip()}", "Suivi"])
                    reset_after(lab_note_ana="")
                    st.toast("Note enregistrée", icon="✅")
                    st.rerun()
                else:
                    st.warning("Écrivez d'abord votre observation.")
        with colonne_b:
            if st.button("🔔 Créer une alerte ici", key="lab_ana_alerte"):
                st.session_state["lab_al_actif"] = actif
                st.session_state["lab_tab"] = ONGLETS[3]
                st.rerun()


def onglet_actus(cfg):
    with conteneur("labrow-actu"):
        _defaut("lab_actu_actif", cfg["watchlist"][0] if cfg["watchlist"] else "Bitcoin")
        actif = st.selectbox("Actualités de", list(UNIVERS), key="lab_actu_actif")

    liste, err = depeches(UNIVERS[actif][0])
    if err:
        note(err, "calme")
    for i, article in enumerate(liste):
        lien = article["lien"]
        quand = f" · {article['quand']}" if article["quand"] else ""
        corps = (f"<div class='t'>{article['titre']}</div>"
                 f"<div class='s'>{article['source']}{quand}</div>")
        balise = (f"<a class='lab-actu' href='{lien}' target='_blank'>{corps}</a>"
                  if lien else f"<div class='lab-actu'>{corps}</div>")
        st.markdown(balise, unsafe_allow_html=True)
        if st.button("📚 Garder ce titre", key=f"lab_actu_save_{i}"):
            add_row("IA_Lab", [str(date.today()), f"Actu — {actif}",
                               f"{article['titre']}\n{article['source']}\n{lien}", "À retenir"])
            st.toast("Ajouté aux notes", icon="✅")

    if liste:
        st.caption("Les dépêches viennent du même fournisseur que les cours. "
                   "Les titres sont affichés tels quels, sans tri ni interprétation.")

    sous_titre("Un peu de contexte")
    if st.button("📡 Voir où en sont les grands indices", key="lab_actu_indices"):
        st.session_state["lab_live"] = True
        st.session_state["lab_cmp"] = BOUQUETS["Indices"]
        st.session_state["lab_tab"] = ONGLETS[0]
        st.rerun()


def onglet_alertes(cfg):
    mes_alertes = alertes()
    concernes = sorted({a["actif"] for a in mes_alertes} | set(cfg["watchlist"]))
    prix, err = derniers_cours(concernes) if concernes else ({}, None)
    if err:
        note(f"Cours indisponibles : {err}", "calme")

    kpis([
        {"label": "Alertes actives", "valeur": fnum(len(mes_alertes), 0)},
        {"label": "Seuils atteints", "valeur": fnum(
            sum(1 for a in mes_alertes if etat_alerte(a, prix.get(a["actif"]))[0]), 0)},
    ], largeur=170)

    if mes_alertes:
        sous_titre("Vos seuils")
        for alerte in mes_alertes:
            cours = prix.get(alerte["actif"])
            declenchee, ecart = etat_alerte(alerte, cours)
            unite = devise(alerte["actif"])
            with conteneur(f"labrow-al-{alerte['idx']}"):
                colonne_a, colonne_b = st.columns([3, 1])
                with colonne_a:
                    marque = "🔔" if declenchee else "⏳"
                    st.markdown(
                        f"**{marque} {alerte['actif']}** · {alerte['sens'].lower()} "
                        f"{fprix(alerte['seuil'], unite)}  \n"
                        f"Cours actuel {fprix(cours, unite)} · écart {fpct(ecart, 1)}"
                        + (f"  \n_{alerte.get('note')}_" if alerte.get("note") else ""))
                with colonne_b:
                    if st.button("🗑️", key=f"lab_al_del_{alerte['idx']}"):
                        delete_row("IA_Lab", alerte["idx"], libelle="Alerte supprimée")
                        st.rerun()
        st.caption("Les alertes sont vérifiées à chaque ouverture du labo, et rappelées "
                   "en haut de l'onglet Marchés. L'application n'envoie pas de notification.")
    else:
        vide("Aucune alerte. Créez-en une ci-dessous.")

    sous_titre("Nouvelle alerte")
    with conteneur("labrow-al-new"):
        _defaut("lab_al_actif", cfg["watchlist"][0] if cfg["watchlist"] else "Bitcoin")
        actif = st.selectbox("Actif", list(UNIVERS), key="lab_al_actif")
        sens = pills("lab_al_sens", ["Au-dessus de", "En dessous de"],
                     defaut="Au-dessus de", cols=2)
        cours = prix.get(actif)
        if cours is None:
            complement, _ = derniers_cours([actif])
            cours = complement.get(actif)
        if cours is not None:
            st.caption(f"Cours actuel : {fprix(cours, devise(actif))}")
        seuil = st.number_input("Seuil", min_value=0.0, step=1.0, key="lab_al_seuil",
                                value=float(round(cours, 2)) if cours else 0.0)
        commentaire = st.text_input("Pourquoi ce seuil ? (facultatif)", key="lab_al_note",
                                    placeholder="Ex : niveau du dernier sommet")
        if st.button("Créer l'alerte", type="primary", key="lab_al_go"):
            if seuil > 0:
                ajouter_alerte(actif, sens, seuil, commentaire)
                reset_after(lab_al_note="")
                st.toast("Alerte créée", icon="🔔")
                st.rerun()
            else:
                st.warning("Indiquez un seuil supérieur à zéro.")


def onglet_notes(cfg):
    notes_liste = notes_utilisateur()

    with conteneur("labrow-search"):
        recherche = st.text_input("Rechercher dans vos notes", key="lab_recherche",
                                  placeholder="Ex : or, séance, idée…")
        filtre_type = pills("lab_type_filtre", ["Tous"] + TYPES_NOTE, defaut="Tous", cols=3)

    visibles = notes_liste
    if filtre_type != "Tous":
        visibles = [n for n in visibles if n["type"] == filtre_type]
    if recherche.strip():
        mots = re.findall(r"\w{3,}", recherche.lower())
        classees = []
        for n in visibles:
            blob = f"{n['sujet']} {n['contenu']}".lower()
            score = sum(blob.count(mot) for mot in mots)
            if score:
                classees.append((score, n))
        visibles = [n for _, n in sorted(classees, key=lambda c: -c[0])]

    kpis([
        {"label": "Notes enregistrées", "valeur": fnum(len(notes_liste), 0)},
        {"label": "Affichées ici", "valeur": fnum(len(visibles), 0)},
        {"label": "Alertes actives", "valeur": fnum(len(alertes()), 0)},
    ], largeur=160)

    if visibles:
        for n in reversed(visibles[-40:]):
            with st.expander(f"{n['sujet']} · {n['type']} · {n['date']}"):
                cle_edition = f"lab_edit_{n['idx']}"
                _defaut(cle_edition, n["contenu"] or "")
                edition = st.text_area("Contenu", height=140, key=cle_edition)
                with conteneur(f"labrow-note-{n['idx']}"):
                    colonne_a, colonne_b = st.columns(2)
                    with colonne_a:
                        if st.button("Enregistrer les modifications", type="primary",
                                     key=f"lab_maj_{n['idx']}"):
                            set_cell("IA_Lab", n["idx"], 3, edition)
                            st.toast("Note mise à jour", icon="✅")
                            st.rerun()
                    with colonne_b:
                        if st.button("Supprimer", key=f"lab_supp_{n['idx']}"):
                            delete_row("IA_Lab", n["idx"], libelle="Note supprimée")
                            st.rerun()
    else:
        vide("Aucune note ne correspond. Créez-en une ci-dessous.")

    if notes_liste:
        export = pd.DataFrame(notes_liste)[["date", "type", "sujet", "contenu"]]
        st.download_button("Télécharger toutes les notes (CSV)",
                           export.to_csv(index=False).encode("utf-8"),
                           file_name=f"notes-labo-{date.today()}.csv", mime="text/csv",
                           key="lab_export")

    sous_titre("Nouvelle note")
    sujet = st.text_input("Sujet", key="lab_n_sujet", placeholder="Ex : ce que j'ai compris sur l'or")
    type_note = pills("lab_n_type", TYPES_NOTE, defaut=TYPES_NOTE[0], cols=2)
    contenu = st.text_area("Contenu", key="lab_n_contenu", height=170,
                           placeholder="Ce que vous voulez retrouver plus tard…")
    if st.button("Enregistrer la note", type="primary", key="lab_n_save"):
        if sujet.strip():
            add_row("IA_Lab", [str(date.today()), sujet.strip(), contenu.strip(), type_note])
            reset_after(lab_n_sujet="", lab_n_contenu="")
            st.toast("Note enregistrée", icon="📚")
            st.rerun()
        else:
            st.warning("Donnez un sujet à la note.")

    with st.expander("Réglages du labo"):
        st.caption("Les actifs suivis se choisissent dans l'onglet Marchés et sont partagés "
                   "entre vous deux via Google Sheets.")
        st.caption("Commentaire rédigé : "
                   + ("activé" if cle_ia() else "désactivé (aucune clé dans les secrets)"))
        if st.button("Recharger les cours et vider le cache", key="lab_cfg_cache"):
            st.cache_data.clear()
            st.session_state.pop("lab_live", None)
            st.rerun()
        st.caption(f"Labo version {VERSION_LABO} · {len(UNIVERS)} actifs suivis")

# ==========================================================
# 9. POINT D'ENTRÉE
# ==========================================================
ROUTES = {
    ONGLETS[0]: onglet_marches,
    ONGLETS[1]: onglet_analyse,
    ONGLETS[2]: onglet_actus,
    ONGLETS[3]: onglet_alertes,
    ONGLETS[4]: onglet_notes,
}


def render(ctx):
    global _CTX
    _CTX = ctx

    absents = [nom for nom in REQUIS if nom not in ctx]
    if absents:
        st.error("Le labo n'a pas reçu toutes les fonctions de l'application : "
                 + ", ".join(absents))
        return

    st.markdown(CSS, unsafe_allow_html=True)
    titre("🧠 Labo IA & marchés")
    with conteneur("labtabs"):
        onglet = pills("lab_tab", ONGLETS, defaut=ONGLETS[0], cols=3)

    try:
        cfg = config()
        ROUTES.get(onglet, onglet_marches)(cfg)
    except Exception as err:
        # Une erreur dans un onglet ne doit jamais laisser une page vide :
        # on affiche le message pour pouvoir corriger.
        st.error(f"Le labo a rencontré une erreur sur « {onglet} » : {err}")
        with st.expander("Détail technique"):
            st.code(traceback.format_exc())
        if st.button("Réinitialiser le labo", key="lab_panic"):
            for cle in [c for c in list(st.session_state) if str(c).startswith("lab_")]:
                st.session_state.pop(cle, None)
            st.cache_data.clear()
            st.rerun()
