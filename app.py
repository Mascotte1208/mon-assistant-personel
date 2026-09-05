"""
Labo IA & Marchés — module autonome pour « Notre Assistant ».

Se branche sur l'application principale sans dépendance inverse : le module ne
connaît de l'app que les fonctions passées dans le contexte.

    elif page_cle == "ialab":
        import labo_ia
        labo_ia.render({
            "rows": rows, "add_row": add_row, "delete_row": delete_row,
            "set_cell": set_cell, "pad": pad, "to_float": to_float,
            "parse_date": parse_date, "conteneur": conteneur, "titre": titre,
            "vide": vide, "pills": pills, "reset_after": reset_after,
            "vider_file": vider_file,
        })

Feuille « Trades » : 3 colonnes ajoutées à la fin (Taille, Sortie, DateSortie).
Les anciennes lignes restent lisibles, aucune migration n'est nécessaire.

Sections :
  1. Constantes          5. Journal (lecture / statistiques)
  2. Accès à l'app       6. Onglets
  3. Mise en forme       7. render()
  4. Données de marché

Version 3.1 — corrections d'ouverture sur mobile :
  · plus de boucle d'écriture Google Sheets sur la watchlist du cockpit ;
  · les cours ne sont plus téléchargés avant l'affichage de la page ;
  · plus d'écriture dans st.session_state après création d'un widget ;
  · CSS de largeur restreint aux grands écrans ;
  · toute erreur d'onglet est affichée au lieu de casser la page.
"""

import json
import math
import re
import traceback
from datetime import date

import pandas as pd
import streamlit as st

# ==========================================================
# 1. CONSTANTES
# ==========================================================
VERSION_LABO = "3.2"
CFG_SUJET = "Paramètres du labo"

ONGLETS = ["🧭 Cockpit", "📈 Marchés", "🔬 Analyse", "🎯 Journal", "🧮 DCA", "📚 Notes"]

UNIVERS = {
    "Bitcoin":        ("BTC-USD",   "Crypto"),
    "Ethereum":       ("ETH-USD",   "Crypto"),
    "Solana":         ("SOL-USD",   "Crypto"),
    "Or":             ("GC=F",      "Matières premières"),
    "Argent":         ("SI=F",      "Matières premières"),
    "Pétrole WTI":    ("CL=F",      "Matières premières"),
    "S&P 500":        ("^GSPC",     "Indices"),
    "Nasdaq 100":     ("^NDX",      "Indices"),
    "CAC 40":         ("^FCHI",     "Indices"),
    "Euro Stoxx 50":  ("^STOXX50E", "Indices"),
    "Apple":          ("AAPL",      "Actions"),
    "Nvidia":         ("NVDA",      "Actions"),
    "Microsoft":      ("MSFT",      "Actions"),
    "Tesla":          ("TSLA",      "Actions"),
    "Amazon":         ("AMZN",      "Actions"),
    "ASML":           ("ASML",      "Actions"),
    "EUR/USD":        ("EURUSD=X",  "Devises"),
}
NOM_PAR_TICKER = {t: n for n, (t, _) in UNIVERS.items()}

# libellé : (période yfinance, intervalle, barres par an pour l'annualisation)
PERIODES = {
    "1J": ("1d", "5m", 252 * 78),
    "5J": ("5d", "15m", 252 * 26),
    "1M": ("1mo", "1h", 252 * 7),
    "6M": ("6mo", "1d", 252),
    "1A": ("1y", "1d", 252),
    "5A": ("5y", "1wk", 52),
}

PALETTE = ["#be185d", "#7c3aed", "#0891b2", "#d97706", "#16a34a", "#2563eb"]

TYPES_NOTE = ["Règle de trading", "Apprentissage", "Post-mortem", "Sécurité & dangers"]

PRESETS = {
    "Cassure de résistance (breakout)":
        "Entrée : cassure franche d'un range horizontal en 5 m / 15 m, avec un volume "
        "au moins doublé sur la bougie de cassure.\n"
        "Stop-loss : sous le dernier support du range.\n"
        "Objectif : hauteur du range reportée depuis le point de cassure.\n"
        "Invalidation : retour à l'intérieur du range sur clôture de bougie.",
    "Pullback sur EMA 20":
        "Contexte : EMA 20 au-dessus de l'EMA 50, prix au-dessus des deux.\n"
        "Entrée : retour du prix à moins de 1 % de l'EMA 20 avec une bougie de rejet.\n"
        "Stop-loss : sous le dernier creux, ou 1,5 × ATR sous l'entrée.\n"
        "Objectif : dernier plus haut, puis extension si la tendance tient.",
    "RSI survente / surachat":
        "RSI 14 sous 30 : zone d'achat surveillée, à confirmer par une divergence "
        "ou une bougie de retournement — le RSI seul ne suffit pas en tendance forte.\n"
        "RSI 14 au-dessus de 70 : allègement progressif plutôt que vente totale.",
    "Gestion du risque":
        "Risque maximum par position : 1 % du capital.\n"
        "Ratio rendement / risque minimum accepté : 2 pour 1.\n"
        "Trois pertes consécutives : arrêt de la journée, revue des trades le soir.\n"
        "Taille de position = (capital × risque %) ÷ |entrée − stop|.",
    "Checklist avant d'entrer":
        "1. La tendance de fond va-t-elle dans le sens du trade ?\n"
        "2. Le stop-loss est-il placé sur un niveau technique, pas sur un montant ?\n"
        "3. Le ratio rendement / risque est-il au moins de 2 ?\n"
        "4. La taille de position respecte-t-elle la règle de risque ?\n"
        "5. Y a-t-il une annonce macro dans l'heure qui vient ?\n"
        "6. Est-ce que je suis calme, ou en train de rattraper une perte ?",
    "Erreurs à ne plus répéter":
        "Déplacer un stop-loss pour éviter d'être touché.\n"
        "Doubler une position perdante.\n"
        "Entrer sans avoir noté l'objectif et l'invalidation à l'avance.\n"
        "Trader par ennui, hors des créneaux prévus.",
}

# Feuille Trades : Date, Actif, Sens, Entree, Objectif, StopLoss, Statut, Notes,
#                  Taille, Sortie, DateSortie
COLS_TRADE = 11

# ==========================================================
# 2. ACCÈS À L'APPLICATION HÔTE
# ==========================================================
_CTX = {}


def _f(nom):
    fonction = _CTX.get(nom)
    if fonction is None:
        raise RuntimeError(f"Contexte incomplet : « {nom} » n'a pas été transmis à labo_ia.render().")
    return fonction


def rows(feuille):
    return _f("rows")(feuille)


def add_row(feuille, ligne, flush=True):
    # L'app hôte expose add_row(feuille, ligne) : deux arguments, pas trois.
    # Le paramètre flush est conservé pour la lisibilité des appels du labo.
    return _f("add_row")(feuille, ligne)


def delete_row(feuille, index, libelle="Élément supprimé"):
    return _f("delete_row")(feuille, index, True, libelle)


def set_cell(feuille, index, colonne, valeur, flush=True):
    # L'app hôte expose set_cell(feuille, index, colonne, valeur, annulable, libelle).
    # On s'en tient aux quatre premiers : chaque écriture est déjà poussée.
    return _f("set_cell")(feuille, index, colonne, valeur)


def pad(ligne, n):
    return _f("pad")(ligne, n)


def to_float(valeur):
    return _f("to_float")(valeur)


def parse_date(valeur):
    return _f("parse_date")(valeur)


def conteneur(cle=None, bordure=True):
    return _f("conteneur")(cle, bordure)


def titre(texte):
    return _f("titre")(texte)


def vide(texte):
    return _f("vide")(texte)


def pills(cle, options, defaut=None, cols=3):
    """Un défaut est toujours transmis : sans lui, certaines implémentations
    renvoient None et le reste de la page part en erreur."""
    if defaut is None and options:
        defaut = options[0]
    return _f("pills")(cle, options, defaut, cols)


def flush():
    fonction = _CTX.get("vider_file")
    return fonction() if fonction else True


def reset_after(**champs):
    """Applique des valeurs au prochain rerun. C'est la seule façon sûre de
    modifier une clé de widget déjà instanciée dans le run en cours."""
    fonction = _CTX.get("reset_after")
    if fonction:
        fonction(**champs)
        return True
    return False


