# ==========================================================
# 8d. LABO IA & MARCHÉS — module externe labo_ia.py
# ==========================================================
elif page_cle == "ialab" and st.session_state.get("mode_ia"):
    try:
        import labo_ia
    except Exception as err:
        st.error(f"Module labo_ia.py introuvable : {err}")
    else:
        labo_ia.render({
            "rows": rows, "add_row": add_row, "delete_row": delete_row,
            "set_cell": set_cell, "pad": pad, "to_float": to_float,
            "parse_date": parse_date, "conteneur": conteneur, "titre": titre,
            "vide": vide, "pills": pills, "reset_after": reset_after,
            "vider_file": vider_file,
        })
