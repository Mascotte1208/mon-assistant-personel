"""
Labo IA & Marchés — module autonome pour « Notre Assistant ».

Trois onglets : les cours des marchés, l'analyse d'un actif, et un carnet de
notes. Rien d'autre : ni journal de positions, ni gestion du risque, ni
simulation d'investissement.

Branchement dans l'application principale, sans dépendance inverse :

    elif page_cle == "ialab" and st.session_state.get("mode_ia"):
        import labo_ia
        labo_ia.render({
            "rows": rows, "add_row": add_row, "delete_row": delete_row,
            "set_cell": set_cell, "pad": pad, "to_float": to_float,
            "parse_date": parse_date, "conteneur": conteneur, "titre": titre,
            "vide": vide, "pills": pills, "reset_after": reset_after,
            "vider_file": vider_file,
        })

Le module n'écrit que dans la feuille « IA_Lab », qui existe déjà avec ses
quatre colonnes (Date, Sujet, Contenu, Type). Aucune migration nécessaire.

Sections :
  1. Constantes         4. Données de marché
  2. Accès à l'app      5. Notes & réglages
  3. Mise en forme      6. Onglets · 7. render()
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
VERSION_LABO = "4.0"
CFG_SUJET = "Paramètres du labo"

ONGLETS = ["📈 Marchés", "🔬 Analyse", "📚 Notes"]

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

TYPES_NOTE = ["Note", "À retenir", "Idée", "Suivi"]

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
    # L'app expose add_row(feuille, ligne) : deux arguments, pas davantage.
    return _f("add_row")(feuille, ligne)


def delete_row(feuille, index, libelle="Élément supprimé"):
    return _f("delete_row")(feuille, index, True, libelle)


def set_cell(feuille, index, colonne, valeur):
    # L'app expose set_cell(feuille, index, colonne, valeur, annulable, libelle).
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
    """Applique des valeurs au prochain rerun.

    C'est la seule façon sûre de modifier une clé de widget déjà instanciée :
    Streamlit refuse l'affectation directe dans ce cas.
    """
    fonction = _CTX.get("reset_after")
    if fonction:
        fonction(**champs)
        return True
    return False


def _defaut(cle, valeur):
    """Valeur initiale d'un widget, posée avant sa création.

    Évite le mélange `value=` + `key=`, source d'avertissements et de valeurs
    qui ne se rafraîchissent pas.
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


CSS = """
<style>
/* Le labo respire plus large que le reste de l'app, mais seulement sur écran :
   sur téléphone on garde la mise en page de l'application principale. */
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
    return {NOM_PAR_TICKER.get(t, t): df for t, df in paquets.items()}, barres_an, err


def moyenne_mobile(serie, n):
    return serie.rolling(n).mean()


def volatilite(serie, barres_an):
    """Amplitude typique des variations, ramenée à une échelle annuelle."""
    variations = serie.pct_change().dropna()
    if len(variations) < 3:
        return float("nan")
    return float(variations.std() * math.sqrt(barres_an) * 100)


def profil(df, barres_an):
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
        "repli": float((cloture / cloture.cummax() - 1).min() * 100),
    }
    amplitude = p["haut"] - p["bas"]
    # Position du dernier cours dans le couloir de la période, en pourcentage.
    p["position"] = ((dernier - p["bas"]) / amplitude * 100) if amplitude else float("nan")
    p["mm20"] = float(moyenne_mobile(cloture, 20).iloc[-1]) if len(cloture) >= 20 else float("nan")
    p["ecart20"] = (dernier / p["mm20"] - 1) * 100 if not _nan(p["mm20"]) else float("nan")
    return p


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
        st.plotly_chart(_mise_en_page(fig, hauteur, titre_y), use_container_width=True)
    except Exception:
        st.line_chart(df)

# ==========================================================
# 5. NOTES & RÉGLAGES
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
        pass  # feuille absente ou illisible : on démarre sur les valeurs par défaut

    base["watchlist"] = [n for n in base.get("watchlist", []) if n in UNIVERS][:6]
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
        add_row("IA_Lab", [str(date.today()), CFG_SUJET, charge, "Config"])
        for i, ligne in rows("IA_Lab"):          # on retient l'index tout de suite
            _, sujet, _, type_ = pad(ligne, 4)
            if type_ == "Config" and sujet == CFG_SUJET:
                st.session_state["lab_cfg_idx"] = i
                break
    except Exception as err:
        st.warning(f"Réglages non enregistrés : {str(err)[:120]}")


def notes_utilisateur():
    """Toutes les notes, sauf la ligne technique de configuration."""
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
                       "contenu": contenu, "type": type_ or TYPES_NOTE[0]})
    return sortie

# ==========================================================
# 6. ONGLETS
# ==========================================================
def _selection(cle_widget, cfg, maxi=6):
    """Sélecteur d'actifs qui n'écrit la configuration qu'à un vrai changement."""
    _defaut(cle_widget, [n for n in cfg["watchlist"] if n in UNIVERS][:maxi] or ["Bitcoin", "Or"])
    choix = st.multiselect("Actifs suivis", list(UNIVERS), max_selections=maxi, key=cle_widget)

    deja = st.session_state.get("lab_watch_saved")
    if deja is None:
        deja = tuple(cfg["watchlist"])
    if choix and tuple(choix) != tuple(deja):
        st.session_state["lab_watch_saved"] = tuple(choix)
        cfg["watchlist"] = list(choix)
        sauver_config(cfg)
    return choix