def _defaut(cle, valeur):
    """Valeur initiale d'un widget, posée avant sa création.

    Évite le mélange `value=` + `key=` qui déclenche des avertissements et des
    comportements imprévisibles quand la session contient déjà la clé.
    """
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


def ton(valeur, seuil=1e-9):
    if _nan(valeur) or abs(float(valeur)) < seuil:
        return "flat"
    return "up" if float(valeur) > 0 else "down"


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
    """colonnes : liste de (titre, classe 'txt' ou 'num'). Tableau défilable,
    en-tête et première colonne figées : aucune valeur n'est tronquée."""
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


def badge(texte, style="neutre"):
    return f"<span class='lab-badge {style}'>{texte}</span>"


def note(texte, style="info"):
    st.markdown(f"<div class='lab-note {style}'>{texte}</div>", unsafe_allow_html=True)


def sous_titre(texte):
    st.markdown(f"<div class='lab-sec'>{texte}</div>", unsafe_allow_html=True)


CSS = """
<style>
/* Le labo respire plus large que le reste de l'app, mais seulement sur écran :
   sur téléphone on laisse la mise en page de l'application principale. */
@media (min-width:700px){ .block-container{max-width:980px !important;} }

.lab-grid{display:grid; grid-template-columns:repeat(auto-fit,minmax(var(--mini,152px),1fr));
  gap:10px; margin:4px 0 14px;}
.lab-kpi{background:#fff; border:3px solid #be185d; border-radius:16px; padding:10px 13px 11px;
  box-shadow:0 6px 18px rgba(131,24,67,.16); min-width:0; overflow:hidden;}
.lab-kpi .l{font-size:11px; font-weight:800; letter-spacing:.02em; color:#701a75;
  white-space:nowrap; overflow:hidden; text-overflow:ellipsis; margin-bottom:3px;}
.lab-kpi .v{font-size:clamp(15px,4vw,21px); font-weight:800; color:#9d174d; line-height:1.15;
  font-variant-numeric:tabular-nums; white-space:nowrap;}
.lab-kpi .d{font-size:12px; font-weight:800; margin-top:3px; white-space:nowrap;
  font-variant-numeric:tabular-nums;}
.lab-kpi .up{color:#15803d;} .lab-kpi .down{color:#b91c1c;} .lab-kpi .d.flat{color:#6b7280;}

.lab-tablewrap{border:3px solid #be185d; border-radius:16px; background:#fff; overflow:auto;
  max-height:440px; box-shadow:0 6px 18px rgba(131,24,67,.14); margin:4px 0 14px;
  -webkit-overflow-scrolling:touch;}
.lab-table{border-collapse:separate; border-spacing:0; width:100%; font-size:13px;}
.lab-table th{position:sticky; top:0; z-index:3; background:#fdf2f8; color:#9d174d; text-align:left;
  font-size:11.5px; font-weight:800; padding:10px 12px; white-space:nowrap;
  border-bottom:2px solid #f472b6;}
.lab-table td{padding:9px 12px; white-space:nowrap; font-weight:700; color:#311026;
  font-variant-numeric:tabular-nums; border-bottom:1px solid #fce7f3;}
.lab-table td.num, .lab-table th.num{text-align:right;}
.lab-table tbody tr:last-child td{border-bottom:none;}
.lab-table td:first-child{position:sticky; left:0; z-index:2; background:#fff;
  box-shadow:1px 0 0 #fce7f3;}
.lab-table th:first-child{left:0; z-index:4;}
.lab-table .up{color:#15803d;} .lab-table .down{color:#b91c1c;} .lab-table .flat{color:#6b7280;}

.lab-badge{display:inline-block; padding:3px 9px; border-radius:9px; font-size:11px;
  font-weight:800; white-space:nowrap; border:1.5px solid;}
.lab-badge.achat{background:#f0fdf4; color:#15803d; border-color:#86efac;}
.lab-badge.vente{background:#fef2f2; color:#b91c1c; border-color:#fca5a5;}
.lab-badge.neutre{background:#fdf2f8; color:#be185d; border-color:#f472b6;}

.lab-note{border-radius:14px; padding:11px 14px; font-size:13px; font-weight:700; margin:6px 0 12px;
  background:#fdf2f8; border:2px solid #f472b6; color:#9d174d; line-height:1.5;}
.lab-note.warn{background:#fff7ed; border-color:#fb923c; color:#c2410c;}
.lab-note.calme{background:#f8fafc; border-color:#cbd5e1; color:#475569;}
.lab-sec{font-weight:800; font-size:15.5px; color:#9d174d; margin:16px 0 6px;}

/* Dans le labo, les rangées de champs passent à la ligne au lieu de s'écraser. */
[class*="st-key-labrow"] [data-testid="stHorizontalBlock"]{flex-wrap:wrap !important; gap:10px !important;}
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
    par_nom = {NOM_PAR_TICKER.get(t, t): df for t, df in paquets.items()}
    return par_nom, barres_an, err


# --- Indicateurs ------------------------------------------------------------
def ema(serie, n):
    return serie.ewm(span=n, adjust=False).mean()


def rsi(serie, n=14):
    delta = serie.diff()
    hausse = delta.clip(lower=0).ewm(alpha=1 / n, adjust=False).mean()
    baisse = (-delta.clip(upper=0)).ewm(alpha=1 / n, adjust=False).mean()
    force = hausse / baisse.replace(0, 1e-12)
    return 100 - 100 / (1 + force)


def macd(serie, court=12, long=26, lissage=9):
    ligne = ema(serie, court) - ema(serie, long)
    signal = ema(ligne, lissage)
    return ligne, signal, ligne - signal


def bollinger(serie, n=20, k=2.0):
    moyenne = serie.rolling(n).mean()
    ecart = serie.rolling(n).std()
    return moyenne, moyenne + k * ecart, moyenne - k * ecart


def atr(df, n=14):
    if df is None or not {"High", "Low", "Close"}.issubset(df.columns):
        return None
    haut, bas, cloture = df["High"], df["Low"], df["Close"]
    precedent = cloture.shift()
    amplitude = pd.concat([haut - bas, (haut - precedent).abs(), (bas - precedent).abs()],
                          axis=1).max(axis=1)
    return amplitude.ewm(alpha=1 / n, adjust=False).mean()


def volatilite(serie, barres_an):
    variations = serie.pct_change().dropna()
    if len(variations) < 3:
        return float("nan")
    return float(variations.std() * math.sqrt(barres_an) * 100)


def profil(df, barres_an):
    """Photo complète d'un actif sur la période chargée."""
    if df is None or "Close" not in df:
        return None
    cloture = df["Close"].dropna()
    if len(cloture) < 2:
        return None
    dernier, premier = float(cloture.iloc[-1]), float(cloture.iloc[0])
    p = {
        "serie": cloture,
        "dernier": dernier,
        "var": (dernier / premier - 1) * 100 if premier else float("nan"),
        "haut": float(cloture.max()),
        "bas": float(cloture.min()),
        "vol": volatilite(cloture, barres_an),
        "dd": float((cloture / cloture.cummax() - 1).min() * 100),
        "rsi": float(rsi(cloture).iloc[-1]) if len(cloture) > 15 else float("nan"),
        "ema20": float(ema(cloture, 20).iloc[-1]) if len(cloture) >= 20 else float("nan"),
        "ema50": float(ema(cloture, 50).iloc[-1]) if len(cloture) >= 50 else float("nan"),
    }
    p["ecart20"] = (dernier / p["ema20"] - 1) * 100 if not _nan(p["ema20"]) else float("nan")
    if not _nan(p["ema20"]) and not _nan(p["ema50"]):
        if p["ema20"] > p["ema50"] and dernier > p["ema20"]:
            p["tendance"] = "Haussière"
        elif p["ema20"] < p["ema50"] and dernier < p["ema20"]:
            p["tendance"] = "Baissière"
        else:
            p["tendance"] = "Indécise"
    else:
        p["tendance"] = "—"
    return p


