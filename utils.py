import re
import streamlit as st

OPZIONI_CRITICO = ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)", "Crit (2 Hits)"]
OPZIONI_ANTI = ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE", "BEAST", "CHARGE"]
OPZIONI_DADI = ["---", "1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "D3", "D3+1", "D6", "2D3", "2D6"]
OPZIONI_HW = ["---", 2, 3, 4, 5, 6]

def estrai_intero_sicuro(valore, default=0):
    if isinstance(valore, (int, float)):
        return int(valore)
    if isinstance(valore, str):
        match = re.search(r"\d+", valore)
        if match:
            return int(match.group(0))
    return default

def estrai_valore_keyword(keywords, prefisso):
    if not keywords:
        return None
    for kw in keywords:
        if str(kw).lower().startswith(prefisso.lower()):
            return str(kw)
    return None

def estrai_livello_potere(keywords, prefisso):
    kw_str = estrai_valore_keyword(keywords, prefisso)
    if not kw_str:
        return 0
    match = re.search(r"\((\d+)\)", kw_str)
    if match:
        return int(match.group(1))
    return 1

def analizza_testo_copiato_robusto(testo):
    armi_estratte = []
    pattern_stat = r'(?:(\d+\")\s+)?((?:\d+|[1-9]?D\d+(?:\+\d+)?|D\d+))\s+(\d)\+\s+(\d)\+\s+(\d|---|0|-)\s+((?:\d+|[1-9]?D\d+(?:\+\d+)?|D\d+))$'
    header_words = {"ranged", "melee", "missile", "weapons", "weapon", "rng", "atk", "hit", "wnd", "rnd", "dmg", "damage", "attacks"}

    linee = testo.split('\n')
    nome_temporaneo = ""

    for linea in linee:
        linea_pulita = linea.strip().replace('\t', ' ')
        linea_pulita = re.sub(r'\s+', ' ', linea_pulita)

        if not linea_pulita:
            continue

        words_in_line = set(re.findall(r'[a-zA-Z]+', linea_pulita.lower()))
        if words_in_line and words_in_line.issubset(header_words):
            continue

        match = re.search(pattern_stat, linea_pulita)
        if match:
            testo_prima = linea_pulita[:match.start()].strip()
            gittata = match.group(1)
            atk = match.group(2)
            hit = int(match.group(3))
            wnd = int(match.group(4))
            rend = 0 if match.group(5) in ["---", "-"] else int(match.group(5))
            dmg = match.group(6)

            testo_combinato = f"{nome_temporaneo} {testo_prima}".strip()
            tc_upper = testo_combinato.upper()

            crit = "Nessuno"
            if "CRIT (MORTAL)" in tc_upper: crit = "Crit (Mortal)"
            elif "CRIT (AUTO-WOUND)" in tc_upper: crit = "Crit (Auto-wound)"
            elif "CRIT (2 HITS)" in tc_upper: crit = "Crit (2 Hits)"

            anti = "Nessuno"
            anti_charge_flag = False
            if "ANTI-CHARGE" in tc_upper:
                anti = "CHARGE"
                anti_charge_flag = True
            elif "ANTI-HERO" in tc_upper: anti = "HERO"
            elif "ANTI-INFANTRY" in tc_upper: anti = "INFANTRY"
            elif "ANTI-MONSTER" in tc_upper: anti = "MONSTER"
            elif "ANTI-CAVALRY" in tc_upper: anti = "CAVALRY"
            elif "ANTI-WAR MACHINE" in tc_upper: anti = "WAR MACHINE"
            elif "ANTI-BEAST" in tc_upper: anti = "BEAST"

            charge_dmg_flag = bool(re.search(r'CHARGE\s*\(\+1\s*DAMAGE\)', tc_upper))
            companion_flag = "COMPANION" in tc_upper

            nome_pulito = nome_temporaneo if nome_temporaneo else testo_prima
            tags_da_rimuovere = [
                "Crit (Auto-wound)", "Crit (Mortal)", "Crit (2 Hits)", "Shoot in Combat",
                "Anti-HERO", "Anti-INFANTRY", "Anti-MONSTER", "Anti-CAVALRY",
                "Anti-WAR MACHINE", "Anti-BEAST", "Anti-charge", "Charge (+1 Damage)", "Companion"
            ]
            for tag in tags_da_rimuovere:
                nome_pulito = re.sub(r',?\s*' + re.escape(tag), '', nome_pulito, flags=re.IGNORECASE)
            nome_pulito = re.sub(r'\(\+1\s*Rend\)', '', nome_pulito, flags=re.IGNORECASE)

            nome_pulito = nome_pulito.strip(" ,-")
            if not nome_pulito:
                nome_pulito = "Arma"

            ranged = True if gittata else False
            gittata_str = gittata if gittata else "Melee"

            armi_estratte.append({
                "nome": nome_pulito, "attiva": True, "ranged": ranged, "range": gittata_str,
                "atk": str(atk), "hit": hit, "wnd": wnd, "rend": rend, "dmg": str(dmg),
                "crit_type": crit, "anti_target": anti,
                "charge_dmg": charge_dmg_flag, "anti_charge": anti_charge_flag, "companion": companion_flag
            })
            nome_temporaneo = ""
        else:
            nome_temporaneo = (nome_temporaneo + " " + linea_pulita).strip()

    return armi_estratte

# ==========================================
# 1. TOAST AUTO-SCOMPARENTE (2.5 SECONDI)
# ==========================================
def mostra_toast_rapido(messaggio, icona="✅"):
    """Salva il messaggio nello stato per mostrarlo con auto-dissolvenza garantita dopo st.rerun()."""
    st.session_state["_matt_toast_msg"] = (messaggio, icona)

def render_toast_temporizzato():
    """Da chiamare in app.py: mostra il pop-up e lo fa sparire da solo dopo 2.5 secondi via CSS."""
    if "_matt_toast_msg" in st.session_state and st.session_state["_matt_toast_msg"]:
        msg, ico = st.session_state.pop("_matt_toast_msg")
        st.markdown(f"""
        <style>
            @keyframes mattToastFade {{
                0%   {{ opacity: 0; transform: translateY(20px); }}
                12%  {{ opacity: 1; transform: translateY(0); }}
                82%  {{ opacity: 1; transform: translateY(0); }}
                100% {{ opacity: 0; transform: translateY(-15px); visibility: hidden; }}
            }}
            .matt-auto-toast {{
                position: fixed;
                bottom: 28px;
                right: 28px;
                z-index: 999999;
                background: linear-gradient(135deg, #24190f 0%, #140d08 100%);
                color: #f7d57f;
                border: 2px solid #d4af37;
                border-radius: 6px 14px 6px 14px;
                padding: 13px 22px;
                font-family: 'Cinzel', serif;
                font-size: 0.96rem;
                font-weight: 700;
                box-shadow: 0 8px 25px rgba(0,0,0,0.9), 0 0 15px rgba(212, 175, 55, 0.35);
                animation: mattToastFade 2.6s ease-in-out forwards;
                pointer-events: none;
            }}
        </style>
        <div class="matt-auto-toast">{ico} &nbsp; {msg}</div>
        """, unsafe_allow_html=True)


# ==========================================
# 2. SELETTORI FILTRO PER FAZIONE (UNITÀ E TRATTI/ARTEFATTI)
# ==========================================
def filtra_unita_per_fazione(db_unita, lista_chiavi_ordinate, key_prefix, label_fazione="Filtra per Fazione", default_fazione="Tutte"):
    """Mostra un selettore fazione e restituisce solo le unità di quella fazione."""
    fazioni = sorted(list({
        db_unita.get(k, {}).get("fazione", k.split(": ")[0] if ": " in k else "Altro")
        for k in lista_chiavi_ordinate if k in db_unita
    }))
    opzioni_faz = ["Tutte"] + [f for f in fazioni if f and f != "---"]
    idx_def = opzioni_faz.index(default_fazione) if default_fazione in opzioni_faz else 0
    
    faz_scelta = st.selectbox(label_fazione, opzioni_faz, index=idx_def, key=f"flt_faz_{key_prefix}_{default_fazione}")
    if faz_scelta == "Tutte":
        return lista_chiavi_ordinate
    return [
        k for k in lista_chiavi_ordinate
        if (db_unita.get(k, {}).get("fazione") == faz_scelta) or k.startswith(f"{faz_scelta}:")
    ]

def filtra_supporti_per_fazione(db_supporto_dict, lista_nomi_ordinati, key_prefix, fazione_default="Tutte"):
    """Filtra Tratti Eroici o Artefatti per Fazione (mantenendo sempre 'Nessuno' in cima)."""
    fazioni = sorted(list({
        v.get("fazione", "Generale") for k, v in db_supporto_dict.items()
        if isinstance(v, dict) and k != "Nessuno"
    }))
    opzioni_faz = ["Tutte"] + fazioni
    idx_def = opzioni_faz.index(fazione_default) if fazione_default in opzioni_faz else 0
    
    faz_scelta = st.selectbox("Filtra Fazione", opzioni_faz, index=idx_def, key=f"flt_sup_{key_prefix}_{fazione_default}")
    if faz_scelta == "Tutte":
        return lista_nomi_ordinati
    filtrati = [
        k for k in lista_nomi_ordinati
        if k == "Nessuno" or db_supporto_dict.get(k, {}).get("fazione", "Generale") == faz_scelta
    ]
    return filtrati if "Nessuno" in filtrati else ["Nessuno"] + filtrati


# ==========================================
# 3. CARD ABILITÀ STILE WAHAPEDIA (COLORI SMORZATI PER FASE)
# ==========================================
def ottieni_stile_wahapedia_abilita(ab):
    """
    Restituisce (bg_header, border_color, text_badge, bg_card) in stile Wahapedia AoS 4e,
    con tonalità desaturate/opache in armonia con la pergamena scura di MattHammer.
    """
    tipo = str(ab.get("tipo", "Ability")).lower()
    fasi_str = " ".join(ab.get("fasi", ["Qualsiasi Fase"])).lower()

    # 1. Passive -> Rosso Scuro / Borgogna Imperiale
    if tipo == "passive" or "passiv" in fasi_str:
        return ("rgba(105, 28, 32, 0.88)", "#8f2d33", "#f2d7d9", "rgba(48, 16, 18, 0.55)")
    # 2. Deployment -> Nero Ossidiana / Antracite
    if "deployment" in fasi_str or "schieramento" in fasi_str:
        return ("rgba(22, 22, 24, 0.92)", "#525257", "#e0e0e0", "rgba(15, 15, 17, 0.65)")
    # 3. Start of Turn -> Verde Foresta Cupo (per le fasi extra non citate)
    if "start of" in fasi_str or "inizio" in fasi_str:
        return ("rgba(34, 74, 54, 0.85)", "#3b7a57", "#d8efe2", "rgba(18, 38, 28, 0.55)")
    # 4. Hero Phase -> Oro Antico / Ambra Scura
    if "hero" in fasi_str or "eroi" in fasi_str:
        return ("rgba(138, 102, 33, 0.88)", "#c49638", "#faecc8", "rgba(58, 42, 14, 0.55)")
    # 5. Movement Phase -> Grigio Ardesia
    if "movement" in fasi_str or "movimento" in fasi_str:
        return ("rgba(72, 78, 84, 0.88)", "#7a848f", "#e4e8ec", "rgba(34, 37, 40, 0.55)")
    # 6. Shooting Phase -> Azzurro / Blu Cobalto Antico
    if "shooting" in fasi_str or "tiro" in fasi_str:
        return ("rgba(32, 74, 112, 0.88)", "#3b7cb8", "#d6e8f7", "rgba(16, 36, 56, 0.55)")
    # 7. Charge Phase -> Arancio Bruciato / Rame
    if "charge" in fasi_str or "carica" in fasi_str:
        return ("rgba(156, 78, 24, 0.88)", "#c96b27", "#fae3d2", "rgba(64, 32, 10, 0.55)")
    # 8. Combat Phase -> Rosso Cremisi da Battaglia
    if "combat" in fasi_str or "combattimento" in fasi_str:
        return ("rgba(142, 38, 34, 0.88)", "#b83732", "#fadbd8", "rgba(62, 18, 16, 0.55)")
    # 9. End of Turn -> Viola Ametista Scuro
    if "end of" in fasi_str or "fine turno" in fasi_str:
        return ("rgba(88, 44, 108, 0.88)", "#8646a3", "#ead8f2", "rgba(40, 20, 50, 0.55)")
    # 10. Qualsiasi Fase / Altre -> Ottone / Bronzo Neutro
    return ("rgba(82, 64, 44, 0.88)", "#8c6d46", "#efe4d2", "rgba(38, 28, 18, 0.55)")

def render_card_abilita_wahapedia(ab):
    """Genera l'HTML della scheda abilità con la barra superiore colorata in stile Wahapedia."""
    bg_head, border_col, txt_head, bg_body = ottieni_stile_wahapedia_abilita(ab)
    tipo_ab = ab.get("tipo", "Ability")
    fasi_txt = ", ".join(ab.get("fasi", ["Qualsiasi Fase"]))
    is_reaz = ab.get("reazione", False)
    is_once = ab.get("once_per_battle", False)
    val_lancio = int(ab.get("valore_lancio", 0) or 0)

    badges_extra = ""
    if is_reaz:
        badges_extra += '<span style="background:#a93226; color:#fff; padding:1px 6px; border-radius:3px; margin-left:6px; font-size:0.75rem;">⚡ REACTION</span>'
    if is_once:
        badges_extra += '<span style="background:rgba(0,0,0,0.45); color:#f5d680; padding:1px 6px; border-radius:3px; margin-left:6px; font-size:0.75rem;">ONCE PER BATTLE</span>'
    if tipo_ab in ["Spell", "Prayer"] and val_lancio > 0:
        badges_extra += f'<span style="background:#1b120c; border:1px solid #d4af37; color:#f7d57f; padding:1px 6px; border-radius:10px; margin-left:6px; font-size:0.78rem;">🎲 {val_lancio}+</span>'

    return f"""
    <div style="background:{bg_body}; border:1px solid {border_col}; border-left:4px solid {border_col}; border-radius:5px; margin:7px 0; overflow:hidden; box-shadow:0 3px 8px rgba(0,0,0,0.45);">
        <div style="background:{bg_head}; color:{txt_head}; padding:4px 10px; font-family:'Cinzel', serif; font-size:0.8rem; font-weight:700; letter-spacing:0.6px; display:flex; justify-content:space-between; align-items:center; border-bottom:1px solid {border_col};">
            <span>{tipo_ab.upper()} — {fasi_txt.upper()}</span>
            <span>{badges_extra}</span>
        </div>
        <div style="padding:8px 12px; color:#f4ecd8; font-size:0.93rem; line-height:1.45;">
            <b style="color:#f7d57f; font-family:'Cinzel', serif;">{ab.get('nome', 'Abilità')}:</b> {ab.get('descrizione', '')}
        </div>
    </div>
    """