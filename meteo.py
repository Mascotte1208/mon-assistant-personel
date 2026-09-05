# ==========================================================
# Meteo - module autonome pour "Notre Assistant"
# ==========================================================
# Affiche la meteo du jour et les trois jours suivants, dans une
# carte posee sur la page d'accueil.
#
# Source : Open-Meteo (open-meteo.com), gratuit, sans cle d'API.
#
# Branchement dans l'application principale, page d'accueil :
#
#     import meteo
#     meteo.carte(conteneur, entete_bloc)
#
# N'ecrit rien dans Google Sheets. Si le reseau ne repond pas,
# la carte affiche un message et le reste de la page continue.
# ==========================================================

from datetime import datetime

import requests
import streamlit as st

VERSION_METEO = "2.0"

# Ajoutez vos villes ici : "Nom": (latitude, longitude)
VILLES = {
    "Bruxelles": (50.8503, 4.3517),
    "Anvers":    (51.2194, 4.4025),
    "Gand":      (51.0543, 3.7174),
    "Liège":     (50.6326, 5.5797),
    "Namur":     (50.4674, 4.8720),
    "Lille":     (50.6292, 3.0573),
    "Paris":     (48.8566, 2.3522),
}
VILLE_DEFAUT = "Bruxelles"

# Codes météo de l'organisation météorologique mondiale.
CODES = {
    0:  ("Ciel dégagé", "☀️"),
    1:  ("Peu nuageux", "🌤️"),
    2:  ("Partiellement nuageux", "⛅"),
    3:  ("Couvert", "☁️"),
    45: ("Brouillard", "🌫️"),
    48: ("Brouillard givrant", "🌫️"),
    51: ("Bruine légère", "🌦️"),
    53: ("Bruine", "🌦️"),
    55: ("Bruine dense", "🌦️"),
    56: ("Bruine verglaçante", "🌧️"),
    57: ("Bruine verglaçante", "🌧️"),
    61: ("Pluie faible", "🌦️"),
    63: ("Pluie", "🌧️"),
    65: ("Forte pluie", "🌧️"),
    66: ("Pluie verglaçante", "🌧️"),
    67: ("Pluie verglaçante", "🌧️"),
    71: ("Neige faible", "🌨️"),
    73: ("Neige", "🌨️"),
    75: ("Fortes chutes de neige", "❄️"),
    77: ("Grains de neige", "🌨️"),
    80: ("Averses", "🌦️"),
    81: ("Averses", "🌧️"),
    82: ("Violentes averses", "⛈️"),
    85: ("Averses de neige", "🌨️"),
    86: ("Averses de neige", "🌨️"),
    95: ("Orage", "⛈️"),
    96: ("Orage et grêle", "⛈️"),
    99: ("Orage et grêle", "⛈️"),
}

JOURS_COURTS = ["lundi", "mardi", "mercredi", "jeudi", "vendredi", "samedi", "dimanche"]

CSS = """
<style>
.meteo-now{display:flex; align-items:center; gap:16px; padding:2px 0 14px;}
.meteo-now .ic{font-size:40px; line-height:1;}
.meteo-now .t{font-size:32px; font-weight:700; color:var(--encre,#241B22); line-height:1;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em;}
.meteo-now .d{font-size:14px; font-weight:600; color:var(--encre-2,#5C4F55); margin-top:4px;}
.meteo-now .s{font-size:12px; font-weight:500; color:var(--gris,#8A7C82); margin-top:2px;}
.meteo-jours{display:grid; grid-template-columns:repeat(auto-fit,minmax(72px,1fr)); gap:6px;
  padding-top:12px; border-top:1px solid var(--trait,#ECE0E5);}
.meteo-jour{text-align:center; padding:6px 4px;}
.meteo-jour .j{font-size:11px; font-weight:600; color:var(--gris,#8A7C82);}
.meteo-jour .e{font-size:20px; line-height:1.5;}
.meteo-jour .m{font-size:12.5px; font-weight:700; color:var(--encre,#241B22);
  font-variant-numeric:tabular-nums; white-space:nowrap;}
.meteo-jour .m .min{color:var(--gris,#8A7C82); font-weight:500;}
.meteo-conseil{background:#FDF4EA; border:1px solid #EBD3B4; color:var(--ambre,#A65B12);
  border-radius:12px; padding:10px 13px; font-size:12.5px; font-weight:600; margin-top:12px;}
</style>
"""