def signaux(df):
    """Lecture des règles du carnet : cassure, pullback EMA 20, RSI, MACD."""
    if df is None or "Close" not in df:
        return []
    cloture = df["Close"].dropna()
    if len(cloture) < 25:
        return []
    prix = float(cloture.iloc[-1])
    valeur_rsi = float(rsi(cloture).iloc[-1])
    e20 = float(ema(cloture, 20).iloc[-1])
    e50 = float(ema(cloture, 50).iloc[-1]) if len(cloture) >= 50 else e20
    plus_haut = float(cloture.iloc[-21:-1].max())
    plus_bas = float(cloture.iloc[-21:-1].min())
    _, _, histogramme = macd(cloture)
    histogramme = histogramme.dropna()

    listes = []
    if valeur_rsi < 30:
        listes.append((f"RSI en survente ({valeur_rsi:.0f})", "achat"))
    elif valeur_rsi > 70:
        listes.append((f"RSI en surachat ({valeur_rsi:.0f})", "vente"))
    if prix > plus_haut:
        listes.append(("Cassure du plus haut 20 périodes", "achat"))
    if prix < plus_bas:
        listes.append(("Cassure du plus bas 20 périodes", "vente"))
    if e20 > e50 and e20 and abs(prix / e20 - 1) <= 0.01:
        listes.append(("Pullback sur EMA 20 en tendance haussière", "achat"))
    if len(histogramme) >= 2:
        avant, maintenant = float(histogramme.iloc[-2]), float(histogramme.iloc[-1])
        if avant <= 0 < maintenant:
            listes.append(("Croisement MACD haussier", "achat"))
        elif avant >= 0 > maintenant:
            listes.append(("Croisement MACD baissier", "vente"))
    return listes


def biais(liste_signaux):
    score = sum(1 if s[1] == "achat" else -1 for s in liste_signaux)
    if score >= 2:
        return "Orientation acheteuse", "achat", score
    if score <= -2:
        return "Orientation vendeuse", "vente", score
    return "Pas de direction nette", "neutre", score


# --- Graphiques -------------------------------------------------------------
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
        font=dict(family="Plus Jakarta Sans, sans-serif", size=12, color="#581c87"),
        paper_bgcolor="rgba(0,0,0,0)",
    )
    return fig


def courbe(df, titre_y="", hauteur=360, aire=False):
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
                fill="tozeroy" if aire and i == 0 else None,
            ))
        st.plotly_chart(_mise_en_page(fig, hauteur, titre_y), use_container_width=True)
    except Exception:
        st.line_chart(df)

# ==========================================================
# 5. CONFIGURATION, JOURNAL ET STATISTIQUES
# ==========================================================
def _config_par_defaut():
    return {
        "capital": 5000.0,
        "risque": 1.0,
        "watchlist": ["Bitcoin", "Or", "S&P 500", "Nvidia"],
        "dca_montant": 150.0,
        "dca_poids": {"Bitcoin": 40, "Or": 30, "Nvidia": 30},
    }


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
            if type_ == "Config" and sujet == CFG_SUJET:
                try:
                    charge = json.loads(contenu)
                    if isinstance(charge, dict):
                        base.update(charge)
                except Exception:
                    pass
                st.session_state["lab_cfg_idx"] = index
                break
    except Exception:
        # Feuille absente ou illisible : on démarre sur les valeurs par défaut.
        pass

    base["watchlist"] = [n for n in base.get("watchlist", []) if n in UNIVERS][:8]
    base["dca_poids"] = {n: int(p) for n, p in base.get("dca_poids", {}).items() if n in UNIVERS}
    st.session_state["lab_cfg"] = base
    return base


def sauver_config(cfg):
    """Écrit les réglages sans jamais relire la feuille dans la foulée.

    L'ancienne version supprimait « lab_cfg » de la session après un ajout, ce
    qui provoquait une relecture, une divergence, puis une nouvelle écriture :
    l'application bouclait sur l'API Google et ne s'affichait plus.
    """
    st.session_state["lab_cfg"] = cfg
    charge = json.dumps(cfg, ensure_ascii=False)
    index = st.session_state.get("lab_cfg_idx")
    try:
        if index:
            set_cell("IA_Lab", index, 3, charge)
            return
        add_row("IA_Lab", [str(date.today()), CFG_SUJET, charge, "Config"])
        for i, ligne in rows("IA_Lab"):          # on retient l'index tout de suite
            _, sujet, _, type_ = pad(ligne, 4)
            if type_ == "Config" and sujet == CFG_SUJET:
                st.session_state["lab_cfg_idx"] = i
                break
    except Exception as err:
        st.warning(f"Réglages non enregistrés : {str(err)[:120]}")


def notes_utilisateur():
    """Toutes les notes sauf la ligne technique de configuration."""
    sortie = []
    try:
        lignes = rows("IA_Lab")
    except Exception:
        return sortie
    for index, ligne in lignes:
        d, sujet, contenu, type_ = pad(ligne, 4)
        if type_ == "Config":
            continue
        sortie.append({"idx": index, "date": d, "sujet": sujet,
                       "contenu": contenu, "type": type_ or "Apprentissage"})
    return sortie


def actif_connu(libelle):
    """« Bitcoin (BTC) » d'un ancien trade → « Bitcoin »."""
    texte = (libelle or "").lower()
    for nom in UNIVERS:
        if re.search(rf"\b{re.escape(nom.lower())}\b", texte):
            return nom
    return None


def lire_trades():
    sortie = []
    try:
        lignes = rows("Trades")
    except Exception:
        return sortie
    for index, ligne in lignes:
        (d, actif, sens, entree, objectif, stop,
         statut, notes, taille, sortie_prix, date_sortie) = pad(ligne, COLS_TRADE)
        prix_e, prix_o, prix_s = to_float(entree), to_float(objectif), to_float(stop)
        quantite = to_float(taille) or 1.0
        prix_x = to_float(sortie_prix)
        risque_unitaire = abs(prix_e - prix_s) if prix_e > 0 and prix_s > 0 else 0.0
        gain_unitaire = abs(prix_o - prix_e) if prix_e > 0 and prix_o > 0 else 0.0
        cloture = str(statut or "").lower().startswith("cl")
        pnl = r_realise = float("nan")
        if cloture and prix_x > 0 and prix_e > 0:
            sens_num = -1 if sens == "Vente" else 1
            unitaire = (prix_x - prix_e) * sens_num
            pnl = unitaire * quantite
            if risque_unitaire:
                r_realise = unitaire / risque_unitaire
        sortie.append({
            "idx": index, "date": d, "date_obj": parse_date(d), "actif": actif,
            "nom_marche": actif_connu(actif), "sens": sens or "Achat",
            "entree": prix_e, "objectif": prix_o, "stop": prix_s,
            "statut": statut or "En cours", "notes": notes, "taille": quantite,
            "sortie": prix_x, "date_sortie": date_sortie, "cloture": cloture,
            "risque_unitaire": risque_unitaire,
            "risque_total": risque_unitaire * quantite,
            "rr": gain_unitaire / risque_unitaire if risque_unitaire else float("nan"),
            "pnl": pnl, "r_realise": r_realise,
        })
    return sortie


def stats_trades(trades):
    clotures = [t for t in trades if t["cloture"] and not _nan(t["pnl"])]
    gains = [t["pnl"] for t in clotures if t["pnl"] > 0]
    pertes = [t["pnl"] for t in clotures if t["pnl"] < 0]
    r_valides = [t["r_realise"] for t in clotures if not _nan(t["r_realise"])]
    somme_pertes = abs(sum(pertes))
    return {
        "clotures": len(clotures),
        "ouverts": len([t for t in trades if not t["cloture"]]),
        "gagnants": len(gains),
        "reussite": (len(gains) / len(clotures) * 100) if clotures else float("nan"),
        "pnl": sum(t["pnl"] for t in clotures),
        "gain_moyen": (sum(gains) / len(gains)) if gains else 0.0,
        "perte_moyenne": (sum(pertes) / len(pertes)) if pertes else 0.0,
        "facteur": (sum(gains) / somme_pertes) if somme_pertes else float("nan"),
        "esperance_r": (sum(r_valides) / len(r_valides)) if r_valides else float("nan"),
        "liste_clotures": clotures,
    }

