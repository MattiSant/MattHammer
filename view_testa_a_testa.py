import streamlit as st
import numpy as np
import pandas as pd
import re
from core_engine import (
    calcola_arma_analitico,
    simula_monte_carlo
)

# Funzione helper per estrarre in sicurezza numeri interi da stringhe/dizionari
def estrai_intero_sicuro(valore, default=0):
    if isinstance(valore, (int, float)):
        return int(valore)
    if isinstance(valore, str):
        match = re.search(r"\d+", valore)
        if match:
            return int(match.group(0))
    return default

# PARSER AVANZATO PER ARMI AoS 4e
def analizza_testo_copiato_robusto(testo):
    armi_estratte = []
    pattern_stat = r'(?:(\d+\")\s+)?((?:\d+|[1-9]?D\d+(?:\+\d+)?|D\d+))\s+(\d)\+\s+(\d)\+\s+(\d|---|0|-)\s+((?:\d+|[1-9]?D\d+(?:\+\d+)?|D\d+))$'
    
    # Set di parole chiave che compongono le intestazioni delle tabelle (vengono ignorate)
    header_words = {"ranged", "melee", "missile", "weapons", "weapon", "rng", "atk", "hit", "wnd", "rnd", "dmg", "damage", "attacks"}

    linee = testo.split('\n')
    nome_temporaneo = ""

    for linea in linee:
        linea_pulita = linea.strip().replace('\t', ' ')
        linea_pulita = re.sub(r'\s+', ' ', linea_pulita)

        if not linea_pulita:
            continue

        # Filtro anti-intestazione
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

            crit = "Nessuno"
            if "Crit (Mortal)" in testo_combinato: crit = "Crit (Mortal)"
            elif "Crit (Auto-wound)" in testo_combinato: crit = "Crit (Auto-wound)"
            elif "Crit (2 Hits)" in testo_combinato: crit = "Crit (2 Hits)"

            anti = "Nessuno"
            if "Anti-HERO" in testo_combinato: anti = "HERO"
            elif "Anti-INFANTRY" in testo_combinato: anti = "INFANTRY"
            elif "Anti-MONSTER" in testo_combinato: anti = "MONSTER"
            elif "Anti-CAVALRY" in testo_combinato: anti = "CAVALRY"

            nome_pulito = nome_temporaneo if nome_temporaneo else testo_prima
            
            tags_da_rimuovere = ["Crit (Auto-wound)", "Crit (Mortal)", "Crit (2 Hits)", "Shoot in Combat", "Anti-HERO", "Anti-INFANTRY", "Anti-MONSTER", "Anti-CAVALRY"]
            for tag in tags_da_rimuovere:
                nome_pulito = re.sub(r',?\s*' + re.escape(tag), '', nome_pulito, flags=re.IGNORECASE)
            
            nome_pulito = nome_pulito.strip(" ,-")
            if not nome_pulito:
                nome_pulito = "Arma"

            ranged = True if gittata else False
            gittata_str = gittata if gittata else "Melee"

            armi_estratte.append({
                "nome": nome_pulito, "attiva": True, "ranged": ranged, "range": gittata_str,
                "atk": str(atk), "hit": hit, "wnd": wnd, "rend": rend, "dmg": str(dmg),
                "crit_type": crit, "anti_target": anti, "charge_dmg": False, "anti_charge": False, "companion": False
            })

            nome_temporaneo = ""
        else:
            nome_temporaneo = (nome_temporaneo + " " + linea_pulita).strip()

    return armi_estratte