def _libelle(code):
    return CODES.get(int(code) if code is not None else -1, ("Temps variable", "🌡️"))


def _t(valeur):
    """Température arrondie, sans décimale inutile."""
    try:
        return f"{round(float(valeur))}°"
    except (TypeError, ValueError):
        return "—"


@st.cache_data(ttl=1800, show_spinner=False)
def previsions(latitude, longitude):
    """Renvoie (données, erreur). Rafraîchi toutes les 30 minutes."""
    try:
        reponse = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": ("weather_code,temperature_2m_max,temperature_2m_min,"
                          "precipitation_probability_max"),
                "timezone": "auto",
                "forecast_days": 4,
            },
            timeout=8,
        )
        reponse.raise_for_status()
        return reponse.json(), None
    except Exception as err:
        return None, str(err)[:120]


def carte(conteneur, entete_bloc):
    """Dessine la carte météo. Ne lève jamais : au pire, elle s'excuse."""
    st.markdown(CSS, unsafe_allow_html=True)

    if "meteo_ville" not in st.session_state:
        st.session_state["meteo_ville"] = VILLE_DEFAUT
    ville = st.session_state["meteo_ville"]
    if ville not in VILLES:
        ville = VILLE_DEFAUT

    with conteneur("carte-meteo"):
        entete_bloc(f"🌤️ Météo · {ville}")

        latitude, longitude = VILLES[ville]
        donnees, err = previsions(latitude, longitude)
        if err or not donnees:
            st.markdown("<div class='today-none'>Météo indisponible pour le moment.</div>",
                        unsafe_allow_html=True)
            if st.button("Réessayer", key="meteo_retry"):
                previsions.clear()
                st.rerun()
            return

        actuel = donnees.get("current", {}) or {}
        texte, emoji = _libelle(actuel.get("weather_code"))
        ressenti = _t(actuel.get("apparent_temperature"))
        vent = actuel.get("wind_speed_10m")
        vent_txt = f" · vent {round(float(vent))} km/h" if vent is not None else ""

        st.markdown(
            f"<div class='meteo-now'><div class='ic'>{emoji}</div><div>"
            f"<div class='t'>{_t(actuel.get('temperature_2m'))}</div>"
            f"<div class='d'>{texte}</div>"
            f"<div class='s'>ressenti {ressenti}{vent_txt}</div>"
            f"</div></div>",
            unsafe_allow_html=True,
        )

        jours = donnees.get("daily", {}) or {}
        dates = jours.get("time", []) or []
        blocs, pluie_du_jour = [], None
        for i, iso in enumerate(dates[:4]):
            try:
                jour = datetime.strptime(iso, "%Y-%m-%d").date()
            except ValueError:
                continue
            libelle = "aujourd'hui" if i == 0 else JOURS_COURTS[jour.weekday()][:3]
            _, ico = _libelle((jours.get("weather_code") or [None])[i]
                              if i < len(jours.get("weather_code", [])) else None)
            haut = (jours.get("temperature_2m_max") or [None])[i] \
                if i < len(jours.get("temperature_2m_max", [])) else None
            bas = (jours.get("temperature_2m_min") or [None])[i] \
                if i < len(jours.get("temperature_2m_min", [])) else None
            if i == 0:
                proba = jours.get("precipitation_probability_max") or []
                pluie_du_jour = proba[0] if proba else None
            blocs.append(
                f"<div class='meteo-jour'><div class='j'>{libelle}</div>"
                f"<div class='e'>{ico}</div>"
                f"<div class='m'>{_t(haut)} <span class='min'>{_t(bas)}</span></div></div>"
            )
        if blocs:
            st.markdown(f"<div class='meteo-jours'>{''.join(blocs)}</div>", unsafe_allow_html=True)

        try:
            if pluie_du_jour is not None and float(pluie_du_jour) >= 50:
                st.markdown(
                    f"<div class='meteo-conseil'>☂️ {round(float(pluie_du_jour))} % de risque "
                    f"de pluie aujourd'hui — prenez un parapluie.</div>",
                    unsafe_allow_html=True,
                )
        except (TypeError, ValueError):
            pass

        st.selectbox("Ville", list(VILLES), key="meteo_ville",
                     label_visibility="collapsed")