# ==========================================================
# 6. ONGLETS
# ==========================================================
def onglet_cockpit(cfg):
    trades = lire_trades()
    stats = stats_trades(trades)
    ouverts = [t for t in trades if not t["cloture"]]
    risque_engage = sum(t["risque_total"] for t in ouverts)
    part_risque = (risque_engage / cfg["capital"] * 100) if cfg["capital"] else float("nan")

    kpis([
        {"label": "Capital de référence", "valeur": fnum(cfg["capital"], 0, "€"),
         "aide": f"risque cible {fnum(cfg['risque'], 1)}{FINE}% par position"},
        {"label": "Positions ouvertes", "valeur": fnum(stats["ouverts"], 0),
         "aide": f"{fnum(stats['clotures'], 0)} clôturées"},
        {"label": "Risque engagé", "valeur": fnum(risque_engage, 2, "€"),
         "delta": f"{fpct(part_risque, 1, signe=False)} du capital",
         "delta_ton": "down" if not _nan(part_risque) and part_risque > 5 else "flat"},
        {"label": "Résultat réalisé", "valeur": fnum(stats["pnl"], 2, "€"),
         "delta_ton": ton(stats["pnl"]), "delta": "cumul des trades clôturés"},
        {"label": "Trades gagnants", "valeur": fpct(stats["reussite"], 0, signe=False),
         "aide": f"{fnum(stats['gagnants'], 0)} sur {fnum(stats['clotures'], 0)}"},
        {"label": "Espérance", "valeur": f"{fnum(stats['esperance_r'], 2)}{FINE}R",
         "delta_ton": ton(stats["esperance_r"]), "delta": "gain moyen en unités de risque"},
    ])

    # --- Watchlist ---------------------------------------------------------
    with conteneur("labrow-watch"):
        st.markdown("**Suivi du jour**")
        _defaut("lab_watch", [n for n in cfg["watchlist"] if n in UNIVERS][:8])
        choix = st.multiselect("Actifs suivis", list(UNIVERS), max_selections=8,
                               key="lab_watch", label_visibility="collapsed")

    # Une seule écriture par changement réel : sans ce garde-fou, la page
    # réécrivait la configuration à chaque rerun et ne finissait jamais de charger.
    deja_sauve = st.session_state.get("lab_watch_saved")
    if deja_sauve is None:
        deja_sauve = tuple(cfg["watchlist"])
    if tuple(choix) != tuple(deja_sauve):
        st.session_state["lab_watch_saved"] = tuple(choix)
        cfg["watchlist"] = list(choix)
        sauver_config(cfg)

    if not choix:
        note("Choisissez les actifs à suivre pour afficher le tableau du jour.")
        return

    # --- Chargement des cours à la demande ---------------------------------
    # Sur téléphone, télécharger huit séries intraday avant le premier affichage
    # laissait la page sur un spinner interminable.
    if not st.session_state.get("lab_cockpit_live"):
        note("Les cours ne sont pas encore chargés — appuyez pour interroger les marchés.")
        if st.button("📡 Charger les cours", type="primary", key="lab_cockpit_go"):
            st.session_state["lab_cockpit_live"] = True
            st.rerun()
        dernieres = notes_utilisateur()[-3:]
        if dernieres:
            sous_titre("Dernières notes")
            for n in reversed(dernieres):
                st.markdown(f"<div class='lab-note calme'><b>{n['sujet']}</b> · {n['date']}<br>"
                            f"{(n['contenu'] or '')[:180]}</div>", unsafe_allow_html=True)
        return

    besoins = set(choix) | {t["nom_marche"] for t in ouverts if t["nom_marche"]}
    with st.spinner("Lecture des marchés…"):
        donnees, barres_an, err = marche(sorted(besoins), "1J")
    if err:
        note(f"⚠️ {err}", "warn")
        if st.button("Réessayer", key="lab_cockpit_retry"):
            st.cache_data.clear()
            st.rerun()
        return

    lignes, alertes = [], []
    for nom in choix:
        p = profil(donnees.get(nom), barres_an)
        if not p:
            lignes.append([nom, "—", "—", "—", "—", "—"])
            continue
        signes = signaux(donnees[nom])
        libelle_biais, style_biais, _ = biais(signes)
        lignes.append([
            nom,
            fprix(p["dernier"]),
            f"<span class='{ton(p['var'])}'>{fpct(p['var'])}</span>",
            fnum(p["rsi"], 0),
            p["tendance"],
            badge(libelle_biais, style_biais),
        ])
        for texte, sens in signes:
            alertes.append(f"{badge(sens.capitalize(), sens)} <b>{nom}</b> — {texte}")

    sous_titre("Marchés suivis")
    table([("Actif", "txt"), ("Dernier", "num"), ("Séance", "num"),
           ("RSI 14", "num"), ("Tendance", "txt"), ("Lecture", "txt")], lignes)

    # --- Positions ouvertes vs prix actuel ---------------------------------
    if ouverts:
        sous_titre("Positions ouvertes")
        lignes_pos = []
        for t in ouverts:
            p = profil(donnees.get(t["nom_marche"]), barres_an) if t["nom_marche"] else None
            actuel = p["dernier"] if p else float("nan")
            if not _nan(actuel) and t["entree"]:
                sens_num = -1 if t["sens"] == "Vente" else 1
                latent = (actuel - t["entree"]) * sens_num * t["taille"]
                vers_stop = abs(actuel - t["stop"]) / actuel * 100 if t["stop"] and actuel else float("nan")
            else:
                latent = vers_stop = float("nan")
            lignes_pos.append([
                t["actif"],
                badge(t["sens"], "achat" if t["sens"] != "Vente" else "vente"),
                fprix(t["entree"]), fprix(actuel),
                f"<span class='{ton(latent)}'>{fnum(latent, 2, '€')}</span>",
                fpct(vers_stop, 1, signe=False),
                fnum(t["rr"], 2),
            ])
            if not _nan(vers_stop) and vers_stop < 1.5:
                alertes.append(f"{badge('Risque', 'vente')} <b>{t['actif']}</b> — "
                               f"le prix est à {fpct(vers_stop, 1, signe=False)} du stop-loss")
        table([("Actif", "txt"), ("Sens", "txt"), ("Entrée", "num"), ("Actuel", "num"),
               ("Latent", "num"), ("Distance stop", "num"), ("R/R visé", "num")], lignes_pos)

    sous_titre("Ce qui mérite un œil")
    if alertes:
        st.markdown("<div class='lab-note'>" + "<br>".join(alertes[:10]) + "</div>",
                    unsafe_allow_html=True)
    else:
        note("Aucun signal actif sur votre sélection. Rien à forcer.")

    dernieres = notes_utilisateur()[-3:]
    if dernieres:
        sous_titre("Dernières notes")
        for n in reversed(dernieres):
            st.markdown(f"<div class='lab-note calme'><b>{n['sujet']}</b> · {n['date']}<br>"
                        f"{(n['contenu'] or '')[:180]}</div>", unsafe_allow_html=True)