def render_testa_a_testa():
    st.markdown("""
    <style>
        .section-header {
            font-family: 'Cinzel Decorative', serif !important;
            font-size: 1.85rem !important;
            color: #f5d680 !important;
            letter-spacing: 1.5px !important;
            text-transform: uppercase;
            border-bottom: 2px solid #8c6d46 !important;
            padding-bottom: 6px;
            margin-top: 15px;
            margin-bottom: 4px;
            text-shadow: 0 2px 8px rgba(0,0,0,0.8);
        }
        .subsection-title {
            font-family: 'Cinzel', serif !important;
            font-size: 1.25rem !important;
            color: #e6c665 !important;
            font-weight: 700 !important;
            letter-spacing: 0.6px !important;
            border-bottom: 1px dashed rgba(140, 109, 70, 0.45);
            padding-bottom: 3px;
            margin-bottom: 6px;
        }
        .warscroll-box {
            background: linear-gradient(135deg, #1c150e 0%, #120e0a 100%);
            border: 2px solid #8c6d46;
            border-radius: 6px;
            padding: 12px;
            margin-top: 8px;
            margin-bottom: 12px;
            color: #f4ecd8;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("MattHammer — Laboratorio Tattico")
    st.caption("Analizzatore duelli, test matematici e assalti coordinati multi-unità.")

    if "lista_supporti_attivi" not in st.session_state:
        st.session_state["lista_supporti_attivi"] = []

    opzioni_db = ["--- Inserimento Manuale ---"] + [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]

    # ==========================================
    # SEZIONE 1: SCHIERAMENTO D'ASSALTO (PRINCIPALE)
    # ==========================================
    st.markdown('<div class="section-header">Schieramento d\'Assalto</div>', unsafe_allow_html=True)
    st.caption("Seleziona un'unità dal database (in Sola Lettura) oppure inserisci manualmente le armi per testarle.")

    attaccante_sel = st.selectbox("Seleziona Unità d'Attacco Principale", opzioni_db, key="sel_attaccante_principale")

    armi_attaccante = []
    n_mod_att_base = 1
    punti_att_base = 0
    campione_att = False
    rinforzata_att = False

    if attaccante_sel == "--- Inserimento Manuale ---":
        # ================= MANUALE =================
        with st.container(border=True):
            st.markdown('<div class="subsection-title">Inserimento Rapido Manuale</div>', unsafe_allow_html=True)
            st.caption("Incolla un testo (es. 'Spada 12\" 5 3+ 3+ 1 2') o crea le armi a mano.")
            testo_copiato = st.text_area("Incolla profili armi:", height=68, key="txt_copia_att")
            if st.button("Applica Testo alle Armi"):
                armi_estratte = analizza_testo_copiato_robusto(testo_copiato)
                if armi_estratte:
                    st.session_state["corrente_armi"] = armi_estratte
                    # FIX CHE RISOLVE IL PROBLEMA DELLE ARMI VUOTE:
                    st.session_state["form_version"] = st.session_state.get("form_version", 0) + 1 
                    st.rerun()
                else:
                    st.error("Nessun profilo riconosciuto! Assicurati che finisca con: Attacchi, Hit, Wound, Rend, Danno.")

        col_armi, col_difesa_unita = st.columns(2)
        opzioni_dadi = ["---", "1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "D3", "D3+1", "D6", "2D6"]
        opzioni_hw = ["---", 2, 3, 4, 5, 6]
        v_key = st.session_state.get("form_version", 0)

        with col_armi:
            st.markdown('<div class="subsection-title">Profili Armi (Modificabili)</div>', unsafe_allow_html=True)
            if st.button("➕ Aggiungi Arma"):
                st.session_state["corrente_armi"].append({
                    "nome": "Nuova Arma", "attiva": True, "ranged": False, "range": "Melee", "atk": "1",
                    "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno",
                    "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False
                })
                st.session_state["form_version"] += 1
                st.rerun()

            armi_aggiornate = []
            for idx, p_arma in enumerate(st.session_state["corrente_armi"]):
                with st.expander(f"⚔️ {p_arma['nome']}", expanded=True):
                    c1, c2, c3 = st.columns([2, 1, 1])
                    nome_a = c1.text_input("Nome", value=p_arma["nome"], key=f"nm_{idx}_{v_key}")
                    attiva_a = c2.checkbox("Attiva", value=p_arma["attiva"], key=f"att_{idx}_{v_key}")
                    comp_a = c3.checkbox("Companion", value=p_arma.get("companion", False), key=f"cmp_{idx}_{v_key}")

                    s1, s2, s3, s4, s5 = st.columns(5)
                    atk = s1.selectbox("Atk", opzioni_dadi, index=opzioni_dadi.index(str(p_arma.get("atk", "1"))) if str(p_arma.get("atk", "1")) in opzioni_dadi else 1, key=f"atk_{idx}_{v_key}")
                    hit = s2.selectbox("Hit", opzioni_hw, index=opzioni_hw.index(p_arma.get("hit", 4)) if p_arma.get("hit", 4) in opzioni_hw else 3, key=f"hit_{idx}_{v_key}")
                    wnd = s3.selectbox("Wnd", opzioni_hw, index=opzioni_hw.index(p_arma.get("wnd", 4)) if p_arma.get("wnd", 4) in opzioni_hw else 3, key=f"wnd_{idx}_{v_key}")
                    rend = s4.number_input("Rend", 0, 5, value=int(p_arma.get("rend", 0)) if str(p_arma.get("rend", 0)) != "---" else 0, key=f"rnd_{idx}_{v_key}")
                    dmg = s5.selectbox("Dmg", opzioni_dadi, index=opzioni_dadi.index(str(p_arma.get("dmg", "1"))) if str(p_arma.get("dmg", "1")) in opzioni_dadi else 1, key=f"dmg_{idx}_{v_key}")

                    ab1, ab2, ab3, ab4 = st.columns(4)
                    crit = ab1.selectbox("Critico", ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)"], index=["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)"].index(p_arma.get("crit_type", "Nessuno")), key=f"crt_{idx}_{v_key}")
                    anti = ab2.selectbox("Anti-X", ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER"], index=["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER"].index(p_arma.get("anti_target", "Nessuno")), key=f"ant_{idx}_{v_key}")
                    ranged = ab3.checkbox("Da Tiro", value=p_arma.get("ranged", False), key=f"rng_{idx}_{v_key}")
                    gittata = ab4.text_input("Gittata", value=p_arma.get("range", "12\"" if p_arma.get("ranged") else "Melee"), key=f"ran_{idx}_{v_key}")
                    
                    if st.button("🗑️ Rimuovi", key=f"del_{idx}_{v_key}"):
                        st.session_state["corrente_armi"].pop(idx)
                        st.session_state["form_version"] += 1
                        st.rerun()

                    armi_aggiornate.append({
                        "nome": nome_a, "attiva": attiva_a, "ranged": ranged, "range": gittata, "atk": atk, "hit": hit, "wnd": wnd, "rend": rend, "dmg": dmg,
                        "crit_type": crit, "anti_target": anti, "charge_dmg": p_arma.get("charge_dmg", False), "anti_charge": p_arma.get("anti_charge", False), "companion": comp_a
                    })
            st.session_state["corrente_armi"] = armi_aggiornate

        with col_difesa_unita:
            st.markdown('<div class="subsection-title">Statistiche e Composizione (Manuale)</div>', unsafe_allow_html=True)
            with st.container(border=True):
                cs1, cs2 = st.columns(2)
                
                val_modelli = max(1, estrai_intero_sicuro(st.session_state.get("corrente_modelli", 1), 1))
                st.session_state["corrente_modelli"] = cs1.number_input("Modelli Base", min_value=1, max_value=60, value=val_modelli)
                
                val_punti = max(0, estrai_intero_sicuro(st.session_state.get("corrente_punti", 100), 0))
                st.session_state["corrente_punti"] = cs2.number_input("Costo in Punti", min_value=0, max_value=2000, value=val_punti, step=10)
                
                rinforzata_att = st.checkbox("Unità Rinforzata (x2)", value=False)
                st.session_state["corrente_campione"] = st.checkbox("Presenza Campione (+1 Atk)", value=st.session_state.get("corrente_campione", False))
                
                d_corr = st.session_state.get("corrente_difesa", {"salute_per_modello": 2, "save": 4, "ward": 7})
                c_sv, c_wd, c_hp = st.columns(3)
                
                sv_idx = [2, 3, 4, 5, 6, "---"].index(d_corr.get("save", 4)) if d_corr.get("save", 4) in [2, 3, 4, 5, 6, "---"] else 2
                save_nativo = c_sv.selectbox("Save Base", [2, 3, 4, 5, 6, "---"], index=sv_idx)
                
                wd_idx = [4, 5, 6, 7, "---"].index(d_corr.get("ward", 7)) if d_corr.get("ward", 7) in [4, 5, 6, 7, "---"] else 3
                ward_nativo = c_wd.selectbox("Ward Base", [4, 5, 6, 7, "---"], index=wd_idx)
                
                val_salute = max(1, estrai_intero_sicuro(d_corr.get("salute_per_modello", 2), 2))
                salute_modello = c_hp.number_input("Salute", min_value=1, max_value=30, value=val_salute)
                
                st.session_state["corrente_difesa"] = {"salute_per_modello": salute_modello, "save": save_nativo, "ward": ward_nativo}

            # ================= PONTE PER LA FORGIA =================
            st.markdown("---")
            if st.button("🛠️ Invia Profilo alla Forgia per il Salvataggio", type="primary", use_container_width=True):
                st.session_state["forgia_armi"] = [dict(a) for a in st.session_state["corrente_armi"]]
                d_def = st.session_state["corrente_difesa"]
                st.session_state["forgia_salute"] = d_def.get("salute_per_modello", 2)
                
                sv = d_def.get("save", "---")
                st.session_state["forgia_save"] = f"{sv}+" if sv != "---" else "-"
                wd = d_def.get("ward", "---")
                st.session_state["forgia_ward"] = f"{wd}+" if wd != "---" else "-"
                
                st.session_state["forgia_modelli"] = st.session_state["corrente_modelli"]
                st.session_state["forgia_punti"] = st.session_state["corrente_punti"]
                st.session_state["forgia_campione"] = st.session_state["corrente_campione"]
                
                st.session_state["forgia_version"] = st.session_state.get("forgia_version", 0) + 1
                st.session_state["forgia_nome"] = ""
                
                st.session_state["pagina_selezionata"] = "Forgia del Grimorio (Database)"
                st.rerun()

        armi_attaccante = st.session_state["corrente_armi"]
        n_mod_att_base = st.session_state["corrente_modelli"]
        campione_att = st.session_state["corrente_campione"]
        punti_att_base = st.session_state["corrente_punti"]

    else:
        # ================= DA DATABASE (SOLA LETTURA) =================
        d_att_db = st.session_state["db_unita"][attaccante_sel]
        armi_attaccante = d_att_db.get("armi", [])
        n_mod_att_base = estrai_intero_sicuro(d_att_db.get("n_modelli", 1), 1)
        campione_att = d_att_db.get("campione", False)
        punti_att_base = estrai_intero_sicuro(d_att_db.get("punti", 100))
        
        stat_c_att = d_att_db.get("statistiche_cerchio", {})
        dif_att = d_att_db.get("difesa", {})

        st.markdown('<div class="subsection-title">Warscroll Unità (Sola Lettura)</div>', unsafe_allow_html=True)
        c_w1, c_w2 = st.columns([1, 2.5])
        
        with c_w1:
            st.markdown(f"""
            <div class="warscroll-box" style="font-size: 0.95rem;">
                <b style="color:#e6c665;">Base:</b> {n_mod_att_base} mod. | {punti_att_base} pt<br>
                <b>Move:</b> {stat_c_att.get("movimento", "6\"")}<br>
                <b>OC:</b> {stat_c_att.get("controllo", 1)}<br>
                <b>Save:</b> {stat_c_att.get("save", f"{dif_att.get('save', 4)}+")}<br>
                <b>Salute:</b> {stat_c_att.get("salute", dif_att.get("salute_per_modello", 2))}<br>
                <b>Ward:</b> {stat_c_att.get("ward", f"{dif_att.get('ward', 7)}+")}
            </div>
            """, unsafe_allow_html=True)
            
            if d_att_db.get("può_essere_rinforzata", True):
                rinforzata_att = st.checkbox("Schiera Rinforzata (x2)", value=False)
            else:
                st.caption("Unità non rinforzabile")
                
        with c_w2:
            for arma in armi_attaccante:
                if str(arma.get("hit")) != "---":
                    re_str = arma.get('rend', 0)
                    cr_str = arma.get('crit_type', 'Nessuno')
                    cp_str = " | Companion" if arma.get("companion", False) else ""
                    st.markdown(f"""
                    <div style="background: rgba(0,0,0,0.3); border-left: 3px solid #8c6d46; padding: 6px 10px; margin-bottom: 5px;">
                        <b>⚔️ {arma['nome']}</b> {cp_str}<br>
                        <small>Atk: <b>{arma['atk']}</b> | Hit: <b>{arma['hit']}+</b> | Wnd: <b>{arma['wnd']}+</b> | Rend: <b>{re_str}</b> | Dmg: <b>{arma['dmg']}</b> | Critico: <b>{cr_str}</b> | Range: <b>{arma.get('range', 'Melee')}</b></small>
                    </div>
                    """, unsafe_allow_html=True)


    # ==========================================
    # MODIFICATORI GLOBALI E BUFF (SEMPRE ATTIVI)
    # ==========================================
    col_comandi, col_danni_extra = st.columns(2)
    with col_comandi:
        st.markdown('<div class="subsection-title">Buff, Comandi e Carica</div>', unsafe_allow_html=True)
        st.caption("Modificatori situazionali da applicare al profilo d'attacco.")
        with st.container(border=True):
            ha_caricato = st.checkbox("L'unità ha Caricato", value=False, key="glob_carica")
            all_out_attack = st.checkbox("Comando: All-out Attack (+1 Hit)", value=False, key="glob_aoa")
            with st.expander("Modificatori Hit/Wound e Bonus Extra"):
                mod_hit_extra = st.slider("Modificatori Hit Extra", -2, 2, 0, key="glob_mhit")
                mod_wnd_extra = st.slider("Modificatori Wound Extra", -2, 2, 0, key="glob_mwnd")
                bonus_atk = st.number_input("Attacchi Extra", 0, 5, 0, key="glob_batk")
                bonus_rend = st.number_input("Rend Extra", 0, 3, 0, key="glob_brend")
                bonus_dmg = st.number_input("Danno Extra", 0, 3, 0, key="glob_bdmg")
                crit_on_5 = st.checkbox("Critico al 5+", value=False, key="glob_crit5")

    with col_danni_extra:
        st.markdown('<div class="subsection-title">Danni Mortali Extra (Preghiere/Magie)</div>', unsafe_allow_html=True)
        st.caption("Impatto di eventuali mortali inflitti nella stessa sequenza.")
        with st.container(border=True):
            c1, c2, c3 = st.columns([1, 1.2, 1.5])
            mortal_extra_dadi = c1.number_input("N. Dadi", min_value=0, max_value=100, value=0, key="glob_mdadi")
            mortal_extra_tipo = c2.selectbox("Tipo", [3, 6], index=1, format_func=lambda x: f"D{x}", key="glob_mtipo")
            mortal_extra_soglia = c3.selectbox("Soglia", ["Nessuna (Somma)", "2+", "3+", "4+", "5+", "6+"], key="glob_msoglia")
            mortal_extra_fisso = st.number_input("Danni Fissi Extra", 0, 100, 0, key="glob_mfisso")
            
    # Costruzione Moduli di Attacco finali
    n_mod_att = n_mod_att_base * (2 if rinforzata_att else 1)
    punti_att_totale = punti_att_base * (2 if rinforzata_att else 1)
    
    mod_globali_att = {
        "n_modelli": n_mod_att, 
        "campione": campione_att, 
        "ha_caricato": ha_caricato,
        "all_out_attack": all_out_attack, 
        "mod_hit": mod_hit_extra + (1 if all_out_attack else 0),
        "mod_wnd": mod_wnd_extra, 
        "bonus_atk": bonus_atk, 
        "bonus_rend": bonus_rend,
        "bonus_dmg": bonus_dmg, 
        "crit_on": 5 if crit_on_5 else 6,
        "mortal_extra_dadi": mortal_extra_dadi,
        "mortal_extra_tipo": mortal_extra_tipo,
        "mortal_extra_soglia": mortal_extra_soglia,
        "mortal_extra_fisso": mortal_extra_fisso
    }

    # ==========================================
    # FORZE DI SUPPORTO (COMBINATO)
    # ==========================================
    st.markdown("---")
    with st.expander("🛡️ Forze Alleate di Supporto (Attacco Combinato)", expanded=bool(st.session_state["lista_supporti_attivi"])):
        col_sel_sup, col_btn_sup = st.columns([3, 1])
        opzioni_db_supporto = [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]
        unita_da_aggiungere = col_sel_sup.selectbox("Scegli supporto dal DB:", ["--- Scegli unità ---"] + opzioni_db_supporto, key="sel_nuovo_supporto")
        
        if col_btn_sup.button("➕ Schiera Supporto"):
            if unita_da_aggiungere != "--- Scegli unità ---":
                st.session_state["lista_supporti_attivi"].append({
                    "chiave_db": unita_da_aggiungere,
                    "rinforzata": False, "carica": ha_caricato, "all_out_attack": False,
                    "mod_hit": 0, "mod_wnd": 0, "bonus_atk": 0, "bonus_rend": 0, "bonus_dmg": 0, "crit_5": False
                })
                st.rerun()

        config_supporti = []
        if st.session_state["lista_supporti_attivi"]:
            supporti_da_rimuovere = []
            for s_idx, sup_elem in enumerate(st.session_state["lista_supporti_attivi"]):
                nome_db = sup_elem["chiave_db"]
                dati_u_db = st.session_state["db_unita"].get(nome_db, {})
                
                with st.container(border=True):
                    cs_h1, cs_h2, cs_h3 = st.columns([2.5, 1, 1])
                    cs_h1.markdown(f"**Supporto #{s_idx+1}:** {nome_db}")
                    sup_elem["rinforzata"] = cs_h2.checkbox("Rinforzata (x2)", value=sup_elem["rinforzata"], key=f"rinf_s_{s_idx}")
                    if cs_h3.button("Rimuovi", key=f"del_s_{s_idx}"): supporti_da_rimuovere.append(s_idx)

                    sb1, sb2, sb3 = st.columns(3)
                    sup_elem["carica"] = sb1.checkbox("Carica", value=sup_elem["carica"], key=f"chg_s_{s_idx}")
                    sup_elem["all_out_attack"] = sb2.checkbox("All-out Attack", value=sup_elem["all_out_attack"], key=f"aoa_s_{s_idx}")
                    sup_elem["crit_5"] = sb3.checkbox("Critico al 5+", value=sup_elem["crit_5"], key=f"c5_s_{s_idx}")

                    n_mod_sup = estrai_intero_sicuro(dati_u_db.get("n_modelli", 1)) * (2 if sup_elem["rinforzata"] else 1)
                    punti_sup = estrai_intero_sicuro(dati_u_db.get("punti", 0)) * (2 if sup_elem["rinforzata"] else 1)
                    
                    config_supporti.append({
                        "nome_unita": nome_db,
                        "armi": dati_u_db.get("armi", []),
                        "punti": punti_sup,
                        "mod_globali": {
                            "n_modelli": n_mod_sup,
                            "campione": bool(dati_u_db.get("campione", False)),
                            "ha_caricato": sup_elem["carica"],
                            "all_out_attack": sup_elem["all_out_attack"],
                            "mod_hit": sup_elem["mod_hit"] + (1 if sup_elem["all_out_attack"] else 0),
                            "mod_wnd": sup_elem["mod_wnd"],
                            "bonus_atk": sup_elem["bonus_atk"], "bonus_rend": sup_elem["bonus_rend"], "bonus_dmg": sup_elem["bonus_dmg"],
                            "crit_on": 5 if sup_elem["crit_5"] else 6,
                            "mortal_extra_dadi": 0, "mortal_extra_tipo": 6, "mortal_extra_soglia": "Nessuna (Somma i valori)", "mortal_extra_fisso": 0
                        }
                    })
            if supporti_da_rimuovere:
                for idx_canc in sorted(supporti_da_rimuovere, reverse=True): st.session_state["lista_supporti_attivi"].pop(idx_canc)
                st.rerun()

    # ==========================================
    # SEZIONE 2: BERSAGLIO DESIGNATO
    # ==========================================
    st.markdown('<div class="section-header">Bersaglio Designato (Difesa)</div>', unsafe_allow_html=True)
    
    bersaglio_sel = st.selectbox("Seleziona Unità Avversaria (Bersaglio)", opzioni_db, key="sel_bersaglio_principale")

    save_b = 4
    ward_b = 7
    salute_b = 10
    punti_b = 100
    keywords_b = ["INFANTRY"]

    if bersaglio_sel == "--- Inserimento Manuale ---":
        with st.container(border=True):
            b1, b2, b3, b4 = st.columns(4)
            save_b = b1.selectbox("Save Base Bersaglio", [2, 3, 4, 5, 6, 7], index=2, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
            ward_b = b2.selectbox("Ward Base Bersaglio", [7, 6, 5, 4], index=0, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)")
            salute_b = b3.number_input("Salute Totale (PF)", 1, 200, 10)
            punti_b = b4.number_input("Costo Punti", 0, 2000, 100, step=10)
            keywords_b = st.multiselect("Keywords", ["INFANTRY", "HERO", "CAVALRY", "MONSTER", "WAR MACHINE"], default=["INFANTRY"])
    else:
        d_bers_db = st.session_state["db_unita"][bersaglio_sel]
        stat_c_b = d_bers_db.get("statistiche_cerchio", {})
        dif_b = d_bers_db.get("difesa", {})
        
        sv_str = stat_c_b.get("save", f"{dif_b.get('save', 4)}+")
        wd_str = stat_c_b.get("ward", f"{dif_b.get('ward', 7)}+")
        sv_base = estrai_intero_sicuro(sv_str, 7)
        wd_base = estrai_intero_sicuro(wd_str, 7)
        
        sal_mod = estrai_intero_sicuro(stat_c_b.get("salute", dif_b.get("salute_per_modello", 1)), 1)
        mod_base = estrai_intero_sicuro(d_bers_db.get("n_modelli", 1), 1)
        pt_base = estrai_intero_sicuro(d_bers_db.get("punti", 100))

        with st.container(border=True):
            cw1, cw2 = st.columns([1.5, 1])
            cw1.markdown(f"""
            <div class="warscroll-box" style="font-size: 0.95rem; margin-top:0;">
                <b style="color:#c0392b;">Bersaglio:</b> {bersaglio_sel}<br>
                <b>Save:</b> {sv_str} | <b>Ward:</b> {wd_str} | <b>Salute/mod:</b> {sal_mod}
            </div>
            """, unsafe_allow_html=True)
            
            rinforzata_bers = cw2.checkbox("Bersaglio Rinforzato (x2)", value=False)
            
            molt_b = 2 if rinforzata_bers else 1
            salute_b = sal_mod * mod_base * molt_b
            punti_b = pt_base * molt_b
            save_b = sv_base
            ward_b = wd_base
            keywords_b = [str(k).upper() for k in d_bers_db.get("keywords", ["INFANTRY"])]
            
            cw2.markdown(f"**Salute Totale:** `{salute_b} PF`\n\n**Valore:** `{punti_b} pt`")

    with st.container(border=True):
        st.markdown("**Buff Difensivi e Terreno del Bersaglio (Modificabili)**")
        dt1, dt2, dt3 = st.columns(3)
        cover_b = dt1.checkbox("Cover (+1 Save)", value=False, key="def_cover")
        aod_b = dt2.checkbox("All-out Defence (+1 Save)", value=False, key="def_aod")
        extra_save_b = dt3.checkbox("Abilità extra (+1 Save)", value=False, key="def_exsv")
        obscuring_b = dt1.checkbox("Terreno Obscuring (-1 Hit)", value=False, key="def_obsc")
        bersaglio_carica = dt2.checkbox("Il Bersaglio ha Caricato", value=False, key="def_bchg")
        blocca_ward_b = dt3.checkbox("Ward Annullati", value=False, key="def_nowd")

    mod_globali_att["bersaglio_ha_caricato"] = bersaglio_carica
    for sup in config_supporti:
        sup["mod_globali"]["bersaglio_ha_caricato"] = bersaglio_carica

    bersaglio_dict = {
        "save": save_b, "ward": ward_b, "salute": salute_b, "keywords": keywords_b,
        "cover": cover_b, "aod": aod_b, "bonus_save_extra": 1 if extra_save_b else 0,
        "obscuring": obscuring_b, "bersaglio_ha_caricato": bersaglio_carica,
        "mod_ward_penalita": 0, "blocca_ward": blocca_ward_b, "mod_wnd_nerf": 0
    }

    # ==========================================
    # CALCOLO MOTORE ANALITICO E MONTE CARLO
    # ==========================================
    dettaglio_armi_combinate = []
    
    for a in armi_attaccante:
        if a.get("attiva", False) and str(a.get("hit")) != "---":
            dettaglio_armi_combinate.append({
                "fonte": "Unità Principale", "arma": a, "risultato": calcola_arma_analitico(a, mod_globali_att, bersaglio_dict)
            })

    for sup in config_supporti:
        for a_sup in sup["armi"]:
            if a_sup.get("attiva", False) and str(a_sup.get("hit")) != "---":
                dettaglio_armi_combinate.append({
                    "fonte": sup["nome_unita"], "arma": a_sup, "risultato": calcola_arma_analitico(a_sup, sup["mod_globali"], bersaglio_dict)
                })

    risultati_armi = [item["risultato"] for item in dettaglio_armi_combinate]
    danno_atteso_armi = sum(r["danno_netto"] for r in risultati_armi)
    moltiplicatore_ward = 0.0 if bersaglio_dict["blocca_ward"] else (1.0 if ward_b >= 7 else 1.0 - ((7 - max(2, ward_b)) / 6.0))

    danno_extra_base = float(mortal_extra_fisso)
    if mortal_extra_dadi > 0:
        if mortal_extra_soglia == "Nessuna (Somma)": danno_extra_base += mortal_extra_dadi * (2.0 if mortal_extra_tipo == 3 else 3.5)
        else: danno_extra_base += mortal_extra_dadi * max(0.0, (mortal_extra_tipo - int(mortal_extra_soglia[0]) + 1) / float(mortal_extra_tipo))

    danno_totale_atteso = danno_atteso_armi + (danno_extra_base * moltiplicatore_ward)
    punti_attaccante_totali = punti_att_totale + sum(sup["punti"] for sup in config_supporti)
    roi_punti = (danno_totale_atteso / punti_attaccante_totali) * 100.0 if punti_attaccante_totali > 0 else 0.0

    n_simulazioni = 10000
    campioni_mc = simula_monte_carlo(armi_attaccante, mod_globali_att, bersaglio_dict, n_sim=n_simulazioni)
    for sup in config_supporti:
        campioni_mc += simula_monte_carlo(sup["armi"], sup["mod_globali"], bersaglio_dict, n_sim=n_simulazioni)

    prob_uccisione = np.mean(campioni_mc >= salute_b) * 100.0
    dev_std = np.std(campioni_mc)

    # ==========================================
    # VERDETTO TATTICO E RISULTATI
    # ==========================================
    st.markdown('<div class="section-header">Verdetto Tattico e Risultati</div>', unsafe_allow_html=True)
    st.caption("Scomposizione dettagliata delle fasi di combattimento, curva cumulativa e sostenibilità in punti.")

    attacchi_totali = sum(r['attacchi'] for r in risultati_armi)
    tutte_armi_attive = [item["arma"] for item in dettaglio_armi_combinate if item["arma"]["attiva"] and str(item["arma"]["hit"]) != "---"]
    max_rend = max([int(a['rend']) for a in tutte_armi_attive if str(a['rend']) != "---"] + [0])
    ha_crit_mortal = any(a.get('crit_type', 'Nessuno') == 'Crit (Mortal)' for a in tutte_armi_attive)
    anti_targets = list(set([a['anti_target'] for a in tutte_armi_attive if a.get('anti_target', 'Nessuno') != 'Nessuno']))

    difesa_corrente = st.session_state.get("corrente_difesa", {})
    ward_unita = int(difesa_corrente.get("ward", 7)) if str(difesa_corrente.get("ward")) != "---" else 7
    save_unita = int(difesa_corrente.get("save", 4)) if str(difesa_corrente.get("save")) != "---" else 4
    salute_totale_unita = int(difesa_corrente.get("salute_per_modello", 2)) * mod_globali_att["n_modelli"]

    ruoli_trovati = []
    if ward_unita <= 5 or (save_unita <= 3 and salute_totale_unita >= 15):
        ruoli_trovati.append("**Ancoraggio Difensivo (Tank)**: Elevata resistenza. Ideale per presidiare gli obiettivi contesi o assorbire cariche nemiche.")
    if len(anti_targets) > 0:
        targets_str = ", ".join(anti_targets)
        ruoli_trovati.append(f"**Specialista Anti-{targets_str}**: Letale contro questi bersagli designati grazie al bonus penetrazione armatura.")
    if attacchi_totali >= 20:
        ruoli_trovati.append("**Saturatore d'Orde**: Eccezionale volume di dadi per superare le unità leggere per pura saturazione statistica.")
    if ha_crit_mortal or max_rend >= 2:
        ruoli_trovati.append("**Perfora-Armature**: Altamente performante contro bersagli corazzati ed eroi pesanti.")
    if danno_totale_atteso >= 12:
        ruoli_trovati.append("**Incudine d'Urto (Damage Dealer)**: Output offensivo massiccio, da scatenare contro i centri nevralgici del nemico.")
    if not ruoli_trovati:
        ruoli_trovati.append("**Contestatore Flessibile**: Forza bilanciata per contestare obiettivi secondari o schermare i ranghi.")

    with st.container(border=True):
        if config_supporti:
            nomi_sup_str = ", ".join([s["nome_unita"] for s in config_supporti])
            st.markdown(f"**Assalto Coordinato in Corso:** Unità Principale + *{nomi_sup_str}* (Punti complessivi schierati: **{punti_attaccante_totali} pt**)")
            st.markdown("---")
        st.markdown("**Diagnosi Strategica del Gruppo d'Attacco:**")
        for ruolo in ruoli_trovati:
            st.markdown(f"- {ruolo}")

    st.markdown("<br>", unsafe_allow_html=True)

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Danno Medio Atteso", f"{danno_totale_atteso:.2f} ferite", f"± {dev_std:.1f} (Std)")
    m2.metric("Prob. Kill (1 Turno)", f"{prob_uccisione:.1f}%", f"vs {salute_b} Salute")
    m3.metric("ROI Danni (per 100 pt)", f"{roi_punti:.2f} Danni", f"Costo Attacco: {punti_attaccante_totali} pt")
    m4.metric("Attacchi Totali", f"{attacchi_totali:.0f} dadi", f"{1 + len(config_supporti)} unità in azione")

    tab1, tab2, tab3 = st.tabs(["Ripartizione Dadi", "Probabilità Cumulativa", "Consigliere Tattico & Time-to-Kill"])

    with tab1:
        tot_atk = sum(r["attacchi"] for r in risultati_armi)
        tot_hits = sum(r["hits"] for r in risultati_armi)
        tot_wounds = sum(r["wounds"] for r in risultati_armi)
        tot_unsaved = sum(r["unsaved"] for r in risultati_armi)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.markdown('<div class="subsection-title">Ripartizione Danni per Singola Arma</div>', unsafe_allow_html=True)
            st.caption("Dettaglio del rendimento di ciascun profilo d'attacco schierato.")
            righe_armi = []
            for item in dettaglio_armi_combinate:
                righe_armi.append({
                    "Arma": f"{item['arma']['nome']} ({item['fonte']})" if config_supporti else item['arma']["nome"], 
                    "Attacchi": round(item['risultato']["attacchi"], 1), "Hits": round(item['risultato']["hits"], 2), 
                    "Wounds": round(item['risultato']["wounds"], 2), "Danno Netto": round(item['risultato']["danno_netto"], 2)
                })
            if righe_armi:
                st.dataframe(pd.DataFrame(righe_armi), use_container_width=True, hide_index=True)

                if tot_atk > 0:
                    drop_hit = (1.0 - (tot_hits / tot_atk)) * 100.0 if tot_atk > 0 else 0.0
                    drop_wnd = (1.0 - (tot_wounds / tot_hits)) * 100.0 if tot_hits > 0 else 0.0
                    drop_save = (1.0 - (tot_unsaved / tot_wounds)) * 100.0 if tot_wounds > 0 else 0.0
                    
                    max_drop = max(drop_hit, drop_wnd, drop_save)
                    if max_drop == drop_hit:
                        fase_critica = "Fase 1 -> 2 (Tiro per Colpire / Hit)"
                        consiglio_cp = (
                            "**Investi in Fase di Hit (Comando: All-out Attack - 1 CP):** "
                            f"La dispersione maggiore avviene nel colpire (**-{drop_hit:.1f}%** di dadi scartati). "
                            + ("*All-out Attack* è già attivo sull'Unità Principale!" if mod_globali_att["all_out_attack"] else "Attivare **All-out Attack (+1 Hit)** è la scelta migliore per massimizzare il volume di dadi che raggiunge le fasi successive.")
                        )
                    elif max_drop == drop_wnd:
                        fase_critica = "Fase 2 -> 3 (Tiro per Ferire / Wound)"
                        consiglio_cp = (
                            "**Investi in Fase di Wound (Preghiere o Buff di Fazione):** "
                            f"La precisione è solida, ma si perde il **{drop_wnd:.1f}%** dei colpi cercando di ferire. Usa abilità o preghiere che migliorano il Wound."
                        )
                    else:
                        fase_critica = "Fase 3 -> 4 (Tiro Salvezza Nemico / Save)"
                        consiglio_cp = (
                            "**Investi in Penetrazione (Rend) o Effetti Critici:** "
                            f"L'armatura avversaria sta assorbendo il **{drop_save:.1f}%** delle tue ferite! Investi in bonus al Rend o effetti mortali."
                        )

                    with st.container(border=True):
                        st.markdown("#### Guida all'Interpretazione & Analisi del Flusso")
                        st.markdown(
                            f"**Lettura del Flusso Progressivo:**\n"
                            f"1. **Attacchi ({tot_atk:.1f}):** Volume iniziale di dadi tirati.\n"
                            f"2. **Colpi ({tot_hits:.2f}):** A segno (dispersi: {drop_hit:.1f}%).\n"
                            f"3. **Ferite ({tot_wounds:.2f}):** Ferite inflitte con successo (disperse: {drop_wnd:.1f}%).\n"
                            f"4. **Non Salvati ({tot_unsaved:.2f}):** Oltrepassano l'armatura nemica (assorbiti dal Save: {drop_save:.1f}%).\n"
                            f"5. **Danno Finale ({danno_totale_atteso:.2f}):** Moltiplicato per il danno delle armi ed extra"
                            + (f", ridotto dal Ward nemico." if moltiplicatore_ward < 1.0 else ".")
                        )
                        st.markdown("---")
                        st.markdown(f"**Collo di Bottiglia Individuato:** `{fase_critica}`")
                        st.markdown(consiglio_cp)
            else:
                st.info("Nessuna arma attiva.")

        with col_t2:
            st.markdown('<div class="subsection-title">Scomposizione del Flusso d\'Attacco</div>', unsafe_allow_html=True)
            st.caption("Visualizzazione progressiva dei dadi superstiti fino al Danno Netto finale.")
            if tot_atk > 0:
                df_perdite = pd.DataFrame({
                    "Fase": ["1. Attacchi", "2. Colpi (Hit)", "3. Ferite (Wound)", "4. Non Salvati", "5. Danno Netto"],
                    "Valore": [round(tot_atk, 1), round(tot_hits, 1), round(tot_wounds, 1), round(tot_unsaved, 1), round(danno_totale_atteso, 1)]
                })
                st.bar_chart(df_perdite.set_index("Fase"), color="#b38b4d")

    with tab2:
        st.markdown('<div class="subsection-title">Curva di Probabilità Cumulativa</div>', unsafe_allow_html=True)
        st.caption("Probabilità percentuale di infliggere almeno X danni totali in questa fase d'attacco.")
        max_danno_grafico = int(np.percentile(campioni_mc, 99.5)) + 2 if len(campioni_mc) > 0 else 10
        asse_x = np.arange(1, max(10, max_danno_grafico))
        prob_almeno_x = [np.mean(campioni_mc >= x) * 100.0 for x in asse_x]
        st.line_chart(pd.DataFrame({"Danni Minimi (X)": asse_x, "Probabilità (%)": prob_almeno_x}).set_index("Danni Minimi (X)"), color="#b38b4d")

    with tab3:
        st.markdown('<div class="subsection-title">Stima Sopravvivenza Bersaglio (Time-to-Kill)</div>', unsafe_allow_html=True)
        st.caption("Turni stimati necessari per azzerare la salute del bersaglio con le forze schierate.")
        
        ttk = salute_b / danno_totale_atteso if danno_totale_atteso > 0 else 99
        
        if ttk <= 1.0:
            st.success(f"**Esito Letale:** Eliminazione attesa in **1 singolo turno** (Danno atteso {danno_totale_atteso:.1f} vs Salute {salute_b}).")
        elif ttk <= 2.0:
            st.warning(f"**Logoramento:** Saranno necessari circa **2 turni** per abbattere il bersaglio (Danno atteso {danno_totale_atteso:.1f} vs Salute {salute_b}). Valuta un supporto addizionale.")
        else:
            st.error(f"**Attacco Inefficiente:** Richiesti circa **{int(ttk)+1} turni**. Sconsigliato ingaggiare senza supporto concentrato.")

        st.markdown("---")
        st.markdown('<div class="subsection-title">Bilancio Economico e Valutazione d\'Ingaggio</div>', unsafe_allow_html=True)
        st.caption("Rapporto tra punti investiti nell'attacco e valore effettivo neutralizzato sul bersaglio.")
        
        with st.container(border=True):
            if punti_attaccante_totali > 0 and punti_b > 0:
                rapporto_punti = punti_attaccante_totali / float(punti_b)
                percentuale_vita_tolta = min(1.0, danno_totale_atteso / float(salute_b)) if salute_b > 0 else 0.0
                punti_neutralizzati_stimati = punti_b * percentuale_vita_tolta
                efficienza_scambio = (punti_neutralizzati_stimati / float(punti_attaccante_totali)) * 100.0

                ec1, ec2, ec3 = st.columns(3)
                ec1.markdown(f"**Punti Attacco Complessivi:** `{punti_attaccante_totali} pt`")
                ec2.markdown(f"**Valore Bersaglio Nemico:** `{punti_b} pt`")
                ec3.markdown(f"**Valore Neutralizzato (1 Turno):** `{punti_neutralizzati_stimati:.0f} pt` ({percentuale_vita_tolta*100:.0f}% vita)")
                st.markdown("---")

                if ttk <= 1.0 and rapporto_punti <= 1.0:
                    st.success(f"**VERDETTO: SCAMBIO ALTAMENTE VANTAGGIOSO (Trade-Up)**\n\nImpegni {punti_attaccante_totali} pt per spazzare via un bersaglio da {punti_b} pt in 1 turno. Vantaggio netto di {punti_b - punti_attaccante_totali} pt. Ingaggio prioritario raccomandato.")
                elif ttk <= 1.0 and rapporto_punti <= 1.5:
                    st.success(f"**VERDETTO: ELIMINAZIONE AFFIDABILE E CONVENIENTE**\n\nEliminazione immediata al Turno 1 (Kill: {prob_uccisione:.1f}%). Rimuove la risposta nemica al costo di un piccolo sovrapprezzo.")
                elif ttk <= 1.0 and rapporto_punti > 1.5:
                    st.warning(f"**VERDETTO: SOVRACCOSTO TATTICO (Overkill)**\n\nStai concentrando ben {punti_attaccante_totali} pt contro un pezzo da appena {punti_b} pt. Attento a non sguarnire gli obiettivi della mappa.")
                elif ttk <= 1.8 and rapporto_punti <= 1.1:
                    st.info(f"**VERDETTO: INGAGGIO EQUILIBRATO DI LOGORAMENTO**\n\nPunti bilanciati ({punti_attaccante_totali} pt vs {punti_b} pt). Neutralizzi ~{punti_neutralizzati_stimati:.0f} pt al Turno 1.")
                else:
                    st.error(f"**VERDETTO: TRAPPOLA TATTICA (Alto Rischio)**\n\nNeutralizzi appena {punti_neutralizzati_stimati:.0f} pt al Turno 1 (indice di rendimento: {efficienza_scambio:.0f}%). Le truppe rimarranno bloccate fino a {int(ttk)+1} turni.")
            else:
                st.info("Specifica sia il **Costo in Punti dell'Unità Principale** sia il **Costo in Punti del Bersaglio** per visualizzare l'analisi economica.")

        st.markdown("---")
        st.markdown('<div class="subsection-title">Matrice Target Priority</div>', unsafe_allow_html=True)
        st.caption("Danno netto atteso del gruppo d'attacco contro tutte le combinazioni di Save e Ward avversari.")
        saves_lista = [2, 3, 4, 5, 6, 7]
        wards_lista = [7, 6, 5, 4]
        matrice_dati = {}
        for w_val in wards_lista:
            col_nome = f"Ward {w_val}+" if w_val < 7 else "Nessun Ward"
            col_valori = []
            for s_val in saves_lista:
                b_temp = {**bersaglio_dict, "save": s_val, "ward": w_val, "blocca_ward": False}
                danno_armi_mat = sum(calcola_arma_analitico(a, mod_globali_att, b_temp)["danno_netto"] for a in armi_attaccante if a.get("attiva", False))
                for sup in config_supporti:
                    danno_armi_mat += sum(calcola_arma_analitico(a_sup, sup["mod_globali"], b_temp)["danno_netto"] for a_sup in sup["armi"] if a_sup.get("attiva", False))
                col_valori.append(round(danno_armi_mat, 2))
            matrice_dati[col_nome] = col_valori
        df_matrice = pd.DataFrame(matrice_dati, index=[f"Save {s}+" if s < 7 else "No Save (-)" for s in saves_lista])
        
        st.dataframe(df_matrice.style.background_gradient(cmap="YlOrBr", low=0.1, high=0.8), use_container_width=True)