def onglet_marches(cfg):
    with conteneur("labrow-sel"):
        choix = _selection("lab_cmp", cfg)
        colonne_a, colonne_b = st.columns(2)
        with colonne_a:
            periode = pills("lab_periode", list(PERIODES), defaut="5J", cols=3)
        with colonne_b:
            base = pills("lab_base", ["Base 100", "Prix réels"], defaut="Base 100", cols=2)

    if not choix:
        note("Sélectionnez au moins un actif pour afficher les cours.")
        return

    # Chargement à la demande : sur téléphone, télécharger plusieurs séries
    # avant le premier affichage laissait la page sur un spinner interminable.
    if not st.session_state.get("lab_live"):
        note("Les cours ne sont pas encore chargés — appuyez pour interroger les marchés.")
        if st.button("📡 Charger les cours", type="primary", key="lab_go"):
            st.session_state["lab_live"] = True
            st.rerun()
        return

    with st.spinner("Lecture des marchés…"):
        donnees, barres_an, err = marche(choix, periode)
    if err:
        note(f"⚠️ {err}", "warn")
        if st.button("Réessayer", key="lab_retry"):
            st.cache_data.clear()
            st.rerun()
        return

    valides = {nom: p for nom, p in ((n, profil(donnees.get(n), barres_an)) for n in choix) if p}
    if not valides:
        note("Aucune donnée exploitable sur cette période.", "warn")
        return

    kpis([{"label": nom, "valeur": fprix(p["dernier"]),
           "delta": fpct(p["var"]), "delta_ton": ton(p["var"])}
          for nom, p in valides.items()], largeur=160)

    sous_titre("Les cours sur la période")
    table([("Actif", "txt"), ("Dernier", "num"), ("Variation", "num"), ("Plus haut", "num"),
           ("Plus bas", "num"), ("Moyenne", "num"), ("Amplitude", "num")],
          [[nom, fprix(p["dernier"]),
            f"<span class='{ton(p['var'])}'>{fpct(p['var'])}</span>",
            fprix(p["haut"]), fprix(p["bas"]), fprix(p["moyenne"]),
            fpct((p["haut"] / p["bas"] - 1) * 100 if p["bas"] else float("nan"), 1, signe=False)]
           for nom, p in valides.items()])
    st.caption("Le tableau défile horizontalement : aucune valeur n'est tronquée.")

    sous_titre("Évolution comparée")
    series = pd.DataFrame({nom: p["serie"] for nom, p in valides.items()})
    if base == "Base 100":
        series = series.apply(lambda c: c / c.dropna().iloc[0] * 100 if not c.dropna().empty else c)
        courbe(series, "Base 100 au départ de la période")
        st.caption("Chaque actif part de 100 : les courbes se comparent malgré des prix "
                   "très différents.")
    else:
        courbe(series, "Prix, dans la devise de cotation")

    if len(valides) >= 2 and len(series.dropna()) > 5:
        sous_titre("Est-ce que ça bouge ensemble ?")
        matrice = series.pct_change().corr()
        colonnes = [("", "txt")] + [(nom, "num") for nom in matrice.columns]
        lignes = []
        for nom in matrice.index:
            cellules = [f"<b>{nom}</b>"]
            for autre in matrice.columns:
                valeur = matrice.loc[nom, autre]
                classe = "up" if valeur > 0.5 else ("down" if valeur < -0.2 else "flat")
                cellules.append(f"<span class='{classe}'>{fnum(valeur, 2)}</span>")
            lignes.append(cellules)
        table(colonnes, lignes)
        st.caption("1,00 = les deux actifs montent et descendent ensemble · 0,00 = aucun lien · "
                   "négatif = quand l'un monte, l'autre baisse.")

    sous_titre("Garder une trace")
    with conteneur("labrow-note-marche"):
        commentaire = st.text_area("Ce que vous retenez de cette séance",
                                   key="lab_note_marche", height=90,
                                   placeholder="Ex : l'or tient pendant que le Nasdaq recule…")
        if st.button("Enregistrer dans mes notes", type="primary", key="lab_save_marche"):
            if commentaire.strip():
                resume = " · ".join(f"{nom} {fpct(p['var'])}" for nom, p in valides.items())
                add_row("IA_Lab", [str(date.today()), f"Marchés ({periode})",
                                   f"{resume}\n\n{commentaire.strip()}", "Suivi"])
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
            periode = pills("lab_ana_periode", list(PERIODES), defaut="1M", cols=3)

    if not st.session_state.get("lab_live"):
        note("Les cours ne sont pas encore chargés — appuyez pour interroger les marchés.")
        if st.button("📡 Charger les cours", type="primary", key="lab_go_ana"):
            st.session_state["lab_live"] = True
            st.rerun()
        return

    with st.spinner("Lecture des marchés…"):
        donnees, barres_an, err = marche([actif], periode)
    if err:
        note(f"⚠️ {err}", "warn")
        return
    df = donnees.get(actif)
    p = profil(df, barres_an)
    if not p:
        note("Pas assez de données pour cet actif sur cette période.", "warn")
        return

    cloture = p["serie"]
    kpis([
        {"label": "Dernier cours", "valeur": fprix(p["dernier"]),
         "delta": fpct(p["var"]), "delta_ton": ton(p["var"])},
        {"label": "Plus haut", "valeur": fprix(p["haut"]),
         "aide": "sommet de la période"},
        {"label": "Plus bas", "valeur": fprix(p["bas"]),
         "aide": "creux de la période"},
        {"label": "Dans le couloir", "valeur": fpct(p["position"], 0, signe=False),
         "aide": "0 % = au plus bas · 100 % = au plus haut"},
        {"label": "Écart à la moyenne 20", "valeur": fpct(p["ecart20"], 2),
         "delta_ton": ton(p["ecart20"])},
        {"label": "Agitation annualisée", "valeur": fpct(p["vol"], 1, signe=False),
         "aide": "amplitude typique des variations"},
    ])

    go = _plotly()
    trace_ok = False
    if go is not None:
        try:
            from plotly.subplots import make_subplots
            avec_volume = "Volume" in df.columns and float(df["Volume"].fillna(0).sum()) > 0
            fig = make_subplots(rows=2 if avec_volume else 1, cols=1, shared_xaxes=True,
                                row_heights=[0.74, 0.26] if avec_volume else [1.0],
                                vertical_spacing=0.05)

            if {"Open", "High", "Low", "Close"}.issubset(df.columns):
                fig.add_trace(go.Candlestick(
                    x=df.index, open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
                    name="Cours", increasing_line_color="#15803d",
                    decreasing_line_color="#b91c1c", showlegend=False), row=1, col=1)
            else:
                fig.add_trace(go.Scatter(x=cloture.index, y=cloture, name="Cours",
                                         line=dict(color="#be185d", width=2.4)), row=1, col=1)

            if len(cloture) >= 20:
                fig.add_trace(go.Scatter(x=cloture.index, y=moyenne_mobile(cloture, 20),
                                         name="Moyenne 20",
                                         line=dict(color="#be185d", width=2)), row=1, col=1)
            if len(cloture) >= 50:
                fig.add_trace(go.Scatter(x=cloture.index, y=moyenne_mobile(cloture, 50),
                                         name="Moyenne 50",
                                         line=dict(color="#7c3aed", width=2, dash="dot")),
                              row=1, col=1)

            if avec_volume:
                fig.add_trace(go.Bar(x=df.index, y=df["Volume"], name="Volume",
                                     marker_color="#f472b6", showlegend=False), row=2, col=1)
                fig.update_yaxes(title_text="Volume", row=2, col=1)

            fig.update_xaxes(rangeslider_visible=False)
            st.plotly_chart(_mise_en_page(fig, 520 if avec_volume else 400, "Prix"),
                            use_container_width=True)
            trace_ok = True
        except Exception:
            trace_ok = False
    if not trace_ok:
        courbe(pd.DataFrame({actif: cloture}), "Prix", hauteur=380)

    sous_titre("Repères de la période")
    reperes = [
        ("Plus haut", p["haut"]),
        ("Moyenne des cours", p["moyenne"]),
        ("Moyenne mobile 20", p["mm20"]),
        ("Premier cours de la période", p["premier"]),
        ("Plus bas", p["bas"]),
    ]
    dernier = p["dernier"]
    table([("Repère", "txt"), ("Cours", "num"), ("Écart au dernier", "num")],
          [[libelle, fprix(valeur),
            f"<span class='{ton(dernier - valeur)}'>{fpct((dernier / valeur - 1) * 100, 2)}</span>"
            if not _nan(valeur) and valeur else "—"]
           for libelle, valeur in reperes])

    note("Ces chiffres décrivent des cours passés. Ils ne prédisent rien et ne constituent "
         "pas un conseil en investissement.", "calme")

    sous_titre("Noter cette observation")
    with conteneur("labrow-note-ana"):
        obs = st.text_area(f"Ce que vous observez sur {actif}", key="lab_note_ana", height=90,
                           placeholder="Ex : le cours reste au-dessus de sa moyenne 20 depuis…")
        if st.button("Enregistrer dans mes notes", type="primary", key="lab_save_ana"):
            if obs.strip():
                entete = (f"{actif} · {fprix(p['dernier'])} ({fpct(p['var'])}) "
                          f"sur {periode}")
                add_row("IA_Lab", [str(date.today()), f"Observation — {actif}",
                                   f"{entete}\n\n{obs.strip()}", "Suivi"])
                reset_after(lab_note_ana="")
                st.toast("Note enregistrée", icon="✅")
                st.rerun()
            else:
                st.warning("Écrivez d'abord votre observation.")


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
    ], largeur=170)

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
        if st.button("Recharger les cours et vider le cache", key="lab_cfg_cache"):
            st.cache_data.clear()
            st.session_state.pop("lab_live", None)
            st.rerun()
        st.caption(f"Labo version {VERSION_LABO}")

# ==========================================================
# 7. POINT D'ENTRÉE
# ==========================================================
ROUTES = {
    ONGLETS[0]: onglet_marches,
    ONGLETS[1]: onglet_analyse,
    ONGLETS[2]: onglet_notes,
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