def onglet_marches(cfg):
    with conteneur("labrow-sel"):
        colonne_a, colonne_b = st.columns([2, 1])
        with colonne_a:
            _defaut("lab_cmp", [n for n in cfg["watchlist"] if n in UNIVERS][:4]
                    or ["Bitcoin", "Or"])
            choix = st.multiselect("Actifs à comparer", list(UNIVERS),
                                   max_selections=6, key="lab_cmp")
        with colonne_b:
            periode = pills("lab_periode", list(PERIODES), defaut="5J", cols=3)
        base = pills("lab_base", ["Base 100", "Prix réels"], defaut="Base 100", cols=2)

    if not choix:
        note("Sélectionnez au moins un actif.")
        return

    with st.spinner("Lecture des marchés…"):
        donnees, barres_an, err = marche(choix, periode)
    if err:
        note(f"⚠️ {err}", "warn")
        return

    profils = {nom: profil(donnees.get(nom), barres_an) for nom in choix}
    valides = {nom: p for nom, p in profils.items() if p}
    if not valides:
        note("Aucune donnée exploitable sur cette période.", "warn")
        return

    kpis([{"label": nom, "valeur": fprix(p["dernier"]),
           "delta": fpct(p["var"]), "delta_ton": ton(p["var"])}
          for nom, p in valides.items()], largeur=160)

    sous_titre("Tableau de bord")
    lignes = []
    for nom, p in valides.items():
        lignes.append([
            nom,
            fprix(p["dernier"]),
            f"<span class='{ton(p['var'])}'>{fpct(p['var'])}</span>",
            fnum(p["rsi"], 0),
            f"<span class='{ton(p['ecart20'])}'>{fpct(p['ecart20'], 1)}</span>",
            p["tendance"],
            fpct(p["vol"], 1, signe=False),
            f"<span class='down'>{fpct(p['dd'], 1)}</span>",
            fprix(p["haut"]),
            fprix(p["bas"]),
        ])
    table([("Actif", "txt"), ("Dernier", "num"), ("Variation", "num"), ("RSI 14", "num"),
           ("Écart EMA 20", "num"), ("Tendance", "txt"), ("Volatilité an.", "num"),
           ("Repli max", "num"), ("Plus haut", "num"), ("Plus bas", "num")], lignes)
    st.caption("Le tableau défile horizontalement : aucune valeur n'est tronquée.")

    sous_titre("Évolution comparée")
    series = pd.DataFrame({nom: p["serie"] for nom, p in valides.items()})
    if base == "Base 100":
        series = series.apply(lambda c: c / c.dropna().iloc[0] * 100 if not c.dropna().empty else c)
        courbe(series, "Base 100 au départ de la période")
    else:
        courbe(series, "Prix (devise de cotation)")

    if len(valides) >= 2 and len(series.dropna()) > 5:
        sous_titre("Corrélation des variations")
        matrice = series.pct_change().corr()
        colonnes = [("", "txt")] + [(nom, "num") for nom in matrice.columns]
        lignes_corr = []
        for nom in matrice.index:
            cellules = [f"<b>{nom}</b>"]
            for autre in matrice.columns:
                valeur = matrice.loc[nom, autre]
                classe = "up" if valeur > 0.5 else ("down" if valeur < -0.2 else "flat")
                cellules.append(f"<span class='{classe}'>{fnum(valeur, 2)}</span>")
            lignes_corr.append(cellules)
        table(colonnes, lignes_corr)
        st.caption("1,00 = les deux actifs bougent ensemble · 0,00 = aucun lien · "
                   "négatif = ils s'opposent.")

    sous_titre("Garder une trace")
    with conteneur("labrow-note-marche"):
        commentaire = st.text_area("Ce que vous retenez de cette séance",
                                   key="lab_note_marche", height=90,
                                   placeholder="Ex : l'or tient son support pendant que le Nasdaq recule…")
        if st.button("Enregistrer l'analyse", type="primary", key="lab_save_marche"):
            if commentaire.strip():
                resume = " · ".join(f"{nom} {fpct(p['var'])}" for nom, p in valides.items())
                add_row("IA_Lab", [str(date.today()), f"Analyse marchés ({periode})",
                                   f"{resume}\n\n{commentaire.strip()}", "Apprentissage"])
                reset_after(lab_note_marche="")
                st.toast("Analyse enregistrée", icon="✅")
                st.rerun()
            else:
                st.warning("Écrivez d'abord ce que vous retenez.")


def onglet_analyse(cfg):
    with conteneur("labrow-ana"):
        colonne_a, colonne_b = st.columns([2, 1])
        with colonne_a:
            actif = st.selectbox("Actif étudié", list(UNIVERS), key="lab_ana_actif")
        with colonne_b:
            periode = pills("lab_ana_periode", list(PERIODES), defaut="1M", cols=3)

    with st.spinner("Lecture des marchés…"):
        donnees, barres_an, err = marche([actif], periode)
    if err:
        note(f"⚠️ {err}", "warn")
        return
    df = donnees.get(actif)
    p = profil(df, barres_an)
    if not p:
        note("Pas assez de données pour cet actif sur la période.", "warn")
        return

    cloture = p["serie"]
    valeurs_atr = atr(df)
    atr_actuel = float("nan")
    if valeurs_atr is not None:
        propres = valeurs_atr.dropna()
        if not propres.empty:
            atr_actuel = float(propres.iloc[-1])

    kpis([
        {"label": "Dernier prix", "valeur": fprix(p["dernier"]),
         "delta": fpct(p["var"]), "delta_ton": ton(p["var"])},
        {"label": "RSI 14", "valeur": fnum(p["rsi"], 1),
         "aide": "sous 30 : survente · au-dessus de 70 : surachat"},
        {"label": "Écart à l'EMA 20", "valeur": fpct(p["ecart20"], 2),
         "delta_ton": ton(p["ecart20"]), "delta": p["tendance"]},
        {"label": "ATR 14", "valeur": fprix(atr_actuel),
         "aide": "amplitude moyenne d'une bougie"},
        {"label": "Volatilité annualisée", "valeur": fpct(p["vol"], 1, signe=False)},
        {"label": "Repli maximum", "valeur": fpct(p["dd"], 1), "delta_ton": "down"},
    ])

    go = _plotly()
    moyenne_b, haute_b, basse_b = bollinger(cloture)
    if go is not None:
        try:
            from plotly.subplots import make_subplots
            fig = make_subplots(rows=3, cols=1, shared_xaxes=True,
                                row_heights=[0.58, 0.21, 0.21], vertical_spacing=0.04)
            if {"Open", "High", "Low", "Close"}.issubset(df.columns):
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                    name="Cours", increasing_line_color="#15803d", decreasing_line_color="#b91c1c",
                    showlegend=False), row=1, col=1)
            else:
                fig.add_trace(go.Scatter(x=cloture.index, y=cloture, name="Cours",
                                         line=dict(color="#be185d", width=2.4)), row=1, col=1)
            fig.add_trace(go.Scatter(x=haute_b.index, y=haute_b, name="Bollinger",
                                     line=dict(color="#c4b5fd", width=1)), row=1, col=1)
            fig.add_trace(go.Scatter(x=basse_b.index, y=basse_b, name="Bollinger", showlegend=False,
                                     line=dict(color="#c4b5fd", width=1),
                                     fill="tonexty", fillcolor="rgba(196,181,253,.16)"), row=1, col=1)
            fig.add_trace(go.Scatter(x=cloture.index, y=ema(cloture, 20), name="EMA 20",
                                     line=dict(color="#be185d", width=2)), row=1, col=1)
            if len(cloture) >= 50:
                fig.add_trace(go.Scatter(x=cloture.index, y=ema(cloture, 50), name="EMA 50",
                                         line=dict(color="#7c3aed", width=2, dash="dot")),
                              row=1, col=1)

            valeurs_rsi = rsi(cloture)
            fig.add_trace(go.Scatter(x=valeurs_rsi.index, y=valeurs_rsi, name="RSI 14",
                                     line=dict(color="#0891b2", width=2)), row=2, col=1)
            fig.add_hline(y=70, row=2, col=1, line=dict(color="#b91c1c", width=1, dash="dash"))
            fig.add_hline(y=30, row=2, col=1, line=dict(color="#15803d", width=1, dash="dash"))

            ligne_m, signal_m, histo = macd(cloture)
            fig.add_trace(go.Bar(x=histo.index, y=histo, name="MACD",
                                 marker_color="#f472b6"), row=3, col=1)
            fig.add_trace(go.Scatter(x=ligne_m.index, y=ligne_m, name="Ligne MACD",
                                     line=dict(color="#9d174d", width=1.6)), row=3, col=1)
            fig.add_trace(go.Scatter(x=signal_m.index, y=signal_m, name="Signal",
                                     line=dict(color="#d97706", width=1.4)), row=3, col=1)

            fig.update_xaxes(rangeslider_visible=False)
            fig.update_yaxes(title_text="RSI", range=[0, 100], row=2, col=1)
            fig.update_yaxes(title_text="MACD", row=3, col=1)
            st.plotly_chart(_mise_en_page(fig, 620, "Prix"), use_container_width=True)
        except Exception:
            courbe(pd.DataFrame({actif: cloture}), "Prix")
    else:
        courbe(pd.DataFrame({actif: cloture}), "Prix")

    # --- Niveaux ------------------------------------------------------------
    haut, bas, dernier = p["haut"], p["bas"], p["dernier"]
    pivot = (haut + bas + dernier) / 3
    haute_propre, basse_propre = haute_b.dropna(), basse_b.dropna()
    niveaux = [
        ("Résistance 2", pivot + (haut - bas)),
        ("Résistance 1", 2 * pivot - bas),
        ("Plus haut de la période", haut),
        ("Bande de Bollinger haute",
         float(haute_propre.iloc[-1]) if not haute_propre.empty else float("nan")),
        ("Pivot", pivot),
        ("EMA 20", p["ema20"]),
        ("EMA 50", p["ema50"]),
        ("Bande de Bollinger basse",
         float(basse_propre.iloc[-1]) if not basse_propre.empty else float("nan")),
        ("Plus bas de la période", bas),
        ("Support 1", 2 * pivot - haut),
        ("Support 2", pivot - (haut - bas)),
    ]
    sous_titre("Niveaux à surveiller")
    table([("Niveau", "txt"), ("Prix", "num"), ("Distance", "num")],
          [[libelle, fprix(valeur),
            f"<span class='{ton(valeur - dernier)}'>{fpct((valeur / dernier - 1) * 100, 2)}</span>"
            if not _nan(valeur) and dernier else "—"]
           for libelle, valeur in niveaux])

    # --- Lecture des règles -------------------------------------------------
    signes = signaux(df)
    libelle_biais, style_biais, score = biais(signes)
    sous_titre("Lecture selon vos règles")
    if signes:
        contenu = "<br>".join(f"{badge(sens.capitalize(), sens)} {texte}" for texte, sens in signes)
        st.markdown(f"<div class='lab-note'>{contenu}<br><br>"
                    f"<b>Synthèse :</b> {libelle_biais} (score {score:+d})</div>",
                    unsafe_allow_html=True)
    else:
        note("Aucune de vos règles ne se déclenche ici. Attendre reste une position.")
    note("Ces lectures sont mécaniques : elles appliquent vos règles aux prix, elles ne "
         "prédisent rien et ne constituent pas un conseil en investissement.", "calme")

    # --- Passerelle vers le journal ----------------------------------------
    if not _nan(atr_actuel) and atr_actuel > 0:
        sous_titre("Préparer une position")
        st.caption("Stop à 1,5 × ATR, objectif à 3 × ATR : un ratio de 2 pour 1 par construction.")
        with conteneur("labrow-prep"):
            colonne_a, colonne_b = st.columns(2)
            with colonne_a:
                if st.button("Préparer un achat", key="lab_prep_achat"):
                    _preparer(actif, "Achat", dernier, dernier - 1.5 * atr_actuel,
                              dernier + 3 * atr_actuel)
            with colonne_b:
                if st.button("Préparer une vente", key="lab_prep_vente"):
                    _preparer(actif, "Vente", dernier, dernier + 1.5 * atr_actuel,
                              dernier - 3 * atr_actuel)


