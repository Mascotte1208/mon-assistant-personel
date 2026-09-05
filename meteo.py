# ==========================================================
# Meteo - module autonome pour "Notre Assistant" (Bruxelles)
# ==========================================================
from datetime import datetime
import requests
import streamlit as st

VERSION_METEO = "2.5"

# Fixé directement sur Bruxelles
LATITUDE, LONGITUDE = 50.8503, 4.3517
VILLE_NOM = "Bruxelles"

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

CSS_METEO = """
<style>
/* Réduction drastique de l'espace tout en haut de la page et du bloc météo */
.block-container {
  padding-top: 0.5rem !important;
}
[data-testid="stVerticalBlock"]:has(.meteo-now) {
  margin-top: -20px !important;
}

.meteo-top{display:flex; justify-content:space-between; align-items:center; margin-bottom:2px;}
.meteo-now{display:flex; align-items:center; gap:16px; padding:0 0 8px;}
.meteo-now .ic{font-size:40px; line-height:1;}
.meteo-now .t{font-size:28px; font-weight:800; color:var(--accent-fonce,#8C1444); line-height:1;
  font-variant-numeric:tabular-nums; letter-spacing:-.02em;}
.meteo-now .d{font-size:13.5px; font-weight:700; color:var(--encre-2,#6E4A5B); margin-top:3px;}
.meteo-now .s{font-size:11.5px; font-weight:600; color:var(--gris,#9B7F8C); margin-top:2px;}

.meteo-jours{display:grid; grid-template-columns:repeat(4,1fr); gap:6px;
  padding-top:8px; border-top:1.5px solid var(--trait,#F3C7DA);}
.meteo-jour{text-align:center; padding:5px 4px; background:var(--papier-2, #FAD9E7); border-radius:10px; border:1px solid var(--trait,#F3C7DA);}
.meteo-jour .j{font-size:10.5px; font-weight:700; color:var(--encre-2); text-transform:uppercase;}
.meteo-jour .e{font-size:16px; line-height:1.2;}
.meteo-jour .m{font-size:11.5px; font-weight:700; color:var(--encre,#3A1A28);
  font-variant-numeric:tabular-nums; white-space:nowrap;}
.meteo-jour .m .min{color:var(--gris,#9B7F8C); font-weight:500;}

.meteo-conseil{background:#FDF4EA; border:1px solid #EBD3B4; color:var(--ambre,#A65B12);
  border-radius:8px; padding:5px 8px; font-size:11.5px; font-weight:600; margin-top:6px;}
</style>
"""

def _libelle(code):
    return CODES.get(int(code) if code is not None else -1, ("Temps variable", "🌡️"))

def _t(valeur):
    try:
        return f"{round(float(valeur))}°"
    except (TypeError, ValueError):
        return "—"

@st.cache_data(ttl=1800, show_spinner=False)
def previsions():
    try:
        reponse = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude": LATITUDE,
                "longitude": LONGITUDE,
                "current": "temperature_2m,apparent_temperature,weather_code,wind_speed_10m",
                "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
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
    st.markdown(CSS_METEO, unsafe_allow_html=True)

    with conteneur("carte-meteo"):
        # On garde uniquement l'en-tête sans le sélecteur de ville
        entete_bloc("🌤️ Météo")

        donnees, err = previsions()
        if err or not donnees:
            st.markdown("<div class='today-none'>Météo indisponible pour le moment.</div>", unsafe_allow_html=True)
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
            f"<div class='d'>{VILLE_NOM} · {texte}</div>"
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
            libelle = "Auj." if i == 0 else JOURS_COURTS[jour.weekday()][:3].capitalize()
            _, ico = _libelle((jours.get("weather_code") or [None])[i] if i < len(jours.get("weather_code", [])) else None)
            haut = (jours.get("temperature_2m_max") or [None])[i] if i < len(jours.get("temperature_2m_max", [])) else None
            bas = (jours.get("temperature_2m_min") or [None])[i] if i < len(jours.get("temperature_2m_min", [])) else None
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
            if pluie_du_jour is not None and float(pluie_du_jour) >= 30:
                st.markdown(
                    f"<div class='meteo-conseil'>☂️ {round(float(pluie_du_jour))} % de risque de pluie</div>",
                    unsafe_allow_html=True,
                )
        except (TypeError, ValueError):
            pass
