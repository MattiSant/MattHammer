import streamlit as st
import re
from core_engine import salva_nel_database, analizza_testo_copiato

def estrai_intero_da_stringa(testo, default=0):
    match = re.search(r"\d+", str(testo))
    return int(match.group(0)) if match else default

def render_forgia_db():
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
            padding: 15px;
            margin-top: 8px;
            margin-bottom: 12px;
            color: #f4ecd8;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("MattHammer — Forgia del Grimorio")
    st.caption("Crea, modifica e aggiorna le Warscrolls complete delle unità nel tuo database.")

    # Inizializzazione Stati della Forgia
    if "forgia_version" not in st.session_state:
        st.session_state["forgia_version"] = 0
    if "forgia_armi" not in st.session_state:
        st.session_state["forgia_armi"] = []
    if "forgia_abilita" not in st.session_state:
        st.session_state["forgia_abilita"] = []

    v_key = st.session_state["forgia_version"]

    opzioni_db = [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]

    # ==========================================
    # CARICAMENTO / RESET
    # ==========================================
    with st.container(border=True):
        col_load1, col_load2 = st.columns([3, 1])
        unita_da_caricare = col_load1.selectbox("Modifica Unità Esistente (oppure creane una da zero):", ["--- Nuova Unità ---"] + opzioni_db, key=f"load_u_{v_key}")
        
        if col_load2.button("Carica nel Profilo", type="primary", use_container_width=True):
            if unita_da_caricare != "--- Nuova Unità ---":
                d_load = st.session_state["db_unita"][unita_da_caricare]
                st.session_state["forgia_fazione"] = d_load.get("fazione", "Nighthaunt")
                st.session_state["forgia_nome"] = unita_da_caricare.split(": ")[-1] if ": " in unita_da_caricare else unita_da_caricare
                st.session_state["forgia_punti"] = d_load.get("punti", 100)
                st.session_state["forgia_modelli"] = d_load.get("n_modelli", 1)
                st.session_state["forgia_basetta"] = d_load.get("dimensione_basetta", "32mm")
                st.session_state["forgia_rinf"] = d_load.get("può_essere_rinforzata", False)
                st.session_state["forgia_campione"] = d_load.get("campione", False)
                
                sc = d_load.get("statistiche_cerchio", {})
                st.session_state["forgia_movimento"] = sc.get("movimento", "6\"")
                st.session_state["forgia_controllo"] = sc.get("controllo", 1)
                st.session_state["forgia_save"] = sc.get("save", "4+")
                st.session_state["forgia_salute"] = sc.get("salute", 2)
                st.session_state["forgia_ward"] = sc.get("ward", "7+")
                
                st.session_state["forgia_armi"] = d_load.get("armi", [])
                st.session_state["forgia_abilita"] = d_load.get("abilita", [])
                st.session_state["forgia_keywords"] = ", ".join(d_load.get("keywords", []))
                
                st.toast(f"Unità caricata: {unita_da_caricare}")
            else:
                # === RESET DEI CAMPI ===
                st.session_state["forgia_fazione"] = "Nighthaunt"
                st.session_state["forgia_nome"] = ""
                st.session_state["forgia_punti"] = 100
                st.session_state["forgia_modelli"] = 1
                st.session_state["forgia_basetta"] = "32mm"
                st.session_state["forgia_rinf"] = False
                st.session_state["forgia_campione"] = False
                
                st.session_state["forgia_movimento"] = "6\""
                st.session_state["forgia_controllo"] = 1
                st.session_state["forgia_save"] = "4+"
                st.session_state["forgia_salute"] = 2
                st.session_state["forgia_ward"] = "7+"
                
                st.session_state["forgia_armi"] = []
                st.session_state["forgia_abilita"] = []
                st.session_state["forgia_keywords"] = ""
                
                st.toast("Campi azzerati. Pronto per creare una nuova unità.")
                
            st.session_state["forgia_version"] += 1
            st.rerun()
            
    # ==========================================
    # DATI GENERALI E CIRCONFERENZA
    # ==========================================
    st.markdown('<div class="section-header">1. Generalità e Statistiche Cerchio</div>', unsafe_allow_html=True)
    
    with st.container(border=True):
        g1, g2, g3 = st.columns([1.5, 2, 1])
        fazione = g1.selectbox("Fazione", ["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Altro"], index=["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Altro"].index(st.session_state.get("forgia_fazione", "Nighthaunt")), key=f"f_faz_{v_key}")
        nome = g2.text_input("Nome Unità", value=st.session_state.get("forgia_nome", ""), key=f"f_nome_{v_key}")
        punti = g3.number_input("Costo in Punti", min_value=10, max_value=2000, value=st.session_state.get("forgia_punti", 100), step=10, key=f"f_pt_{v_key}")

        g4, g5, g6, g7 = st.columns(4)
        n_modelli = g4.number_input("Modelli Base", min_value=1, max_value=60, value=st.session_state.get("forgia_modelli", 1), key=f"f_mod_{v_key}")
        basetta = g5.text_input("Dimensione Basetta", value=st.session_state.get("forgia_basetta", "32mm"), key=f"f_base_{v_key}")
        puo_rinf = g6.checkbox("Può essere Rinforzata (x2)", value=st.session_state.get("forgia_rinf", False), key=f"f_rinf_{v_key}")
        campione = g7.checkbox("Presenza Campione (+1 Atk)", value=st.session_state.get("forgia_campione", False), key=f"f_camp_{v_key}")

        st.markdown("---")
        st.markdown("**Statistiche della Circonferenza Tetrapartita (Warscroll)**")
        c1, c2, c3, c4, c5 = st.columns(5)
        move = c1.text_input("Movimento (es. 8\" Fly)", value=st.session_state.get("forgia_movimento", "6\""), key=f"f_mov_{v_key}")
        oc = c2.number_input("Controllo (OC)", min_value=0, max_value=20, value=st.session_state.get("forgia_controllo", 1), key=f"f_oc_{v_key}")
        save = c3.selectbox("Save (Armatura)", ["2+", "3+", "4+", "5+", "6+", "-"], index=["2+", "3+", "4+", "5+", "6+", "-"].index(st.session_state.get("forgia_save", "4+")), key=f"f_sv_{v_key}")
        salute = c4.number_input("Salute (Ferite)", min_value=1, max_value=50, value=st.session_state.get("forgia_salute", 2), key=f"f_hp_{v_key}")
        ward = c5.selectbox("Ward (Tiro Salvezza Magico)", ["4+", "5+", "6+", "7+", "-"], index=["4+", "5+", "6+", "7+", "-"].index(st.session_state.get("forgia_ward", "7+")), key=f"f_wd_{v_key}")

    # ==========================================
    # ARMI
    # ==========================================
    st.markdown('<div class="section-header">2. Profili di Combattimento (Armi)</div>', unsafe_allow_html=True)
    with st.container(border=True):
        st.caption("Copia le statistiche dal manuale (es. 'Tomb Greatblade Crit(2 Hits) 2 3+ 3+ 1 1') e usa l'inserimento rapido.")
        txt_armi = st.text_area("Inserimento Rapido Armi:", height=68, key=f"f_txt_armi_{v_key}")
        if st.button("Analizza e Aggiungi Armi"):
            armi_estratte = analizza_testo_copiato(txt_armi)
            if armi_estratte:
                st.session_state["forgia_armi"].extend(armi_estratte)
                st.session_state["forgia_version"] += 1
                st.rerun()

        if st.button("➕ Aggiungi Arma Vuota"):
            st.session_state["forgia_armi"].append({
                "nome": "Nuova Arma", "attiva": True, "ranged": False, "range": "Melee", "atk": "1",
                "hit": 4, "wnd": 4, "rend": 0, "dmg": "1", "crit_type": "Nessuno",
                "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False
            })
            st.session_state["forgia_version"] += 1
            st.rerun()

        armi_aggiornate = []
        opzioni_dadi = ["---", "1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "D3", "D3+1", "D6", "2D6"]
        opzioni_hw = ["---", 2, 3, 4, 5, 6]

        for idx, arma in enumerate(st.session_state["forgia_armi"]):
            with st.expander(f"⚔️ {arma['nome']}", expanded=False):
                ca1, ca2 = st.columns([3, 1])
                nome_a = ca1.text_input("Nome Arma", value=arma["nome"], key=f"a_nome_{idx}_{v_key}")
                if ca2.button("🗑️ Rimuovi", key=f"a_del_{idx}_{v_key}"):
                    st.session_state["forgia_armi"].pop(idx)
                    st.session_state["forgia_version"] += 1
                    st.rerun()
                
                s1, s2, s3, s4, s5 = st.columns(5)
                atk = s1.selectbox("Attacks", opzioni_dadi, index=opzioni_dadi.index(str(arma.get("atk", "1"))) if str(arma.get("atk", "1")) in opzioni_dadi else 1, key=f"a_atk_{idx}_{v_key}")
                hit = s2.selectbox("Hit (X+)", opzioni_hw, index=opzioni_hw.index(arma.get("hit", 4)) if arma.get("hit", 4) in opzioni_hw else 3, key=f"a_hit_{idx}_{v_key}")
                wnd = s3.selectbox("Wound (X+)", opzioni_hw, index=opzioni_hw.index(arma.get("wnd", 4)) if arma.get("wnd", 4) in opzioni_hw else 3, key=f"a_wnd_{idx}_{v_key}")
                rend = s4.number_input("Rend", 0, 5, value=int(arma.get("rend", 0)) if str(arma.get("rend", 0)) != "---" else 0, key=f"a_rnd_{idx}_{v_key}")
                dmg = s5.selectbox("Damage", opzioni_dadi, index=opzioni_dadi.index(str(arma.get("dmg", "1"))) if str(arma.get("dmg", "1")) in opzioni_dadi else 1, key=f"a_dmg_{idx}_{v_key}")

                ab1, ab2, ab3, ab4, ab5 = st.columns(5)
                crit = ab1.selectbox("Critico", ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)"], index=["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)"].index(arma.get("crit_type", "Nessuno")), key=f"a_crt_{idx}_{v_key}")
                anti = ab2.selectbox("Anti-Keyword (+1 Rend)", ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER"], index=["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER"].index(arma.get("anti_target", "Nessuno")), key=f"a_ant_{idx}_{v_key}")
                ranged = ab3.checkbox("Arma da Tiro", value=arma.get("ranged", False), key=f"a_rng_{idx}_{v_key}")
                
                valore_gittata = arma.get("range", "12\"" if arma.get("ranged", False) else "Melee")
                gittata = ab4.text_input("Gittata (Range)", value=valore_gittata, key=f"a_ran_{idx}_{v_key}")
                
                comp = ab5.checkbox("Companion", value=arma.get("companion", False), key=f"a_cmp_{idx}_{v_key}")

                armi_aggiornate.append({
                    "nome": nome_a, "attiva": True, "ranged": ranged, "range": gittata, "atk": atk, "hit": hit, "wnd": wnd, "rend": rend, "dmg": dmg,
                    "crit_type": crit, "anti_target": anti, "charge_dmg": arma.get("charge_dmg", False), "anti_charge": arma.get("anti_charge", False), "companion": comp
                })
        st.session_state["forgia_armi"] = armi_aggiornate

    # ==========================================
    # ABILITÀ E KEYWORDS
    # ==========================================
    st.markdown('<div class="section-header">3. Abilità e Keywords</div>', unsafe_allow_html=True)
    with st.container(border=True):
        if st.button("➕ Aggiungi Abilità Warscroll"):
            st.session_state["forgia_abilita"].append({
                "nome": "Nuova Abilità", "tipo": "Ability", "reazione": False, "fasi": ["Qualsiasi Fase"], "descrizione": ""
            })
            st.session_state["forgia_version"] += 1
            st.rerun()

        abilita_aggiornate = []
        fasi_gioco = [
            "Qualsiasi Fase", "Deployment", "Hero Phase (Amica)", "Hero Phase (Nemica)", 
            "Movement Phase (Amica)", "Movement Phase (Nemica)", "Shooting Phase", 
            "Charge Phase", "Combat Phase", "Fine Turno"
        ]

        for a_idx, ab in enumerate(st.session_state["forgia_abilita"]):
            with st.expander(f"✨ {ab['nome']}", expanded=True):
                aa1, aa2 = st.columns([3, 1])
                nome_ab = aa1.text_input("Nome Abilità", value=ab["nome"], key=f"ab_nome_{a_idx}_{v_key}")
                if aa2.button("🗑️ Elimina", key=f"ab_del_{a_idx}_{v_key}"):
                    st.session_state["forgia_abilita"].pop(a_idx)
                    st.session_state["forgia_version"] += 1
                    st.rerun()

                r1, r2, r3 = st.columns([1, 1, 2])
                tipo = r1.selectbox("Tipo", ["Ability", "Passive", "Spell", "Prayer"], index=["Ability", "Passive", "Spell", "Prayer"].index(ab.get("tipo", "Ability")), key=f"ab_tipo_{a_idx}_{v_key}")
                reazione = r2.checkbox("È una Reazione (Reaction)?", value=ab.get("reazione", False), key=f"ab_reaz_{a_idx}_{v_key}")
                fasi_sel = r3.multiselect("Fasi di Attivazione", fasi_gioco, default=ab.get("fasi", ["Qualsiasi Fase"]), key=f"ab_fasi_{a_idx}_{v_key}")
                
                descrizione = st.text_area("Descrizione dell'Effetto", value=ab.get("descrizione", ""), key=f"ab_desc_{a_idx}_{v_key}")

                abilita_aggiornate.append({
                    "nome": nome_ab, "tipo": tipo, "reazione": reazione, "fasi": fasi_sel, "descrizione": descrizione
                })
        st.session_state["forgia_abilita"] = abilita_aggiornate

        st.markdown("---")
        kw_testo = st.text_input("Keywords (separate da virgola)", placeholder="es. Hero, Infantry, Wizard (1), Nighthaunt", value=st.session_state.get("forgia_keywords", ""), key=f"f_kw_{v_key}")

    # ==========================================
    # VALIDAZIONE E SALVATAGGIO
    # ==========================================
    if st.button("💾 Salva Unità nel Grimorio (Database)", type="primary", use_container_width=True):
        if not nome.strip() or nome == "--- Nuova Unità ---":
            st.error("Inserisci un Nome Unità valido.")
        else:
            chiave_db = f"{fazione}: {nome.strip()}"
            
            s_int = estrai_intero_da_stringa(save, default=7)
            w_int = estrai_intero_da_stringa(ward, default=7)
            
            lista_keywords = [kw.strip() for kw in kw_testo.split(",") if kw.strip()]

            struttura_unita = {
                "fazione": fazione,
                "n_modelli": n_modelli,
                "dimensione_basetta": basetta,
                "può_essere_rinforzata": puo_rinf,
                "campione": campione,
                "punti": punti,
                "statistiche_cerchio": {
                    "movimento": move,
                    "controllo": oc,
                    "save": save,
                    "salute": salute,
                    "ward": ward
                },
                "difesa": {
                    "salute_per_modello": salute,
                    "save": s_int,
                    "ward": w_int
                },
                "armi": st.session_state["forgia_armi"],
                "abilita": st.session_state["forgia_abilita"],
                "keywords": lista_keywords
            }

            st.session_state["db_unita"][chiave_db] = struttura_unita
            successo, messaggio = salva_nel_database(st.session_state["db_unita"])

            if successo:
                st.toast(f"Warscroll '{chiave_db}' registrata con successo nel Grimorio!")
            else:
                st.error(f"Errore di scrittura sul file: {messaggio}")