def _preparer(actif, sens, entree, stop, objectif):
    """Pré-remplit le formulaire du journal puis bascule sur l'onglet.

    Tout passe par reset_after : « lab_tab » et « lab_t_sens » sont des clés de
    widgets déjà créés dans ce run, et Streamlit refuse qu'on les modifie
    directement — c'était la cause d'une exception au clic.
    """
    applique = reset_after(
        lab_tab=ONGLETS[3],
        lab_t_sens=sens,
        lab_t_actif=actif,
        lab_t_entree=round(float(entree), 4),
        lab_t_stop=round(float(stop), 4),
        lab_t_objectif=round(float(objectif), 4),
        lab_t_taille=0.0,
        lab_t_notes=f"Préparé depuis l'analyse technique de {actif}.",
    )
    if not applique:
        st.warning("Ouvrez l'onglet Journal pour saisir la position.")
        return
    st.rerun()


def onglet_journal(cfg):
    trades = lire_trades()
    stats = stats_trades(trades)

    kpis([
        {"label": "Résultat réalisé", "valeur": fnum(stats["pnl"], 2, "€"),
         "delta_ton": ton(stats["pnl"]), "delta": f"{fnum(stats['clotures'], 0)} trades clôturés"},
        {"label": "Trades gagnants", "valeur": fpct(stats["reussite"], 0, signe=False),
         "aide": f"{fnum(stats['gagnants'], 0)} sur {fnum(stats['clotures'], 0)}"},
        {"label": "Facteur de profit", "valeur": fnum(stats["facteur"], 2),
         "aide": "gains ÷ pertes · au-dessus de 1, le système gagne"},
        {"label": "Espérance", "valeur": f"{fnum(stats['esperance_r'], 2)}{FINE}R",
         "delta_ton": ton(stats["esperance_r"]), "delta": "par trade, en unités de risque"},
        {"label": "Gain moyen", "valeur": fnum(stats["gain_moyen"], 2, "€"), "delta_ton": "up"},
        {"label": "Perte moyenne", "valeur": fnum(stats["perte_moyenne"], 2, "€"),
         "delta_ton": "down"},
    ])

    if stats["liste_clotures"]:
        ordonnes = sorted(stats["liste_clotures"],
                          key=lambda t: t["date_obj"] or date(1970, 1, 1))
        cumul = pd.Series([t["pnl"] for t in ordonnes]).cumsum()
        cumul.index = range(1, len(cumul) + 1)
        sous_titre("Courbe de résultat")
        courbe(pd.DataFrame({"Résultat cumulé (€)": cumul}), "€", hauteur=280, aire=True)

    # --- Filtres et tableau -------------------------------------------------
    filtre = pills("lab_filtre", ["Tout", "En cours", "Clôturés"], defaut="En cours", cols=3)
    if filtre == "En cours":
        visibles = [t for t in trades if not t["cloture"]]
    elif filtre == "Clôturés":
        visibles = [t for t in trades if t["cloture"]]
    else:
        visibles = list(trades)
    visibles = list(reversed(visibles))

    if visibles:
        sous_titre(f"Journal ({len(visibles)})")
        table([("Actif", "txt"), ("Sens", "txt"), ("Date", "txt"), ("Entrée", "num"),
               ("Stop", "num"), ("Objectif", "num"), ("Taille", "num"), ("R/R", "num"),
               ("Statut", "txt"), ("Résultat", "num"), ("R", "num")],
              [[t["actif"], badge(t["sens"], "achat" if t["sens"] != "Vente" else "vente"),
                t["date"], fprix(t["entree"]), fprix(t["stop"]), fprix(t["objectif"]),
                fnum(t["taille"], 4).rstrip("0").rstrip(",") if t["taille"] else "—",
                fnum(t["rr"], 2), t["statut"],
                f"<span class='{ton(t['pnl'])}'>{fnum(t['pnl'], 2, '€')}</span>",
                fnum(t["r_realise"], 2)] for t in visibles])
    else:
        vide("Aucun trade dans ce filtre.")

    # --- Actions par trade --------------------------------------------------
    for t in visibles[:20]:
        etiquette = (f"{'🟢' if t['sens'] != 'Vente' else '🔴'} {t['actif']} · "
                     f"entrée {fprix(t['entree'])} · {t['statut']}")
        with st.expander(etiquette):
            st.markdown(
                f"**Objectif** {fprix(t['objectif'])} · **Stop** {fprix(t['stop'])} · "
                f"**Taille** {fnum(t['taille'], 4)} · **Risque** {fnum(t['risque_total'], 2, '€')} · "
                f"**R/R visé** {fnum(t['rr'], 2)}"
            )
            if t["notes"]:
                st.write(t["notes"])
            if t["cloture"]:
                st.markdown(f"Sortie {fprix(t['sortie'])} le {t['date_sortie'] or '—'} · "
                            f"résultat {fnum(t['pnl'], 2, '€')} ({fnum(t['r_realise'], 2)} R)")
            with conteneur(f"labrow-close-{t['idx']}"):
                if not t["cloture"]:
                    colonne_a, colonne_b = st.columns([2, 1])
                    with colonne_a:
                        cle_sortie = f"lab_out_{t['idx']}"
                        _defaut(cle_sortie, float(t["entree"] or 0.0))
                        prix_sortie = st.number_input("Prix de sortie", min_value=0.0, step=0.1,
                                                      key=cle_sortie)
                    with colonne_b:
                        if st.button("Clôturer", type="primary", key=f"lab_close_{t['idx']}"):
                            if prix_sortie > 0:
                                set_cell("Trades", t["idx"], 7, "Clôturé")
                                set_cell("Trades", t["idx"], 10, f"{prix_sortie}")
                                set_cell("Trades", t["idx"], 11, str(date.today()))
                                flush()
                                st.rerun()
                            else:
                                st.warning("Indiquez un prix de sortie.")
                if st.button("Supprimer ce trade", key=f"lab_del_{t['idx']}"):
                    delete_row("Trades", t["idx"], libelle="Trade supprimé")
                    st.rerun()

    # --- Nouveau trade ------------------------------------------------------
    sous_titre("Nouvelle position")
    with conteneur("labrow-new"):
        colonne_a, colonne_b = st.columns([2, 1])
        with colonne_a:
            actif = st.selectbox("Actif", list(UNIVERS), key="lab_t_actif")
        with colonne_b:
            sens = pills("lab_t_sens", ["Achat", "Vente"], defaut="Achat", cols=2)

        colonne_1, colonne_2, colonne_3 = st.columns(3)
        with colonne_1:
            entree = st.number_input("Entrée", min_value=0.0, step=0.1, key="lab_t_entree")
        with colonne_2:
            stop = st.number_input("Stop-loss", min_value=0.0, step=0.1, key="lab_t_stop")
        with colonne_3:
            objectif = st.number_input("Objectif", min_value=0.0, step=0.1, key="lab_t_objectif")

    risque_unitaire = abs(entree - stop) if entree > 0 and stop > 0 else 0.0
    gain_unitaire = abs(objectif - entree) if entree > 0 and objectif > 0 else 0.0
    rapport = gain_unitaire / risque_unitaire if risque_unitaire else float("nan")
    budget_risque = cfg["capital"] * cfg["risque"] / 100
    taille_conseillee = budget_risque / risque_unitaire if risque_unitaire else float("nan")

    kpis([
        {"label": "Risque par unité", "valeur": fprix(risque_unitaire)},
        {"label": "Ratio rendement / risque", "valeur": fnum(rapport, 2),
         "delta": "correct" if not _nan(rapport) and rapport >= 2 else "sous votre seuil de 2",
         "delta_ton": "up" if not _nan(rapport) and rapport >= 2 else "down"},
        {"label": "Budget de risque", "valeur": fnum(budget_risque, 2, "€"),
         "aide": f"{fnum(cfg['risque'], 1)}{FINE}% de {fnum(cfg['capital'], 0, '€')}"},
        {"label": "Taille conseillée", "valeur": fnum(taille_conseillee, 4),
         "aide": "unités, pour tenir votre règle de risque"},
    ])

    with conteneur("labrow-new2"):
        colonne_a, colonne_b = st.columns([1, 2])
        with colonne_a:
            if not st.session_state.get("lab_t_taille") and not _nan(taille_conseillee):
                st.session_state["lab_t_taille"] = float(round(taille_conseillee, 4))
            _defaut("lab_t_taille", 0.0)
            taille = st.number_input("Taille retenue", min_value=0.0, step=0.0001, format="%.4f",
                                     key="lab_t_taille")
        with colonne_b:
            notes_trade = st.text_input("Pourquoi ce trade", key="lab_t_notes",
                                        placeholder="Ex : cassure du range 5 min, volume x2")

    if st.button("Enregistrer la position", type="primary", key="lab_save_trade"):
        if entree <= 0 or stop <= 0:
            st.warning("Indiquez au moins un prix d'entrée et un stop-loss.")
        elif sens == "Achat" and stop >= entree:
            st.warning("Sur un achat, le stop-loss doit être sous le prix d'entrée.")
        elif sens == "Vente" and stop <= entree:
            st.warning("Sur une vente, le stop-loss doit être au-dessus du prix d'entrée.")
        else:
            add_row("Trades", [str(date.today()), actif, sens, f"{entree}", f"{objectif}",
                               f"{stop}", "En cours", notes_trade, f"{taille}", "", ""])
            reset_after(lab_t_entree=0.0, lab_t_stop=0.0, lab_t_objectif=0.0,
                        lab_t_taille=0.0, lab_t_notes="")
            st.toast("Position enregistrée", icon="🎯")
            st.rerun()


