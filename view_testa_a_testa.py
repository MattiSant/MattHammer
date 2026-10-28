import streamlit as st
import numpy as np
import pandas as pd
from core_engine import (
    salva_nel_database,
    analizza_testo_copiato,
    calcola_arma_analitico,
    simula_monte_carlo
)

def render_testa_a_testa():
    st.title("MattHammer — Laboratorio Tattico")
    st.caption("Analizzatore duelli testa a testa e attacchi combinati multi-unità.")

    st.markdown("---")
    st.markdown("### 1. Unità da Analizzare")
    st.caption("Inserisci qui le statistiche dell'unità principale che vuoi testare in combattimento.")

    with st.container(border=True):
        st.subheader("Inserimento Rapido da Warscroll")
        st.caption("Copia il blocco di testo dal manuale o da Wahapedia e incollalo qui per compilare automaticamente le armi.")
        
        testo_copiato = st.text_area("Incolla qui il testo:", placeholder="Es: Arma Potente 5 3+ 3+ 2 2", height=80)
        
        if st.button("Applica ai Profili Attivi", type="primary"):
            armi_estratte = analizza_testo_copiato(testo_copiato)
            if armi_estratte:
                st.session_state["corrente_armi"] = armi_estratte
                st.session_state["form_version"] += 1
                st.success(f"Successo! Applicate {len(armi_estratte)} armi.")
                st.rerun()
            else:
                st.error("Nessun profilo arma riconosciuto.")

    col_armi, col_difesa_unita = st.columns(2)
    opzioni_dadi_atk_dmg = ["---", "1", "2", "3", "4", "5", "6", "7", "8", "10", "12", "14", "D3", "D3+1", "D6", "D6+1", "D6+2", "2D3", "2D6"]
    opzioni_hit_wnd = ["---", 2, 3, 4, 5, 6]
    opzioni_save = ["---", 2, 3, 4, 5, 6]
    opzioni_ward = ["---", 7, 6, 5, 4]

    v_key = st.session_state["form_version"]

    with col_armi:
        st.subheader("Profili Armi")
        st.caption("Verifica o modifica i valori di ciascuna arma.")
        if st.button("Aggiungi Nuova Arma"):
            st.session_state["corrente_armi"].append({
                "nome": "---", "attiva": True, "ranged": False, "atk": "---",
                "hit": "---", "wnd": "---", "rend": 0, "dmg": "---", "crit_type": "Nessuno",
                "anti_target": "Nessuno", "charge_dmg": False, "anti_charge": False, "companion": False
            })
            st.session_state["form_version"] += 1
            st.rerun()
            
        armi_aggiornate = []
        for idx, p_arma in enumerate(st.session_state["corrente_armi"]):
            with st.expander(f"Arma {idx+1}: {p_arma['nome']}", expanded=True):
                c1, c2, c3 = st.columns([2, 1, 1])
                nome_a = c1.text_input("Nome Arma", value=p_arma["nome"], key=f"nome_{idx}_v{v_key}")
                attiva_a = c2.checkbox("Attiva", value=p_arma["attiva"], key=f"att_{idx}_v{v_key}")
                comp_a = c3.checkbox("Companion", value=p_arma["companion"], key=f"comp_{idx}_v{v_key}")

                s1, s2, s3, s4, s5 = st.columns(5)
                atk_str = str(p_arma["atk"])
                idx_atk = opzioni_dadi_atk_dmg.index(atk_str) if atk_str in opzioni_dadi_atk_dmg else 0
                
                hit_val = p_arma["hit"]
                idx_hit = opzioni_hit_wnd.index(hit_val) if hit_val in opzioni_hit_wnd else 0
                
                wnd_val = p_arma["wnd"]
                idx_wnd = opzioni_hit_wnd.index(wnd_val) if wnd_val in opzioni_hit_wnd else 0
                
                rend_val = 0 if p_arma["rend"] == "---" else int(p_arma["rend"])
                
                dmg_str = str(p_arma["dmg"])
                idx_dmg = opzioni_dadi_atk_dmg.index(dmg_str) if dmg_str in opzioni_dadi_atk_dmg else 0

                atk_a = s1.selectbox("Attacks", opzioni_dadi_atk_dmg, index=idx_atk, key=f"atk_{idx}_v{v_key}")
                hit_a = s2.selectbox("Hit (X+)", opzioni_hit_wnd, index=idx_hit, key=f"hit_{idx}_v{v_key}")
                wnd_a = s3.selectbox("Wound (X+)", opzioni_hit_wnd, index=idx_wnd, key=f"wnd_{idx}_v{v_key}")
                rend_a = s4.number_input("Rend", 0, 5, value=rend_val, key=f"rend_{idx}_v{v_key}")
                dmg_a = s5.selectbox("Damage", opzioni_dadi_atk_dmg, index=idx_dmg, key=f"dmg_{idx}_v{v_key}")

                ab1, ab2, ab3 = st.columns(3)
                opz_crit = ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)", "Crit (2 Hits)"]
                opz_anti = ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE"]
                idx_crit = opz_crit.index(p_arma["crit_type"]) if p_arma["crit_type"] in opz_crit else 0
                idx_anti = opz_anti.index(p_arma["anti_target"]) if p_arma["anti_target"] in opz_anti else 0

                crit_a = ab1.selectbox("Abilità Critico", opz_crit, index=idx_crit, key=f"crit_{idx}_v{v_key}")
                anti_a = ab2.selectbox("Anti-X (+1 Rend)", opz_anti, index=idx_anti, key=f"anti_{idx}_v{v_key}")
                ranged_a = ab3.checkbox("Arma da Tiro", value=p_arma["ranged"], key=f"rng_{idx}_v{v_key}")

                ch1, ch2, ch_del = st.columns(3)
                chrg_dmg_a = ch1.checkbox("Charge (+1 Dmg)", value=p_arma["charge_dmg"], key=f"cdmg_{idx}_v{v_key}")
                anti_chrg_a = ch2.checkbox("Anti-Charge", value=p_arma["anti_charge"], key=f"achrg_{idx}_v{v_key}")
                if ch_del.button("Rimuovi Arma", key=f"del_{idx}_v{v_key}"):
                    st.session_state["corrente_armi"].pop(idx)
                    st.session_state["form_version"] += 1
                    st.rerun()

                armi_aggiornate.append({
                    "nome": nome_a, "attiva": attiva_a, "ranged": ranged_a,
                    "atk": atk_a, "hit": hit_a, "wnd": wnd_a, "rend": rend_a, "dmg": dmg_a,
                    "crit_type": crit_a, "anti_target": anti_a,
                    "charge_dmg": chrg_dmg_a, "anti_charge": anti_chrg_a, "companion": comp_a
                })
        st.session_state["corrente_armi"] = armi_aggiornate

    with col_difesa_unita:
        st.subheader("Caratteristiche Difensive Unità")
        st.caption("Imposta le statistiche difensive per ciascun modello dell'unità analizzata.")
        with st.container(border=True):
            d_corrente = st.session_state["corrente_difesa"]
            salute_modello = st.number_input("Punti Ferita per Modello", 0, 30, int(d_corrente.get("salute_per_modello", 0)), key=f"def_salute_v{v_key}")
            
            save_val = d_corrente.get("save", "---")
            idx_save = opzioni_save.index(save_val) if save_val in opzioni_save else 0
            save_nativo = st.selectbox("Tiro Salvezza Base (Save X+)", opzioni_save, index=idx_save, key=f"def_save_v{v_key}")
            
            ward_val = d_corrente.get("ward", "---")
            idx_ward = opzioni_ward.index(ward_val) if ward_val in opzioni_ward else 0
            ward_nativo = st.selectbox("Tiro Ward Nativo (X+)", opzioni_ward, index=idx_ward, format_func=lambda x: f"{x}+" if x != "---" else "--- (Non inserito)", key=f"def_ward_v{v_key}")
            
            st.session_state["corrente_difesa"] = {"salute_per_modello": salute_modello, "save": save_nativo, "ward": ward_nativo}

    col_comp, col_comandi = st.columns(2)
    with col_comp:
        st.subheader("Composizione Unità")
        st.caption("Indica quanti modelli compongono l'unità (o se è rinforzata) e il costo totale in punti.")
        with st.container(border=True):
            cs1, cs2 = st.columns(2)
            n_modelli_base = cs1.number_input("Modelli Base", min_value=0, max_value=60, value=int(st.session_state["corrente_modelli"]))
            rinforzata = cs2.checkbox("Rinforzata (x2)", value=False)
            n_modelli = n_modelli_base * 2 if rinforzata else n_modelli_base
            campione = st.checkbox("Presenza Campione (+1 Atk)", value=bool(st.session_state["corrente_campione"]))
            punti_unita = st.number_input("Costo in Punti Unità Principale", min_value=0, max_value=1500, value=int(st.session_state["corrente_punti"]) * (2 if rinforzata else 1), step=10)

    with col_comandi:
        st.subheader("Comandi e Buff")
        st.caption("Attiva se l'unità ha caricato, ha ricevuto comandi o beneficia di bonus speciali.")
        with st.container(border=True):
            ha_caricato = st.checkbox("L'unità ha Caricato questo turno", value=False)
            all_out_attack = st.checkbox("Comando: All-out Attack (+1 Hit)", value=False)
            with st.expander("Altri Buff / Modificatori"):
                mod_hit_extra = st.slider("Altri Modificatori Hit", -2, 2, 0)
                mod_wnd_extra = st.slider("Modificatori Wound", -2, 2, 0)
                bonus_atk = st.number_input("Bonus Attacchi", 0, 5, 0)
                bonus_rend = st.number_input("Bonus Rend Globale", 0, 3, 0)
                bonus_dmg = st.number_input("Bonus Danno Globale", 0, 3, 0)
                crit_on_5 = st.checkbox("Critico al 5+", value=False)

    st.subheader("Danni Aggiuntivi")
    st.caption("Aggiungi danni extra derivanti da abilità speciali o altre fonti esterne. Lascia a 0 se non applicabile.")
    with st.container(border=True):
        mortal_extra_dadi = 0
        mortal_extra_tipo = 6
        mortal_extra_soglia = "Nessuna (Somma i valori)"
        mortal_extra_fisso = 0
        
        st.markdown("**1. Parte Casuale**")
        c1, c2, c3 = st.columns(3)
        mortal_extra_dadi = c1.number_input("Numero Dadi", min_value=0, max_value=100, value=0)
        mortal_extra_tipo = c2.selectbox("Tipo Dado", [3, 6], index=1, format_func=lambda x: f"D{x}")
        mortal_extra_soglia = c3.selectbox("Valore di Successo", ["Nessuna (Somma i valori)", "2+", "3+", "4+", "5+", "6+"])
        
        st.markdown("**2. Parte Fissa**")
        mortal_extra_fisso = st.number_input("Numero fisso da aggiungere ai danni", min_value=0, max_value=100, value=0)

    mod_globali = {
        "n_modelli": n_modelli, "campione": campione, "ha_caricato": ha_caricato,
        "all_out_attack": all_out_attack, "mod_hit": mod_hit_extra + (1 if all_out_attack else 0),
        "mod_wnd": mod_wnd_extra, "bonus_atk": bonus_atk, "bonus_rend": bonus_rend,
        "bonus_dmg": bonus_dmg, "crit_on": 5 if crit_on_5 else 6,
        "mortal_extra_dadi": mortal_extra_dadi,
        "mortal_extra_tipo": mortal_extra_tipo,
        "mortal_extra_soglia": mortal_extra_soglia,
        "mortal_extra_fisso": mortal_extra_fisso
    }

    st.subheader("Forze di Supporto: Attacco Combinato (Opzionale)")
    st.caption("Seleziona una o più unità alleate dal Database per simulare un assalto coordinato contro lo stesso bersaglio. Tutti i grafici e le analisi rifletteranno la forza combinata.")
    with st.container(border=True):
        opzioni_supporto_db = [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]
        unita_supporto_scelte = st.multiselect(
            "Aggiungi unità alleate a supporto dell'attacco:",
            opzioni_supporto_db,
            default=[],
            key="multiselect_supporto"
        )
        
        config_supporti = []
        if unita_supporto_scelte:
            st.markdown("**Configurazione Rapida Unità di Supporto:**")
            for idx_sup, nome_sup in enumerate(unita_supporto_scelte):
                dati_sup = st.session_state["db_unita"][nome_sup]
                sc1, sc2, sc3, sc4 = st.columns([2, 1, 1, 1])
                sc1.markdown(f"**{nome_sup}** ({dati_sup.get('n_modelli', 1)} mod. base — {dati_sup.get('punti', 0)} pt)")
                rinf_sup = sc2.checkbox("Rinforzata (x2)", value=False, key=f"sup_rinf_{idx_sup}")
                carica_sup = sc3.checkbox("Ha Caricato", value=ha_caricato, key=f"sup_chg_{idx_sup}")
                aoa_sup = sc4.checkbox("All-out Attack (+1 Hit)", value=False, key=f"sup_aoa_{idx_sup}")
                
                n_mod_sup = int(dati_sup.get("n_modelli", 1)) * (2 if rinf_sup else 1)
                punti_sup = int(dati_sup.get("punti", 0)) * (2 if rinf_sup else 1)
                
                config_supporti.append({
                    "nome_unita": nome_sup,
                    "armi": [dict(a) for a in dati_sup.get("armi", [])],
                    "punti": punti_sup,
                    "difesa": dati_sup.get("difesa", {"salute_per_modello": 1, "save": 4, "ward": 7}),
                    "mod_globali": {
                        "n_modelli": n_mod_sup,
                        "campione": bool(dati_sup.get("campione", False)),
                        "ha_caricato": carica_sup,
                        "all_out_attack": aoa_sup,
                        "mod_hit": 1 if aoa_sup else 0,
                        "mod_wnd": 0, "bonus_atk": 0, "bonus_rend": 0, "bonus_dmg": 0,
                        "crit_on": 6,
                        "mortal_extra_dadi": 0, "mortal_extra_tipo": 6,
                        "mortal_extra_soglia": "Nessuna (Somma i valori)", "mortal_extra_fisso": 0
                    }
                })

    st.subheader("Salva Unità nel Database Locale")
    st.caption("Seleziona la fazione, dai un nome all'unità principale e salvala per poterla ricaricare rapidamente in futuro.")
    with st.container(border=True):
        db_c1, db_c2 = st.columns(2)
        fazione_scelta = db_c1.selectbox("Seleziona Fazione", ["---", "Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Personale / Altro"])
        nuovo_nome = db_c2.text_input("Nome Specifico dell'Unità:", placeholder="Es. Spirit Hosts")
        
        if st.button("Valida e Salva nel DB", type="primary"):
            errori = []
            if fazione_scelta == "---": errori.append("Seleziona una fazione valida.")
            if not nuovo_nome.strip() or nuovo_nome == "---": errori.append("Inserisci un nome valido per l'unità.")
            if n_modelli <= 0: errori.append("Il numero di modelli deve essere maggiore di zero.")
            if punti_unita <= 0: errori.append("Il costo in punti deve essere specificato.")
            
            difesa_corrente = st.session_state["corrente_difesa"]
            if difesa_corrente.get("salute_per_modello") <= 0 or difesa_corrente.get("save") == "---":
                errori.append("I dati difensivi (Salute o Save) contengono campi non inseriti ('---').")
                
            for idx, arm in enumerate(st.session_state["corrente_armi"]):
                if arm["attiva"] and (str(arm["hit"]) == "---" or str(arm["wnd"]) == "---" or str(arm["atk"]) == "---" or str(arm["dmg"]) == "---"):
                    errori.append(f"L'Arma {idx+1} ({arm['nome']}) ha parametri non compilati ('---').")

            if len(errori) > 0:
                for err in errori: st.error(f"Errore: {err}")
            else:
                chiave_db = f"{fazione_scelta}: {nuovo_nome.strip()}"
                gia_esistente = chiave_db in st.session_state["db_unita"]

                st.session_state["db_unita"][chiave_db] = {
                    "fazione": fazione_scelta, 
                    "n_modelli": n_modelli_base, 
                    "campione": campione, 
                    "punti": int(punti_unita / (2 if rinforzata else 1)), 
                    "difesa": difesa_corrente, 
                    "armi": st.session_state["corrente_armi"]
                }

                successo, messaggio = salva_nel_database(st.session_state["db_unita"])
                    
                if successo:
                    if gia_esistente:
                        st.toast(f"Unità '{chiave_db}' aggiornata con successo (sovrascritta)!")
                    else:
                        st.toast(f"Nuova unità '{chiave_db}' aggiunta con successo al database!")
                    st.rerun()
                else:
                    st.error(f"Errore durante il salvataggio: {messaggio}")

    st.markdown("---")
    st.markdown("### 2. Unità Bersaglio")
    st.caption("Configura le difese, il costo in punti, i terreni (Cover) e i debuff dell'unità nemica che vuoi attaccare.")
    with st.container(border=True):
        st.markdown("**Importa Bersaglio dal Database:**")
        tb_col1, tb_col2, tb_col3 = st.columns([2, 1, 1])
        opzioni_bersaglio_db = ["--- Inserimento Manuale ---"] + [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]
        bersaglio_scelto_db = tb_col1.selectbox("Seleziona un'unità dal DB per caricarne le difese e i punti:", opzioni_bersaglio_db, key="sel_target_db")
        bersaglio_rinforzato_db = tb_col2.checkbox("Bersaglio Rinforzato (x2 modelli/punti)", value=False, key="chk_target_rinf")
        
        if tb_col3.button("Applica Dati Bersaglio", type="primary"):
            if bersaglio_scelto_db != "--- Inserimento Manuale ---":
                dati_b_db = st.session_state["db_unita"][bersaglio_scelto_db]
                dif_b_db = dati_b_db.get("difesa", {})
                
                sv_raw = dif_b_db.get("save", 4)
                st.session_state["bersaglio_save"] = int(sv_raw) if str(sv_raw).isdigit() and int(sv_raw) in [2, 3, 4, 5, 6, 7] else 7
                
                wd_raw = dif_b_db.get("ward", 7)
                st.session_state["bersaglio_ward"] = int(wd_raw) if str(wd_raw).isdigit() and int(wd_raw) in [4, 5, 6, 7] else 7
                
                moltiplicatore_rinf_b = 2 if bersaglio_rinforzato_db else 1
                mod_b = max(1, int(dati_b_db.get("n_modelli", 1))) * moltiplicatore_rinf_b
                sal_mod_b = max(1, int(dif_b_db.get("salute_per_modello", 1)))
                st.session_state["bersaglio_salute"] = min(200, mod_b * sal_mod_b)
                st.session_state["bersaglio_punti"] = int(dati_b_db.get("punti", 0)) * moltiplicatore_rinf_b
                st.session_state["bersaglio_nome_db"] = bersaglio_scelto_db + (" (Rinforzata)" if bersaglio_rinforzato_db else "")
                
                st.session_state["target_version"] += 1
                st.toast(f"Statistiche e punti di '{bersaglio_scelto_db}' caricati nel Bersaglio!")
                st.rerun()

        st.markdown("---")
        tv_key = st.session_state["target_version"]
        b1, b2, b3, b4 = st.columns(4)
        
        lista_saves_b = [2, 3, 4, 5, 6, 7]
        idx_save_b = lista_saves_b.index(st.session_state["bersaglio_save"]) if st.session_state["bersaglio_save"] in lista_saves_b else 2
        save_b = b1.selectbox("Save Base Bersaglio", lista_saves_b, index=idx_save_b, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)", key=f"sb_v{tv_key}")
        
        lista_wards_b = [7, 6, 5, 4]
        idx_ward_b = lista_wards_b.index(st.session_state["bersaglio_ward"]) if st.session_state["bersaglio_ward"] in lista_wards_b else 0
        ward_b = b2.selectbox("Ward Base Bersaglio", lista_wards_b, index=idx_ward_b, format_func=lambda x: f"{x}+" if x < 7 else "Nessuno (-)", key=f"wb_v{tv_key}")
        
        salute_b = b3.number_input("Salute Totale Bersaglio", min_value=1, max_value=200, value=int(st.session_state["bersaglio_salute"]), key=f"salb_v{tv_key}")
        punti_bersaglio = b4.number_input("Costo in Punti Bersaglio", min_value=0, max_value=2000, value=int(st.session_state["bersaglio_punti"]), step=10, key=f"ptb_v{tv_key}")
        
        st.session_state["bersaglio_save"] = save_b
        st.session_state["bersaglio_ward"] = ward_b
        st.session_state["bersaglio_salute"] = salute_b
        st.session_state["bersaglio_punti"] = punti_bersaglio

        keywords_b = st.multiselect("Keywords del Bersaglio", ["INFANTRY", "HERO", "CAVALRY", "MONSTER", "WAR MACHINE"], default=["INFANTRY", "HERO"])

        st.markdown("---")
        st.markdown("**Buff Difensivi del Bersaglio:**")
        dt1, dt2, dt3 = st.columns(3)
        cover_b = dt1.checkbox("Cover (+1 Save)", value=False)
        aod_b = dt2.checkbox("All-out Defence (+1 Save)", value=False)
        extra_save_b = dt3.checkbox("Abilità extra / Scenario (+1 Save)", value=False)
        obscuring_b = dt1.checkbox("Terreno Obscuring (-1 Hit al tiro)", value=False)
        bersaglio_carica = dt2.checkbox("Il Bersaglio ha Caricato", value=False)

        st.markdown("---")
        st.markdown("**Debuff applicati al Bersaglio:**")
        nd1, nd2, nd3 = st.columns(3)
        debuff_ward = nd1.checkbox("Debuff: -1 al tiro Ward", value=False)
        blocca_ward_b = nd2.checkbox("Ward Annullati", value=False)
        nerf_wound = nd3.selectbox("Modificatore Wound subito dal bersaglio", [0, 1, -1], index=0, format_func=lambda x: f"+{x} a Wound" if x>0 else (f"{x} a Wound" if x<0 else "Nessuno"))

    bersaglio_dict = {
        "save": save_b, "ward": ward_b, "salute": salute_b, "keywords": keywords_b,
        "cover": cover_b, "aod": aod_b, "bonus_save_extra": 1 if extra_save_b else 0,
        "obscuring": obscuring_b, "bersaglio_ha_caricato": bersaglio_carica,
        "mod_ward_penalita": 1 if debuff_ward else 0,
        "blocca_ward": blocca_ward_b, "mod_wnd_nerf": nerf_wound
    }
    mod_globali["bersaglio_ha_caricato"] = bersaglio_carica
    for sup in config_supporti:
        sup["mod_globali"]["bersaglio_ha_caricato"] = bersaglio_carica

    armi_attive_calcolo = st.session_state["corrente_armi"]
    risultati_armi_principale = [calcola_arma_analitico(a, mod_globali, bersaglio_dict) for a in armi_attive_calcolo]

    dettaglio_armi_combinate = []
    for a, r in zip(armi_attive_calcolo, risultati_armi_principale):
        dettaglio_armi_combinate.append({
            "fonte": "Unità Principale",
            "arma": a,
            "risultato": r
        })

    for sup in config_supporti:
        for a_sup in sup["armi"]:
            r_sup = calcola_arma_analitico(a_sup, sup["mod_globali"], bersaglio_dict)
            dettaglio_armi_combinate.append({
                "fonte": sup["nome_unita"],
                "arma": a_sup,
                "risultato": r_sup
            })

    risultati_armi = [item["risultato"] for item in dettaglio_armi_combinate]
    danno_atteso_armi = sum(r["danno_netto"] for r in risultati_armi)

    ward_eff = bersaglio_dict["ward"] + bersaglio_dict["mod_ward_penalita"]
    moltiplicatore_ward = 0.0 if bersaglio_dict["blocca_ward"] else (1.0 if (bersaglio_dict["ward"] >= 7 or ward_eff > 6) else 1.0 - ((7 - max(2, ward_eff)) / 6.0))

    danno_extra_base = float(mortal_extra_fisso)
    if mortal_extra_dadi > 0:
        if mortal_extra_soglia == "Nessuna (Somma i valori)":
            danno_extra_base += mortal_extra_dadi * (2.0 if mortal_extra_tipo == 3 else 3.5)
        else:
            target_val = int(mortal_extra_soglia[0])
            prob = max(0.0, (mortal_extra_tipo - target_val + 1) / float(mortal_extra_tipo))
            danno_extra_base += mortal_extra_dadi * prob

    danno_extra_atteso = danno_extra_base * moltiplicatore_ward
    danno_totale_atteso = danno_atteso_armi + danno_extra_atteso

    n_simulazioni = 10000
    campioni_mc = simula_monte_carlo(armi_attive_calcolo, mod_globali, bersaglio_dict, n_sim=n_simulazioni)
    for sup in config_supporti:
        campioni_mc += simula_monte_carlo(sup["armi"], sup["mod_globali"], bersaglio_dict, n_sim=n_simulazioni)

    prob_uccisione = np.mean(campioni_mc >= salute_b) * 100.0
    dev_std = np.std(campioni_mc)

    punti_supporto_totali = sum(sup["punti"] for sup in config_supporti)
    punti_attaccante_totali = punti_unita + punti_supporto_totali
    roi_punti = (danno_totale_atteso / punti_attaccante_totali) * 100.0 if punti_attaccante_totali > 0 else 0.0

    st.markdown("---")
    st.markdown("### 3. Risultati e Statistiche di Combattimento")
    st.caption("Esamina il verdetto strategico, la distribuzione matematica dei danni e la convenienza in punti dell'ingaggio.")

    attacchi_totali = sum(r['attacchi'] for r in risultati_armi)
    tutte_armi_attive = [item["arma"] for item in dettaglio_armi_combinate if item["arma"]["attiva"] and str(item["arma"]["hit"]) != "---"]
    max_rend = max([int(a['rend']) for a in tutte_armi_attive if str(a['rend']) != "---"] + [0])
    ha_crit_mortal = any(a['crit_type'] == 'Crit (Mortal)' for a in tutte_armi_attive)
    anti_targets = list(set([a['anti_target'] for a in tutte_armi_attive if a['anti_target'] != 'Nessuno']))

    difesa_corrente = st.session_state["corrente_difesa"]
    ward_unita = int(difesa_corrente.get("ward", 7)) if difesa_corrente.get("ward") != "---" else 7
    save_unita = int(difesa_corrente.get("save", 4)) if difesa_corrente.get("save") != "---" else 4
    salute_totale_unita = int(difesa_corrente.get("salute_per_modello", 2)) * mod_globali["n_modelli"]

    ruoli_trovati = []
    if ward_unita <= 5 or (save_unita <= 3 and salute_totale_unita >= 15):
        ruoli_trovati.append("**Ancoraggio Difensivo (Tank)**: Ottima resistenza. Utilizza questa unità per presidiare gli obiettivi centrali o fare da scudo.")
    if len(anti_targets) > 0:
        targets_str = ", ".join(anti_targets)
        ruoli_trovati.append(f"**Specialista Anti-{targets_str}**: Letale contro questi bersagli specifici grazie al bonus di penetrazione.")
    if attacchi_totali >= 20:
        ruoli_trovati.append("**Sfoltiscitore d'Orde**: Sfrutta l'enorme volume di dadi per saturare difese nemiche leggere.")
    if ha_crit_mortal or max_rend >= 2:
        ruoli_trovati.append("**Bypassa-Armatura**: Eccelle contro bersagli con armature pesanti (Tiro Salvezza elevato).")
    if danno_totale_atteso >= 12:
        ruoli_trovati.append("**Damage Dealer Puro**: Forza d'urto ad altissimo impatto offensivo. Scatenala contro le minacce principali.")
    if not ruoli_trovati:
        ruoli_trovati.append("**Combattente Flessibile / Supporto**: Unità tattica bilanciata per contestare obiettivi secondari o schermare.")

    with st.container(border=True):
        if config_supporti:
            nomi_sup_str = ", ".join([s["nome_unita"] for s in config_supporti])
            st.markdown(f"**Modalità Attacco Combinato Attiva:** Unità Principale + *{nomi_sup_str}* (Totale investito: **{punti_attaccante_totali} pt**)")
            st.markdown("---")
        st.markdown("**Il Verdetto Strategico (Ruoli individuati):**")
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
        tot_mortal_crit = sum(r["mortal"] for r in risultati_armi)

        col_t1, col_t2 = st.columns(2)
        with col_t1:
            st.subheader("Ripartizione Danni per Arma")
            st.caption("Dettaglio matematico del rendimento di ogni singola arma attiva nell'ingaggio.")
            righe_armi = []
            for item in dettaglio_armi_combinate:
                a = item["arma"]
                r = item["risultato"]
                fonte = item["fonte"]
                if a["attiva"] and str(a["hit"]) != "---" and str(a["atk"]) != "---":
                    etichetta_arma = f"{a['nome']} ({fonte})" if len(config_supporti) > 0 else a["nome"]
                    righe_armi.append({
                        "Arma": etichetta_arma, "Attacchi": round(r["attacchi"], 1),
                        "Hits": round(r["hits"], 2), "Wounds": round(r["wounds"], 2),
                        "Save Falliti": round(r["unsaved"], 2), "Danno Netto": round(r["danno_netto"], 2)
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
                            f"La dispersione maggiore avviene quando cerchi di colpire (**-{drop_hit:.1f}%** di dadi persi). "
                            + ("Hai già *All-out Attack* attivo sull'unità principale!" if all_out_attack else "Attivare **All-out Attack (+1 Hit)** è l'investimento di Punti Comando più redditizio.")
                        )
                    elif max_drop == drop_wnd:
                        fase_critica = "Fase 2 -> 3 (Tiro per Ferire / Wound)"
                        consiglio_cp = (
                            "**Investi in Fase di Wound (Buff al Ferire):** "
                            f"Colpisci bene ma perdi il **{drop_wnd:.1f}%** cercando di ferire. Usa abilità o preghiere per alzare il Wound."
                        )
                    else:
                        fase_critica = "Fase 3 -> 4 (Tiro Salvezza Nemico / Save)"
                        consiglio_cp = (
                            "**Investi in Penetrazione (Rend) o Mortal Wounds:** "
                            f"L'armatura avversaria sta assorbendo il **{drop_save:.1f}%** delle tue ferite! Investi in buff al Rend o Mortal Wounds."
                        )

                    with st.container(border=True):
                        st.markdown("#### Guida all'Interpretazione & Analisi Tattica del Flusso")
                        st.markdown(
                            f"**Dadi vs Danni Reali:**\n"
                            f"1. **Attacchi ({tot_atk:.1f}):** Dadi lanciati.\n"
                            f"2. **Colpi ({tot_hits:.2f}):** A segno (persi: {drop_hit:.1f}%).\n"
                            f"3. **Ferite ({tot_wounds:.2f}):** Ferite con successo (perse: {drop_wnd:.1f}%).\n"
                            f"4. **Non Salvati ({tot_unsaved:.2f}):** Bucano l'armatura (parati: {drop_save:.1f}%).\n"
                            f"5. **Danno Finale ({danno_totale_atteso:.2f}):** Moltiplicato per Damage ed extra"
                            + (f", ridotto dal Ward nemico." if moltiplicatore_ward < 1.0 else ".")
                        )
                        st.markdown("---")
                        st.markdown(f"**Collo di Bottiglia Individuato:** `{fase_critica}`")
                        st.markdown(consiglio_cp)
            else:
                st.info("Inserisci i dati dell'unità e attiva almeno un'arma per vedere il dettaglio.")

        with col_t2:
            st.subheader("Scomposizione del Flusso d'Attacco")
            st.caption("Mostra quanti colpi sopravvivono progressivamente fino al Danno Netto finale.")
            
            if tot_atk > 0:
                df_perdite = pd.DataFrame({
                    "Fase": ["1. Attacchi", "2. Colpi (Hit)", "3. Ferite (Wound)", "4. Non Salvati", "5. Danno Netto"],
                    "Valore": [round(tot_atk, 1), round(tot_hits, 1), round(tot_wounds, 1), round(tot_unsaved, 1), round(danno_totale_atteso, 1)]
                })
                st.bar_chart(df_perdite.set_index("Fase"), x_label="Fase della Sequenza d'Attacco", y_label="Numero di Dadi / Danni Inflitti", color="#b38b4d")
            else:
                st.warning("Dati non ancora inseriti o incompleti. Compila i campi dell'unità.")

    with tab2:
        st.subheader("Curva di Probabilità Cumulativa")
        st.caption("Stima la probabilità di infliggere almeno X danni totali.")
        max_danno_grafico = int(np.percentile(campioni_mc, 99.5)) + 2 if len(campioni_mc) > 0 else 10
        asse_x = np.arange(1, max(10, max_danno_grafico))
        prob_almeno_x = [np.mean(campioni_mc >= x) * 100.0 for x in asse_x]
        st.line_chart(
            pd.DataFrame({"Danni Minimi (X)": asse_x, "Probabilità (%)": prob_almeno_x}).set_index("Danni Minimi (X)"),
            x_label="Danni Minimi Inflitti",
            y_label="Probabilità di Successo (%)",
            color="#b38b4d"
        )

    with tab3:
        st.subheader("Stima Sopravvivenza Bersaglio (Time-to-Kill)")
        st.caption("Valuta quanti turni di combattimento sono necessari per eliminare il bersaglio.")
        ttk = salute_b / danno_totale_atteso if danno_totale_atteso > 0 else 99
        
        if ttk <= 1.0:
            st.success(f"**Esito Letale:** Eliminazione attesa in **1 singolo turno** (Danno {danno_totale_atteso:.1f} vs Salute {salute_b}).")
        elif ttk <= 2.0:
            st.warning(f"**Scontro di Logoramento:** Necessari circa **2 turni** per abbattere il bersaglio (Danno {danno_totale_atteso:.1f} vs Salute {salute_b}).")
        else:
            st.error(f"**Attacco Inefficiente:** Serviranno circa **{int(ttk)+1} turni**. Sconsigliato ingaggiare senza supporto.")

        st.markdown("---")
        st.subheader("Bilancio Economico e Valutazione d'Ingaggio (Confronto Punti)")
        st.caption("Analizza il rapporto tra punti investiti e valore del bersaglio.")
        
        with st.container(border=True):
            if punti_attaccante_totali > 0 and punti_bersaglio > 0:
                rapporto_punti = punti_attaccante_totali / float(punti_bersaglio)
                percentuale_vita_tolta = min(1.0, danno_totale_atteso / float(salute_b)) if salute_b > 0 else 0.0
                punti_neutralizzati_stimati = punti_bersaglio * percentuale_vita_tolta
                efficienza_scambio = (punti_neutralizzati_stimati / float(punti_attaccante_totali)) * 100.0

                ec1, ec2, ec3 = st.columns(3)
                ec1.markdown(f"**Punti Attaccanti:** `{punti_attaccante_totali} pt`")
                ec2.markdown(f"**Valore Bersaglio:** `{punti_bersaglio} pt`")
                ec3.markdown(f"**Valore Neutralizzato (1 Turno):** `{punti_neutralizzati_stimati:.0f} pt` ({percentuale_vita_tolta*100:.0f}% vita)")
                st.markdown("---")

                if ttk <= 1.0 and rapporto_punti <= 1.0:
                    st.success(f"**VERDETTO: SCAMBIO ALTAMENTE VANTAGGIOSO (Trade-Up)**\n\nImpegni {punti_attaccante_totali} pt per spazzare via {punti_bersaglio} pt in 1 turno. Vantaggio netto di {punti_bersaglio - punti_attaccante_totali} pt. Ingaggio fortemente consigliato.")
                elif ttk <= 1.0 and rapporto_punti <= 1.5:
                    st.success(f"**VERDETTO: ELIMINAZIONE AFFIDABILE E CONVENIENTE**\n\nEliminazione immediata garantita (Kill: {prob_uccisione:.1f}%). Eviti il contrattacco nemico, mossa solida.")
                elif ttk <= 1.0 and rapporto_punti > 1.5:
                    st.warning(f"**VERDETTO: SOVRACCOSTO TATTICO (Overkill)**\n\nConcentri {punti_attaccante_totali} pt contro un bersaglio da appena {punti_bersaglio} pt. Verifica di non sguarnire gli obiettivi.")
                elif ttk <= 1.8 and rapporto_punti <= 1.1:
                    st.info(f"**VERDETTO: INGAGGIO EQUILIBRATO DI LOGORAMENTO**\n\nPunti bilanciati ({punti_attaccante_totali} pt vs {punti_bersaglio} pt). Neutralizzi ~{punti_neutralizzati_stimati:.0f} pt in 1 turno.")
                else:
                    st.error(f"**VERDETTO: TRAPPOLA TATTICA (Alto Rischio)**\n\nNeutralizzi solo {punti_neutralizzati_stimati:.0f} pt al Turno 1 (indice: {efficienza_scambio:.0f}%). Le tue truppe rischiano di restare bloccate per {int(ttk)+1} turni.")
            else:
                st.info("Specifica sia il **Costo in Punti dell'Unità Principale** sia il **Costo in Punti del Bersaglio** per visualizzare l'analisi economica.")

        st.markdown("---")
        st.subheader("Matrice Target Priority")
        st.caption("Confronta il danno netto atteso contro tutte le combinazioni di Save e Ward.")
        saves_lista = [2, 3, 4, 5, 6, 7]
        wards_lista = [7, 6, 5, 4]
        matrice_dati = {}
        for w_val in wards_lista:
            col_nome = f"Ward {w_val}+" if w_val < 7 else "Nessun Ward"
            col_valori = []
            for s_val in saves_lista:
                b_temp = {**bersaglio_dict, "save": s_val, "ward": w_val, "blocca_ward": False}
                danno_armi_mat = sum(calcola_arma_analitico(a, mod_globali, b_temp)["danno_netto"] for a in armi_attive_calcolo)
                for sup in config_supporti:
                    danno_armi_mat += sum(calcola_arma_analitico(a_sup, sup["mod_globali"], b_temp)["danno_netto"] for a_sup in sup["armi"])
                col_valori.append(round(danno_armi_mat, 2))
            matrice_dati[col_nome] = col_valori
        df_matrice = pd.DataFrame(matrice_dati, index=[f"Save {s}+" if s < 7 else "No Save (-)" for s in saves_lista])
        
        st.dataframe(df_matrice.style.background_gradient(cmap="YlOrBr", low=0.1, high=0.8), use_container_width=True)