def onglet_dca(cfg):
    st.caption("Un versement automatique, réparti entre plusieurs actifs, testé sur le passé.")

    with conteneur("labrow-dca"):
        colonne_a, colonne_b = st.columns(2)
        with colonne_a:
            _defaut("lab_dca_montant", float(cfg["dca_montant"]))
            montant = st.number_input("Versement mensuel (€)", min_value=10.0, step=10.0,
                                      key="lab_dca_montant")
        with colonne_b:
            _defaut("lab_dca_annees", 3)
            annees = st.slider("Durée du test (années)", 1, 10, key="lab_dca_annees")
        _defaut("lab_dca_actifs",
                [a for a in cfg["dca_poids"] if a in UNIVERS][:6] or ["Bitcoin"])
        choix = st.multiselect("Actifs du plan", list(UNIVERS),
                               max_selections=6, key="lab_dca_actifs")

    if not choix:
        note("Choisissez au moins un actif pour construire le plan.")
        return

    poids = {}
    with conteneur("labrow-dca-poids"):
        st.markdown("**Répartition**")
        colonnes = st.columns(min(3, len(choix)))
        for i, nom in enumerate(choix):
            with colonnes[i % len(colonnes)]:
                _defaut(f"lab_poids_{nom}",
                        int(cfg["dca_poids"].get(nom, round(100 / len(choix)))))
                poids[nom] = st.number_input(nom, min_value=0, max_value=100, step=5,
                                             key=f"lab_poids_{nom}")

    total = sum(poids.values())
    kpis([{"label": "Total réparti", "valeur": fpct(total, 0, signe=False),
           "delta": "prêt" if total == 100 else "doit faire 100 %",
           "delta_ton": "up" if total == 100 else "down"}] +
         [{"label": nom, "valeur": fnum(montant * part / 100, 2, "€"),
           "aide": f"{fnum(part, 0)}{FINE}% par mois"} for nom, part in poids.items()])

    if total != 100:
        with conteneur("labrow-dca-fix"):
            if st.button("Ramener la répartition à 100 %", key="lab_dca_norm") and total > 0:
                reset_after(**{f"lab_poids_{nom}": int(round(part / total * 100))
                               for nom, part in poids.items()})
                st.rerun()
        note("Ajustez la répartition à 100 % pour lancer le test.", "warn")
        return

    if st.button("Enregistrer ce plan", key="lab_dca_save"):
        cfg["dca_montant"] = float(montant)
        cfg["dca_poids"] = {nom: int(part) for nom, part in poids.items()}
        sauver_config(cfg)
        add_row("IA_Lab", [str(date.today()), "Plan d'investissement programmé",
                           f"{fnum(montant, 0, '€')} par mois — " +
                           ", ".join(f"{nom} {part}%" for nom, part in poids.items()),
                           "Apprentissage"])
        st.toast("Plan enregistré", icon="🧮")

    # --- Simulation historique ---------------------------------------------
    sous_titre(f"Si vous aviez commencé il y a {annees} an(s)")
    if not st.session_state.get("lab_dca_live"):
        note("La simulation télécharge plusieurs années d'historique — appuyez pour la lancer.")
        if st.button("🧮 Lancer la simulation", type="primary", key="lab_dca_go"):
            st.session_state["lab_dca_live"] = True
            st.rerun()
        return

    with st.spinner("Reconstitution de l'historique…"):
        historique, err = _mensuel(tuple(sorted(UNIVERS[n][0] for n in choix)), annees)
    if err:
        note(f"⚠️ {err}", "warn")
        return

    historique = historique.rename(columns=NOM_PAR_TICKER).dropna(how="all")
    manquants = [n for n in choix if n not in historique.columns]
    if manquants:
        note("Historique indisponible pour : " + ", ".join(manquants), "warn")
    colonnes_ok = [n for n in choix if n in historique.columns]
    if not colonnes_ok:
        note("Aucun historique exploitable sur cette durée.", "warn")
        return

    unites = {nom: 0.0 for nom in colonnes_ok}
    investi, flux, suivi = 0.0, [], []
    for horodatage, ligne in historique.iterrows():
        verse_du_mois = 0.0
        for nom in colonnes_ok:
            prix = ligne.get(nom)
            if prix is None or _nan(prix) or float(prix) <= 0:
                continue
            part = montant * poids[nom] / 100
            unites[nom] += part / float(prix)
            verse_du_mois += part
        if verse_du_mois <= 0:
            continue
        investi += verse_du_mois
        flux.append(verse_du_mois)
        valeur = sum(unites[nom] * float(ligne[nom])
                     for nom in colonnes_ok if not _nan(ligne.get(nom)))
        suivi.append((horodatage, investi, valeur))

    if not suivi:
        note("Pas assez d'historique pour simuler ce plan.", "warn")
        return

    valeur_finale = suivi[-1][2]
    plus_value = valeur_finale - investi
    performance = (valeur_finale / investi - 1) * 100 if investi else float("nan")
    kpis([
        {"label": "Total versé", "valeur": fnum(investi, 0, "€"),
         "aide": f"{len(flux)} versements"},
        {"label": "Valeur aujourd'hui", "valeur": fnum(valeur_finale, 0, "€")},
        {"label": "Plus ou moins-value", "valeur": fnum(plus_value, 0, "€"),
         "delta": fpct(performance), "delta_ton": ton(plus_value)},
        {"label": "Rendement annuel", "valeur": fpct(_tri(flux, valeur_finale) * 100, 1),
         "aide": "taux de rentabilité interne"},
    ])

    suivi_df = pd.DataFrame(
        {"Total versé": [s[1] for s in suivi], "Valeur du portefeuille": [s[2] for s in suivi]},
        index=[s[0] for s in suivi])
    courbe(suivi_df, "€", hauteur=320)

    lignes = []
    for nom in colonnes_ok:
        serie_propre = historique[nom].dropna()
        if serie_propre.empty:
            continue
        derniere = float(serie_propre.iloc[-1])
        verse = montant * poids[nom] / 100 * len(flux)
        valeur_ligne = unites[nom] * derniere
        lignes.append([nom, fnum(verse, 0, "€"), fnum(valeur_ligne, 0, "€"),
                       f"<span class='{ton(valeur_ligne - verse)}'>"
                       f"{fnum(valeur_ligne - verse, 0, '€')}</span>",
                       f"<span class='{ton(valeur_ligne - verse)}'>"
                       f"{fpct((valeur_ligne / verse - 1) * 100 if verse else float('nan'))}</span>",
                       fnum(unites[nom], 4)])
    sous_titre("Détail par actif")
    table([("Actif", "txt"), ("Versé", "num"), ("Valeur", "num"), ("Écart", "num"),
           ("Performance", "num"), ("Quantité", "num")], lignes)
    note("Simulation sur données passées, hors frais et hors fiscalité. Les performances "
         "passées ne disent rien des performances futures.", "calme")


@st.cache_data(ttl=3600, show_spinner=False)
def _mensuel(tickers, annees):
    try:
        import yfinance as yf
    except ImportError:
        return pd.DataFrame(), "Le module yfinance n'est pas installé."
    try:
        brut = yf.download(list(tickers), period=f"{annees}y", interval="1mo",
                           progress=False, auto_adjust=True, group_by="column")
    except Exception as err:
        return pd.DataFrame(), f"Historique indisponible : {str(err)[:120]}"
    if brut is None or brut.empty:
        return pd.DataFrame(), "Aucun historique renvoyé."
    if isinstance(brut.columns, pd.MultiIndex):
        try:
            cloture = brut["Close"]
        except KeyError:
            return pd.DataFrame(), "Format de données inattendu."
    else:
        if "Close" not in brut.columns:
            return pd.DataFrame(), "Format de données inattendu."
        cloture = brut[["Close"]].rename(columns={"Close": list(tickers)[0]})
    return cloture.dropna(how="all"), None


def _tri(flux, valeur_finale):
    """Taux de rentabilité interne annualisé, par dichotomie sur les flux mensuels."""
    if not flux or valeur_finale <= 0:
        return float("nan")

    def valeur_actuelle(taux):
        n = len(flux)
        sortie = -sum(f / ((1 + taux) ** i) for i, f in enumerate(flux))
        return sortie + valeur_finale / ((1 + taux) ** (n - 1))

    bas, haut = -0.9, 1.0
    try:
        if valeur_actuelle(bas) * valeur_actuelle(haut) > 0:
            return float("nan")
        for _ in range(80):
            milieu = (bas + haut) / 2
            if valeur_actuelle(bas) * valeur_actuelle(milieu) <= 0:
                haut = milieu
            else:
                bas = milieu
    except (OverflowError, ZeroDivisionError):
        return float("nan")
    mensuel = (bas + haut) / 2
    return (1 + mensuel) ** 12 - 1


def onglet_notes(cfg):
    notes_liste = notes_utilisateur()

    with conteneur("labrow-search"):
        recherche = st.text_input("Rechercher dans vos notes", key="lab_recherche",
                                  placeholder="Ex : breakout, stop, erreur…")
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
        {"label": "Affichées", "valeur": fnum(len(visibles), 0)},
        {"label": "Règles de trading", "valeur":
            fnum(len([n for n in notes_liste if n["type"] == "Règle de trading"]), 0)},
        {"label": "Post-mortem", "valeur":
            fnum(len([n for n in notes_liste if n["type"] == "Post-mortem"]), 0)},
    ])

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
    modele = st.selectbox("Partir d'un modèle", ["Page blanche"] + list(PRESETS),
                          key="lab_preset")
    if st.button("Charger ce modèle", key="lab_charger_preset") and modele != "Page blanche":
        reset_after(lab_n_sujet=modele, lab_n_contenu=PRESETS[modele],
                    lab_n_type="Règle de trading")
        st.rerun()

    sujet = st.text_input("Sujet", key="lab_n_sujet", placeholder="Ex : cassure de range en 5 min")
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

    # --- Réglages du labo ---------------------------------------------------
    with st.expander("Réglages du labo"):
        with conteneur("labrow-cfg"):
            colonne_a, colonne_b = st.columns(2)
            with colonne_a:
                _defaut("lab_cfg_capital", float(cfg["capital"]))
                capital = st.number_input("Capital de référence (€)", min_value=0.0, step=100.0,
                                          key="lab_cfg_capital")
            with colonne_b:
                _defaut("lab_cfg_risque", float(cfg["risque"]))
                risque = st.number_input("Risque par position (%)", min_value=0.1, max_value=10.0,
                                         step=0.1, key="lab_cfg_risque")
        if st.button("Enregistrer les réglages", type="primary", key="lab_cfg_save"):
            cfg["capital"] = float(capital)
            cfg["risque"] = float(risque)
            sauver_config(cfg)
            st.toast("Réglages enregistrés", icon="⚙️")
            st.rerun()
        if st.button("Recharger les cours et vider le cache", key="lab_cfg_cache"):
            st.cache_data.clear()
            st.session_state.pop("lab_cockpit_live", None)
            st.session_state.pop("lab_dca_live", None)
            st.rerun()
        st.caption(f"Labo version {VERSION_LABO} · les réglages sont partagés "
                   f"entre vous deux via Google Sheets.")

# ==========================================================
# 7. POINT D'ENTRÉE
# ==========================================================
ROUTES = {
    ONGLETS[0]: onglet_cockpit,
    ONGLETS[1]: onglet_marches,
    ONGLETS[2]: onglet_analyse,
    ONGLETS[3]: onglet_journal,
    ONGLETS[4]: onglet_dca,
    ONGLETS[5]: onglet_notes,
}


REQUIS = ["rows", "add_row", "delete_row", "set_cell", "pad", "to_float",
          "parse_date", "conteneur", "titre", "vide", "pills"]


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
        ROUTES.get(onglet, onglet_cockpit)(cfg)
    except Exception as err:
        # Une erreur dans un onglet ne doit jamais laisser une page blanche :
        # on affiche le message pour pouvoir corriger.
        st.error(f"Le labo a rencontré une erreur sur « {onglet} » : {err}")
        with st.expander("Détail technique"):
            st.code(traceback.format_exc())
        if st.button("Réinitialiser le labo", key="lab_panic"):
            for cle in [c for c in list(st.session_state) if str(c).startswith("lab_")]:
                st.session_state.pop(cle, None)
            st.cache_data.clear()
            st.rerun()
