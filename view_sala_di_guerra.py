import streamlit as st
import numpy as np
import pandas as pd
import json
import os
from core_engine import calcola_arma_analitico

ARMIES_DB_FILE = "armies_db.json"

# ==========================================
# GESTIONE ARCHIVIO LISTE ARMATE (JSON)
# ==========================================
def carica_archivio_armate():
    if os.path.exists(ARMIES_DB_FILE):
        try:
            with open(ARMIES_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def salva_archivio_armate(armate_dict):
    with open(ARMIES_DB_FILE, "w", encoding="utf-8") as f:
        json.dump(armate_dict, f, indent=4, ensure_ascii=False)
    return True

# ==========================================
# FUNZIONI DI SUPPORTO PER ANALISI ROSTER
# ==========================================
def stima_controllo_unita(ruolo, n_modelli):
    if ruolo == "Mostro (5 OC)":
        return 5 * max(1, n_modelli)
    elif ruolo == "Eroe (2 OC)":
        return 2 * max(1, n_modelli)
    elif ruolo == "Cavalleria / Élite (2 OC/mod)":
        return 2 * n_modelli
    elif ruolo == "Macchina da Guerra (3 OC)":
        return 3 * max(1, n_modelli)
    else:  # Fanteria Standard (1 OC/mod)
        return 1 * n_modelli

def calcola_output_unita_su_bersaglio(dati_unita_db, rinforzata, bersaglio_test):
    armi = dati_unita_db.get("armi", [])
    n_mod_base = max(1, int(dati_unita_db.get("n_modelli", 1)))
    n_mod = n_mod_base * (2 if rinforzata else 1)
    campione = bool(dati_unita_db.get("campione", False))

    mod_glob = {
        "n_modelli": n_mod, "campione": campione, "ha_caricato": True,
        "all_out_attack": False, "mod_hit": 0, "mod_wnd": 0,
        "bonus_atk": 0, "bonus_rend": 0, "bonus_dmg": 0, "crit_on": 6,
        "bersaglio_ha_caricato": False
    }

    danno_melee = 0.0
    danno_ranged = 0.0
    max_rend = 0
    attacchi_tot = 0.0

    for a in armi:
        if a.get("attiva", False) and str(a.get("hit", "---")) != "---":
            ris = calcola_arma_analitico(a, mod_glob, bersaglio_test)
            if a.get("ranged", False):
                danno_ranged += ris["danno_netto"]
            else:
                danno_melee += ris["danno_netto"]
            attacchi_tot += ris["attacchi"]
            r_val = 0 if str(a.get("rend", 0)) == "---" else int(a.get("rend", 0))
            if r_val > max_rend:
                max_rend = r_val

    return {
        "danno_melee": danno_melee,
        "danno_ranged": danno_ranged,
        "danno_totale": danno_melee + danno_ranged,
        "max_rend": max_rend,
        "attacchi_tot": attacchi_tot
    }


# ==========================================
# VISTA PRINCIPALE: SALA DI GUERRA
# ==========================================
def render_sala_di_guerra():
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
            border-bottom: 1px dashed rgba(230, 198, 101, 0.45);
            padding-bottom: 3px;
            margin-bottom: 6px;
        }
        div[data-testid="stContainer"] .subsection-title {
            color: #5a3c1e !important;
            border-bottom: 1px dashed rgba(90, 60, 30, 0.4);
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("MattHammer — Sala di Guerra")
    st.caption("Costruttore d'armata per Reggimenti (AoS 4e), diagnosi strategica dei ruoli e simulatore di Match-Up contro liste avversarie.")

    # Inizializzazione Stati della Sala di Guerra
    if "archivio_armate" not in st.session_state:
        st.session_state["archivio_armate"] = carica_archivio_armate()

    if "sdg_nome_armata" not in st.session_state:
        st.session_state["sdg_nome_armata"] = "Schieramento da Guerra"
    if "sdg_fazione_armata" not in st.session_state:
        st.session_state["sdg_fazione_armata"] = "Nighthaunt"
    if "sdg_formazione_battaglia" not in st.session_state:
        st.session_state["sdg_formazione_battaglia"] = "Formazione Standard"

    if "sdg_reggimenti" not in st.session_state:
        st.session_state["sdg_reggimenti"] = [
            {
                "leader": "--- Scegli Eroe Leader ---",
                "is_generale": True,
                "rinforzato": False,
                "tratto_eroico": "Nessuno",
                "artefatto": "Nessuno",
                "livello_mago": 0,
                "livello_prete": 0,
                "seguito": []
            }
        ]

    if "sdg_ausiliari" not in st.session_state:
        st.session_state["sdg_ausiliari"] = []

    if "sdg_nemici_matchup" not in st.session_state:
        st.session_state["sdg_nemici_matchup"] = []

    opzioni_db = [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]

    # ==========================================
    # SEZIONE 1: FORMATO BATTAGLIA E ARCHIVIO ROSTER
    # ==========================================
    st.markdown('<div class="section-header">Configurazione Schieramento e Vincoli 4e</div>', unsafe_allow_html=True)
    st.caption("Seleziona il formato punti della partita, imposta i dettagli della tua armata o carica una lista salvata in precedenza.")

    with st.container(border=True):
        st.markdown('<div class="subsection-title">Parametri Generali dell\'Armata</div>', unsafe_allow_html=True)
        st.caption("Definisci nome, fazione di appartenenza e tetto massimo di punti per la convalida dello schieramento.")

        col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.2, 1.3, 1])
        st.session_state["sdg_nome_armata"] = col_f1.text_input("Nome della Lista / Armata", value=st.session_state["sdg_nome_armata"])
        
        lista_fazioni_disp = ["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", " Grande Alleanza / Mista"]
        idx_faz = lista_fazioni_disp.index(st.session_state["sdg_fazione_armata"]) if st.session_state["sdg_fazione_armata"] in lista_fazioni_disp else 0
        st.session_state["sdg_fazione_armata"] = col_f2.selectbox("Fazione d'Armata", lista_fazioni_disp, index=idx_faz)

        formato_scelto = col_f3.selectbox(
            "Formato Battaglia (AoS 4e)",
            ["Path to Glory (600 pt)", "Vanguard (1000 pt)", "Strike Force (1500 pt)", "Battlehost (2000 pt)", "Personalizzato"],
            index=3
        )

        if "600" in formato_scelto:
            limite_punti = 600
            max_reggimenti = 3
        elif "1000" in formato_scelto:
            limite_punti = 1000
            max_reggimenti = 3
        elif "1500" in formato_scelto:
            limite_punti = 1500
            max_reggimenti = 4
        elif "2000" in formato_scelto:
            limite_punti = 2000
            max_reggimenti = 5
        else:
            limite_punti = col_f4.number_input("Limite Punti Custom", min_value=300, max_value=5000, value=2000, step=50)
            max_reggimenti = 5

        if "Personalizzato" not in formato_scelto:
            st.session_state["sdg_formazione_battaglia"] = col_f4.text_input("Formazione di Battaglia", value=st.session_state["sdg_formazione_battaglia"])

        # Gestione Caricamento / Reset Rapido Armata
        with st.expander("Archivio Liste Salvate (Carica o Elimina Roster)"):
            nomi_armate_salvate = list(st.session_state["archivio_armate"].keys())
            if nomi_armate_salvate:
                ca1, ca2, ca3 = st.columns([2, 1, 1])
                armata_sel_archivio = ca1.selectbox("Seleziona una lista salvata:", nomi_armate_salvate, key="sel_load_army")
                if ca2.button("Carica Lista", type="primary", use_container_width=True):
                    dati_arm = st.session_state["archivio_armate"][armata_sel_archivio]
                    st.session_state["sdg_nome_armata"] = dati_arm.get("nome", armata_sel_archivio)
                    st.session_state["sdg_fazione_armata"] = dati_arm.get("fazione", "Nighthaunt")
                    st.session_state["sdg_formazione_battaglia"] = dati_arm.get("formazione", "Formazione Standard")
                    st.session_state["sdg_reggimenti"] = dati_arm.get("reggimenti", [])
                    st.session_state["sdg_ausiliari"] = dati_arm.get("ausiliari", [])
                    st.toast(f"Armata '{armata_sel_archivio}' caricata nella Sala di Guerra!")
                    st.rerun()
                if ca3.button("Elimina Lista dall'Archivio", use_container_width=True):
                    del st.session_state["archivio_armate"][armata_sel_archivio]
                    salva_archivio_armate(st.session_state["archivio_armate"])
                    st.rerun()
            else:
                st.caption("Nessuna lista d'armata ancora salvata nell'archivio locale.")

    # ==========================================
    # SEZIONE 2: COMPOSIZIONE REGGIMENTI E AUSILIARI
    # ==========================================
    st.markdown('<div class="section-header">Composizione dei Reggimenti</div>', unsafe_allow_html=True)
    st.caption("Organizza l'esercito in Reggimenti guidati da un Eroe (Leader) e assegna Tratti Eroici, Artefatti di Potere e unità di Seguito.")

    col_btn_reg1, col_btn_reg2 = st.columns([1, 3])
    if col_btn_reg1.button("➕ Aggiungi Nuovo Reggimento", type="primary", use_container_width=True):
        st.session_state["sdg_reggimenti"].append({
            "leader": "--- Scegli Eroe Leader ---",
            "is_generale": False if len(st.session_state["sdg_reggimenti"]) > 0 else True,
            "rinforzato": False,
            "tratto_eroico": "Nessuno",
            "artefatto": "Nessuno",
            "livello_mago": 0,
            "livello_prete": 0,
            "seguito": []
        })
        st.rerun()

    if col_btn_reg2.button("Svuota Intero Roster (Reset Armata)"):
        st.session_state["sdg_reggimenti"] = [{
            "leader": "--- Scegli Eroe Leader ---",
            "is_generale": True,
            "rinforzato": False,
            "tratto_eroico": "Nessuno",
            "artefatto": "Nessuno",
            "livello_mago": 0,
            "livello_prete": 0,
            "seguito": []
        }]
        st.session_state["sdg_ausiliari"] = []
        st.rerun()

    opzioni_tratti = [
        "Nessuno",
        "Maestro del Campo (+2 Controllo Obiettivi)",
        "Furia Implacabile (+1 Attacchi alle armi da mischia)",
        "Cacciatore di Eroi (+1 Rend contro Eroi/Mostri)",
        "Protettore Ancestrale (Aura Ward 6+ o difesa)",
        "Incanalatore Arcano (+1 al lancio incantesimi/preghiere)",
        "Tratto Personalizzato di Fazione"
    ]

    opzioni_artefatti = [
        "Nessuno",
        "Talismano di Guardia (Ward 5+ al portatore)",
        "Lama Squarciante (+1 Rend a un'arma da mischia)",
        "Pietra del Vuoto (1 volta per partita: Unbind automatico)",
        "Elmo del Comando (Riduce costo Comandi di 1 CP)",
        "Calice del Vigore (Cura D3 ferite a fine turno)",
        "Artefatto Personalizzato di Fazione"
    ]

    opzioni_ruolo_campo = [
        "Fanteria Standard (1 OC/mod)",
        "Cavalleria / Élite (2 OC/mod)",
        "Mostro (5 OC)",
        "Eroe (2 OC)",
        "Macchina da Guerra (3 OC)"
    ]

    reggimenti_da_rimuovere = []

    for r_idx, reg in enumerate(st.session_state["sdg_reggimenti"]):
        with st.container(border=True):
            head_c1, head_c2 = st.columns([4, 1])
            etichetta_gen = " — ★ REGGIMENTO DEL GENERALE" if reg.get("is_generale", False) else ""
            head_c1.markdown(f'<div class="subsection-title">Reggimento #{r_idx+1}{etichetta_gen}</div>', unsafe_allow_html=True)
            if head_c2.button("🗑️ Rimuovi Reggimento", key=f"del_reg_{r_idx}", use_container_width=True):
                reggimenti_da_rimuovere.append(r_idx)

            st.caption("Seleziona il Comandante (Eroe) del reggimento, configura le sue doti arcane/sacerdotali e aggiungi fino a 3 unità di seguito (4 per il Generale).")

            # Configurazione Leader del Reggimento
            lc1, lc2, lc3, lc4 = st.columns([2.2, 1, 1, 1])
            lista_scelta_leader = ["--- Scegli Eroe Leader ---"] + opzioni_db
            idx_lead = lista_scelta_leader.index(reg["leader"]) if reg["leader"] in lista_scelta_leader else 0
            reg["leader"] = lc1.selectbox("Eroe Leader del Reggimento", lista_scelta_leader, index=idx_lead, key=f"reg_lead_{r_idx}")
            
            is_gen_chk = lc2.checkbox("È il Generale", value=reg.get("is_generale", False), key=f"reg_gen_{r_idx}")
            if is_gen_chk and not reg.get("is_generale", False):
                for altro_idx, altro_reg in enumerate(st.session_state["sdg_reggimenti"]):
                    altro_reg["is_generale"] = (altro_idx == r_idx)
                st.rerun()
            else:
                reg["is_generale"] = is_gen_chk

            reg["livello_mago"] = lc3.selectbox("Livello Mago (Wizard)", [0, 1, 2, 3], index=int(reg.get("livello_mago", 0)), key=f"reg_wiz_{r_idx}")
            reg["livello_prete"] = lc4.selectbox("Livello Prete (Priest)", [0, 1, 2], index=int(reg.get("livello_prete", 0)), key=f"reg_pri_{r_idx}")

            # Tratto Eroico e Artefatto
            tc1, tc2 = st.columns(2)
            idx_tratto = opzioni_tratti.index(reg.get("tratto_eroico", "Nessuno")) if reg.get("tratto_eroico", "Nessuno") in opzioni_tratti else 0
            reg["tratto_eroico"] = tc1.selectbox("Tratto Eroico (Heroic Trait)", opzioni_tratti, index=idx_tratto, key=f"reg_trait_{r_idx}")

            idx_art = opzioni_artefatti.index(reg.get("artefatto", "Nessuno")) if reg.get("artefatto", "Nessuno") in opzioni_artefatti else 0
            reg["artefatto"] = tc2.selectbox("Artefatto di Potere (Artefact of Power)", opzioni_artefatti, index=idx_art, key=f"reg_art_{r_idx}")

            # Info rapida punti Leader
            if reg["leader"] in st.session_state["db_unita"]:
                d_lead = st.session_state["db_unita"][reg["leader"]]
                pt_lead = int(d_lead.get("punti", 0))
                sal_lead = int(d_lead.get("difesa", {}).get("salute_per_modello", 5)) * max(1, int(d_lead.get("n_modelli", 1)))
                sv_lead = d_lead.get("difesa", {}).get("save", 4)
                st.markdown(f"**Statistiche Leader:** Costo `{pt_lead} pt` | Salute Totale: `{sal_lead} PF` | Save: `{sv_lead}+`")

            st.markdown("---")
            max_seguito = 4 if reg.get("is_generale", False) else 3
            st.markdown(f"**Unità del Seguito ({len(reg['seguito'])} / {max_seguito} slot occupati):**")

            # Aggiunta Unità al Seguito
            sc_add1, sc_add2 = st.columns([3, 1])
            unita_seg_sel = sc_add1.selectbox(
                "Aggiungi unità al seguito di questo reggimento:",
                ["--- Scegli unità dal DB ---"] + opzioni_db,
                key=f"sel_add_seg_{r_idx}"
            )
            if sc_add2.button("➕ Aggiungi al Reggimento", key=f"btn_add_seg_{r_idx}", use_container_width=True):
                if unita_seg_sel != "--- Scegli unità dal DB ---":
                    if len(reg["seguito"]) < max_seguito:
                        reg["seguito"].append({
                            "nome": unita_seg_sel,
                            "rinforzata": False,
                            "ruolo": "Fanteria Standard (1 OC/mod)",
                            "mago_extra": 0,
                            "prete_extra": 0
                        })
                        st.rerun()
                    else:
                        st.warning(f"Questo reggimento ha già raggiunto il limite massimo di {max_seguito} unità di seguito.")

            # Elenco Unità nel Seguito
            seguito_da_rimuovere = []
            for f_idx, fol in enumerate(reg["seguito"]):
                nome_fol = fol["nome"]
                dati_fol_db = st.session_state["db_unita"].get(nome_fol, {})
                pt_base_fol = int(dati_fol_db.get("punti", 0))
                mod_base_fol = int(dati_fol_db.get("n_modelli", 1))

                fc1, fc2, fc3, fc4, fc5 = st.columns([2.2, 1, 1.5, 0.8, 0.7])
                molt_f = 2 if fol.get("rinforzata", False) else 1
                fc1.markdown(f"• **{nome_fol}** ({mod_base_fol * molt_f} mod. — `{pt_base_fol * molt_f} pt`)")
                fol["rinforzata"] = fc2.checkbox("Rinforzata (x2)", value=fol.get("rinforzata", False), key=f"fol_rinf_{r_idx}_{f_idx}")
                
                idx_ruolo = opzioni_ruolo_campo.index(fol.get("ruolo", "Fanteria Standard (1 OC/mod)")) if fol.get("ruolo") in opzioni_ruolo_campo else 0
                fol["ruolo"] = fc3.selectbox("Ruolo / OC", opzioni_ruolo_campo, index=idx_ruolo, key=f"fol_role_{r_idx}_{f_idx}", label_visibility="collapsed")
                
                fol["mago_extra"] = 1 if fc4.checkbox("Mago/Prete", value=(fol.get("mago_extra", 0) > 0), key=f"fol_mp_{r_idx}_{f_idx}") else 0
                if fc5.button("✖", key=f"del_fol_{r_idx}_{f_idx}"):
                    seguito_da_rimuovere.append(f_idx)

            if seguito_da_rimuovere:
                for idx_f_del in sorted(seguito_da_rimuovere, reverse=True):
                    reg["seguito"].pop(idx_f_del)
                st.rerun()

    if reggimenti_da_rimuovere:
        for idx_r_del in sorted(reggimenti_da_rimuovere, reverse=True):
            st.session_state["sdg_reggimenti"].pop(idx_r_del)
        st.rerun()

    # Sezione Unità Ausiliarie
    with st.container(border=True):
        st.markdown('<div class="subsection-title">Unità Ausiliarie (Auxiliary Units)</div>', unsafe_allow_html=True)
        st.caption("Schiera unità fuori dai Reggimenti. Attenzione: in AoS 4e chi ha più Unità Ausiliarie concede +1 Punto Comando extra per round all'avversario.")

        au_c1, au_c2 = st.columns([3, 1])
        aux_sel = au_c1.selectbox("Seleziona unità ausiliaria dal DB:", ["--- Scegli unità ---"] + opzioni_db, key="sel_add_aux")
        if au_c2.button("➕ Aggiungi Ausiliaria", use_container_width=True):
            if aux_sel != "--- Scegli unità ---":
                st.session_state["sdg_ausiliari"].append({
                    "nome": aux_sel,
                    "rinforzata": False,
                    "ruolo": "Fanteria Standard (1 OC/mod)"
                })
                st.rerun()

        aux_da_rimuovere = []
        for a_idx, aux in enumerate(st.session_state["sdg_ausiliari"]):
            d_aux = st.session_state["db_unita"].get(aux["nome"], {})
            molt_a = 2 if aux.get("rinforzata", False) else 1
            ac1, ac2, ac3, ac4 = st.columns([2.5, 1, 1.5, 0.7])
            ac1.markdown(f"• **[Ausiliaria] {aux['nome']}** ({int(d_aux.get('n_modelli', 1))*molt_a} mod. — `{int(d_aux.get('punti', 0))*molt_a} pt`)")
            aux["rinforzata"] = ac2.checkbox("Rinforzata (x2)", value=aux.get("rinforzata", False), key=f"aux_rinf_{a_idx}")
            idx_r_aux = opzioni_ruolo_campo.index(aux.get("ruolo", "Fanteria Standard (1 OC/mod)")) if aux.get("ruolo") in opzioni_ruolo_campo else 0
            aux["ruolo"] = ac3.selectbox("Ruolo", opzioni_ruolo_campo, index=idx_r_aux, key=f"aux_role_{a_idx}", label_visibility="collapsed")
            if ac4.button("✖", key=f"del_aux_{a_idx}"):
                aux_da_rimuovere.append(a_idx)

        if aux_da_rimuovere:
            for idx_a_del in sorted(aux_da_rimuovere, reverse=True):
                st.session_state["sdg_ausiliari"].pop(idx_a_del)
            st.rerun()

    # ==========================================
    # AGGREGAZIONE DATI DELL'INTERA ARMATA
    # ==========================================
    bersaglio_medio_riferimento = {
        "save": 4, "ward": 7, "salute": 20, "keywords": ["INFANTRY"],
        "cover": False, "aod": False, "bonus_save_extra": 0,
        "obscuring": False, "bersaglio_ha_caricato": False,
        "mod_ward_penalita": 0, "blocca_ward": False, "mod_wnd_nerf": 0
    }

    unita_totali_schierate = []
    punti_totali = 0
    ferite_totali_armata = 0
    modelli_totali_armata = 0
    oc_totale_armata = 0
    livello_magico_tot = 0
    livello_preti_tot = 0
    danno_melee_armata = 0.0
    danno_tiro_armata = 0.0
    max_rend_armata = 0
    n_unita_screen_economiche = 0
    ha_generale = False
    n_eroi = 0
    n_rinforzate = 0

    # Scansione Reggimenti
    for r_idx, reg in enumerate(st.session_state["sdg_reggimenti"]):
        if reg.get("is_generale", False) and reg["leader"] in st.session_state["db_unita"]:
            ha_generale = True

        livello_magico_tot += int(reg.get("livello_mago", 0))
        livello_preti_tot += int(reg.get("livello_prete", 0))

        # Leader
        if reg["leader"] in st.session_state["db_unita"]:
            n_eroi += 1
            d_u = st.session_state["db_unita"][reg["leader"]]
            pt_u = int(d_u.get("punti", 0))
            n_mod_u = max(1, int(d_u.get("n_modelli", 1)))
            sal_mod_u = max(1, int(d_u.get("difesa", {}).get("salute_per_modello", 5)))
            hp_u = n_mod_u * sal_mod_u
            oc_u = stima_controllo_unita("Eroe (2 OC)", n_mod_u)
            if "Maestro del Campo" in reg.get("tratto_eroico", ""):
                oc_u += 2

            perf = calcola_output_unita_su_bersaglio(d_u, False, bersaglio_medio_riferimento)
            punti_totali += pt_u
            ferite_totali_armata += hp_u
            modelli_totali_armata += n_mod_u
            oc_totale_armata += oc_u
            danno_melee_armata += perf["danno_melee"]
            danno_tiro_armata += perf["danno_ranged"]
            if perf["max_rend"] > max_rend_armata:
                max_rend_armata = perf["max_rend"]

            unita_totali_schierate.append({
                "etichetta": f"[Reg.{r_idx+1} Leader] {reg['leader']}",
                "chiave_db": reg["leader"],
                "rinforzata": False,
                "punti": pt_u,
                "salute": hp_u,
                "oc": oc_u,
                "danno_medio": perf["danno_totale"]
            })

        # Seguito
        for fol in reg["seguito"]:
            if fol["nome"] in st.session_state["db_unita"]:
                d_f = st.session_state["db_unita"][fol["nome"]]
                rinf = bool(fol.get("rinforzata", False))
                if rinf:
                    n_rinforzate += 1
                molt = 2 if rinf else 1
                pt_f = int(d_f.get("punti", 0)) * molt
                n_mod_f = max(1, int(d_f.get("n_modelli", 1))) * molt
                sal_mod_f = max(1, int(d_f.get("difesa", {}).get("salute_per_modello", 1)))
                hp_f = n_mod_f * sal_mod_f
                oc_f = stima_controllo_unita(fol.get("ruolo", "Fanteria Standard (1 OC/mod)"), n_mod_f)
                livello_magico_tot += int(fol.get("mago_extra", 0))

                if pt_f <= 130 and n_mod_f >= 5:
                    n_unita_screen_economiche += 1

                perf_f = calcola_output_unita_su_bersaglio(d_f, rinf, bersaglio_medio_riferimento)
                punti_totali += pt_f
                ferite_totali_armata += hp_f
                modelli_totali_armata += n_mod_f
                oc_totale_armata += oc_f
                danno_melee_armata += perf_f["danno_melee"]
                danno_tiro_armata += perf_f["danno_ranged"]
                if perf_f["max_rend"] > max_rend_armata:
                    max_rend_armata = perf_f["max_rend"]

                unita_totali_schierate.append({
                    "etichetta": f"[Reg.{r_idx+1}] {fol['nome']}" + (" (x2)" if rinf else ""),
                    "chiave_db": fol["nome"],
                    "rinforzata": rinf,
                    "punti": pt_f,
                    "salute": hp_f,
                    "oc": oc_f,
                    "danno_medio": perf_f["danno_totale"]
                })

    # Scansione Ausiliari
    for aux in st.session_state["sdg_ausiliari"]:
        if aux["nome"] in st.session_state["db_unita"]:
            d_a = st.session_state["db_unita"][aux["nome"]]
            rinf_a = bool(aux.get("rinforzata", False))
            if rinf_a:
                n_rinforzate += 1
            molt_a = 2 if rinf_a else 1
            pt_a = int(d_a.get("punti", 0)) * molt_a
            n_mod_a = max(1, int(d_a.get("n_modelli", 1))) * molt_a
            sal_mod_a = max(1, int(d_a.get("difesa", {}).get("salute_per_modello", 1)))
            hp_a = n_mod_a * sal_mod_a
            oc_a = stima_controllo_unita(aux.get("ruolo", "Fanteria Standard (1 OC/mod)"), n_mod_a)

            if pt_a <= 130 and n_mod_a >= 5:
                n_unita_screen_economiche += 1

            perf_a = calcola_output_unita_su_bersaglio(d_a, rinf_a, bersaglio_medio_riferimento)
            punti_totali += pt_a
            ferite_totali_armata += hp_a
            modelli_totali_armata += n_mod_a
            oc_totale_armata += oc_a
            danno_melee_armata += perf_a["danno_melee"]
            danno_tiro_armata += perf_a["danno_ranged"]
            if perf_a["max_rend"] > max_rend_armata:
                max_rend_armata = perf_a["max_rend"]

            unita_totali_schierate.append({
                "etichetta": f"[Ausiliaria] {aux['nome']}" + (" (x2)" if rinf_a else ""),
                "chiave_db": aux["nome"],
                "rinforzata": rinf_a,
                "punti": pt_a,
                "salute": hp_a,
                "oc": oc_a,
                "danno_medio": perf_a["danno_totale"]
            })

    # ==========================================
    # SEZIONE 3: CONVALIDA PUNTI, RUOLI & CHECK-UP STRATEGICO
    # ==========================================
    st.markdown('<div class="section-header">Cruscotto Tattico e Diagnosi dell\'Esercito</div>', unsafe_allow_html=True)
    st.caption("Verifica la legalità del roster secondo i requisiti di AoS 4e ed esamina il bilanciamento dei ruoli sul campo.")

    # Barra di avanzamento punti e Convalida 4e
    with st.container(border=True):
        st.markdown('<div class="subsection-title">Saturazione Punti e Legalità della Lista</div>', unsafe_allow_html=True)
        perc_punti = min(1.0, punti_totali / float(limite_punti)) if limite_punti > 0 else 0.0
        st.progress(perc_punti, text=f"Punti Impegnati: {punti_totali} / {limite_punti} pt ({ (punti_totali/float(limite_punti))*100:.1f}%) — Punti Rimanenti: {limite_punti - punti_totali} pt")

        v1, v2, v3, v4 = st.columns(4)
        if punti_totali <= limite_punti and punti_totali > 0:
            v1.success(f"Punti in Regola ({punti_totali}/{limite_punti})")
        elif punti_totali > limite_punti:
            v1.error(f"Sforamento di +{punti_totali - limite_punti} pt!")
        else:
            v1.warning("Nessuna unità schierata")

        if ha_generale:
            v2.success("Generale Designato: Sì")
        else:
            v2.error("Manca un Eroe Generale!")

        n_reg_attivi = len(st.session_state["sdg_reggimenti"])
        if n_reg_attivi <= max_reggimenti:
            v3.success(f"Reggimenti: {n_reg_attivi} / {max_reggimenti} (Drops)")
        else:
            v3.error(f"Troppi Reggimenti ({n_reg_attivi}/{max_reggimenti})")

        n_aux_attivi = len(st.session_state["sdg_ausiliari"])
        if n_aux_attivi == 0:
            v4.success("Zero Ausiliari (Nessun malus CP)")
        else:
            v4.warning(f"{n_aux_attivi} Ausiliari (Rischio +1 CP al nemico)")

    # Metriche Globali dell'Esercito
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pool Ferite Armata", f"{ferite_totali_armata} PF", f"{modelli_totali_armata} Modelli totali")
    m2.metric("Danno Medio (vs Save 4+)", f"{(danno_melee_armata + danno_tiro_armata):.1f} Danni", f"Mischia: {danno_melee_armata:.1f} | Tiro: {danno_tiro_armata:.1f}")
    m3.metric("Dominio Arcano & Fede", f"{livello_magico_tot} Cast / {livello_preti_tot} Chant", f"{livello_magico_tot} Unbind disponibili")
    m4.metric("Presidio Obiettivi (OC)", f"{oc_totale_armata} Punti Controllo", f"{len(unita_totali_schierate)} Unità sul campo")

    tab_diag, tab_matchup, tab_export = st.tabs([
        "Check-Up Strategico & Carenze",
        "Matrice Match-Up vs Armata Nemica",
        "Salvataggio & Pergamena Torneo"
    ])

    # ==========================================
    # TAB 1: DIAGNOSI E COMPASS DEI 5 ASSI TATTICI
    # ==========================================
    with tab_diag:
        col_d1, col_d2 = st.columns([1.2, 1])

        with col_d1:
            st.markdown('<div class="subsection-title">Avvertimenti dello Stratega (Analisi Carenze)</div>', unsafe_allow_html=True)
            st.caption("Diagnosi automatica dei punti di forza e delle vulnerabilità strutturali della lista attuale.")

            with st.container(border=True):
                if len(unita_totali_schierate) == 0:
                    st.info("Aggiungi almeno un Eroe Leader e delle unità nei Reggimenti per generare la diagnosi strategica dell'esercito.")
                else:
                    avvisi = []
                    punti_forza = []

                    # 1. Controllo Dispersione Magica
                    if livello_magico_tot == 0:
                        avvisi.append("**Vulnerabilità Magica Totale (0 Wizard):** Non possiedi alcun Mago in lista. Non potrai tentare *Unbind* contro gli incantesimi avversari né bandire (*Banish*) le Manifestazioni nemiche nei turni normali, salvo l'uso di un artefatto specifico.")
                    elif livello_magico_tot >= 2:
                        punti_forza.append(f"**Superiorità Arcana ({livello_magico_tot} livelli magici):** Ottima capacità di lancio incantesimi, evocazione di Manifestazioni e controllo magico del campo.")

                    # 2. Controllo Penetrazione Armatura (Rend)
                    if max_rend_armata < 2:
                        avvisi.append(f"**Carenza Anticarro / Basso Rend (Max Rend {max_rend_armata}):** La tua armata manca di penetrazione pesante (Rend 2 o superiore). Rischi di rimbalzare contro liste corazzate con Save 2+ o 3+ che utilizzano *All-out Defence*.")
                    else:
                        punti_forza.append(f"**Capacità Perfora-Corazze (Max Rend {max_rend_armata}):** Presenza di profili capaci di bucare i tiri salvezza delle unità d'élite e dei Mostri avversari.")

                    # 3. Pressione a Distanza
                    if danno_tiro_armata < 3.0:
                        avvisi.append("**Assenza di Pressione a Distanza:** Il tuo output di tiro è quasi nullo. Dovrai avanzare interamente in corpo a corpo per infliggere danni, prestando massima attenzione agli schermi (*screens*) avversari.")
                    elif danno_tiro_armata >= 12.0:
                        punti_forza.append(f"**Potenza di Fuoco Rilevante ({danno_tiro_armata:.1f} danni medi al tiro):** Puoi indebolire o eliminare i supporti nemici prima ancora della fase di carica.")

                    # 4. Cordoni e Schermi (Screens)
                    if n_unita_screen_economiche == 0:
                        avvisi.append("**Mancanza di Cordoni Protettivi (Screens):** Non hai unità economiche (≤ 130 pt) sacrificabili per schermare le tue punte di diamante. Se l'avversario prende il primo turno con un esercito da carica rapida, le tue unità chiave subiranno l'impatto diretto.")
                    else:
                        punti_forza.append(f"**Buona Schermatura Tattica ({n_unita_screen_economiche} unità leggere):** Hai pedine sacrificabili per bloccare le linee di carica avversarie e dettare i tempi di ingaggio.")

                    # 5. Solidità e Pool Ferite rispetto ai punti
                    rapporto_hp_punti = (ferite_totali_armata / float(limite_punti)) * 100.0 if limite_punti > 0 else 0
                    if rapporto_hp_punti < 4.5:
                        avvisi.append(f"**Bassa Densità di Ferite ({ferite_totali_armata} PF totali):** L'armata è molto d'élite ma ha poche ferite complessive. Ogni perdita peserà enormemente sul controllo degli obiettivi.")
                    elif rapporto_hp_punti >= 7.0:
                        punti_forza.append(f"**Elevata Resilienza di Massa ({ferite_totali_armata} PF totali):** Enorme bacino di ferite che richiederà diversi turni al nemico per essere eroso.")

                    if punti_forza:
                        st.markdown("**Punti di Forza Rilevati:**")
                        for pf in punti_forza:
                            st.markdown(f"- ✅ {pf}")
                    if avvisi:
                        st.markdown("---")
                        st.markdown("**Rischi e Carenze Strutturali:**")
                        for av in avvisi:
                            st.markdown(f"- ⚠️ {av}")

        with col_d2:
            st.markdown('<div class="subsection-title">Profilo delle 5 Competenze (Scala 0-100)</div>', unsafe_allow_html=True)
            st.caption("Valutazione parametrica del tuo schieramento rispetto agli standard del formato selezionato.")

            fattore_scala = max(0.5, limite_punti / 2000.0)
            score_melee = min(100.0, (danno_melee_armata / (45.0 * fattore_scala)) * 100.0)
            score_tiro = min(100.0, (danno_tiro_armata / (25.0 * fattore_scala)) * 100.0)
            score_resilienza = min(100.0, (ferite_totali_armata / (130.0 * fattore_scala)) * 100.0)
            score_magia = min(100.0, ((livello_magico_tot + livello_preti_tot) / (4.0 * fattore_scala)) * 100.0)
            score_controllo = min(100.0, (oc_totale_armata / (75.0 * fattore_scala)) * 100.0)

            df_competenze = pd.DataFrame({
                "Competenza": [
                    "1. Impatto Mischia",
                    "2. Fuoco a Distanza",
                    "3. Resilienza (Wound Pool)",
                    "4. Dominio Magia/Preghiere",
                    "5. Controllo Mappa (OC)"
                ],
                "Indice (0-100)": [
                    round(score_melee, 1),
                    round(score_tiro, 1),
                    round(score_resilienza, 1),
                    round(score_magia, 1),
                    round(score_controllo, 1)
                ]
            })
            st.bar_chart(df_competenze.set_index("Competenza"), x_label="Asse Strategico", y_label="Indice di Efficienza (0-100)", color="#b38b4d")

    # ==========================================
    # TAB 2: MATRICE MATCH-UP VS ARMATA NEMICA
    # ==========================================
    with tab_matchup:
        st.markdown('<div class="subsection-title">Simulatore d\'Incrocio: La Tua Armata vs Lista Avversaria</div>', unsafe_allow_html=True)
        st.caption("Seleziona le unità che compongono l'esercito avversario per calcolare la matrice 'Chi deve attaccare Chi' (% di Salute nemica rimossa in 1 turno di combattimento).")

        with st.container(border=True):
            mc1, mc2, mc3 = st.columns([2.5, 1, 1])
            nemico_sel = mc1.selectbox("Aggiungi un'unità alla Lista Avversaria da affrontare:", ["--- Scegli unità nemica dal DB ---"] + opzioni_db, key="sel_enemy_mu")
            nemico_rinf = mc2.checkbox("Nemico Rinforzato (x2)", value=False, key="chk_enemy_rinf")
            if mc3.button("➕ Schiera Nemico", type="primary", use_container_width=True):
                if nemico_sel != "--- Scegli unità nemica dal DB ---":
                    st.session_state["sdg_nemici_matchup"].append({
                        "nome": nemico_sel,
                        "rinforzata": nemico_rinf
                    })
                    st.rerun()

            if st.session_state["sdg_nemici_matchup"]:
                nem_str_list = []
                for n_i, nem_obj in enumerate(st.session_state["sdg_nemici_matchup"]):
                    nem_str_list.append(f"{n_i+1}. {nem_obj['nome']}" + (" (x2)" if nem_obj["rinforzata"] else ""))
                st.markdown("**Forze Avversarie in Campo:** " + " | ".join(nem_str_list))
                if st.button("🗑️ Svuota Lista Nemica"):
                    st.session_state["sdg_nemici_matchup"] = []
                    st.rerun()

        if len(unita_totali_schierate) > 0 and len(st.session_state["sdg_nemici_matchup"]) > 0:
            matrice_matchup = {}
            raccomandazioni_tattiche = []

            for nem_idx, nem_item in enumerate(st.session_state["sdg_nemici_matchup"]):
                d_nem = st.session_state["db_unita"].get(nem_item["nome"], {})
                dif_nem = d_nem.get("difesa", {})
                molt_n = 2 if nem_item.get("rinforzata", False) else 1
                
                sv_n_raw = dif_nem.get("save", 4)
                sv_n = int(sv_n_raw) if str(sv_n_raw).isdigit() else 7
                wd_n_raw = dif_nem.get("ward", 7)
                wd_n = int(wd_n_raw) if str(wd_n_raw).isdigit() else 7
                hp_n = max(1, int(d_nem.get("n_modelli", 1)) * molt_n * max(1, int(dif_nem.get("salute_per_modello", 1))))
                pt_n = int(d_nem.get("punti", 0)) * molt_n

                col_label = f"{nem_item['nome']}" + (" (x2)" if nem_item["rinforzata"] else "") + f" [{hp_n} PF | {pt_n}pt]"
                col_percentuali = []

                miglior_attaccante_nome = ""
                miglior_ratio_scambio = -1.0

                bersaglio_nem_struct = {
                    "save": sv_n, "ward": wd_n, "salute": hp_n, "keywords": ["INFANTRY", "HERO"],
                    "cover": False, "aod": False, "bonus_save_extra": 0,
                    "obscuring": False, "bersaglio_ha_caricato": False,
                    "mod_ward_penalita": 0, "blocca_ward": False, "mod_wnd_nerf": 0
                }

                for mia_u in unita_totali_schierate:
                    d_mia = st.session_state["db_unita"].get(mia_u["chiave_db"], {})
                    ris_scontro = calcola_output_unita_su_bersaglio(d_mia, mia_u["rinforzata"], bersaglio_nem_struct)
                    perc_kill_1t = min(100.0, (ris_scontro["danno_totale"] / float(hp_n)) * 100.0)
                    col_percentuali.append(round(perc_kill_1t, 1))

                    # Valuta efficienza: % di vita tolta ponderata per costo punti
                    efficienza_ingaggio = (perc_kill_1t * pt_n) / max(50.0, float(mia_u["punti"]))
                    if efficienza_ingaggio > miglior_ratio_scambio and perc_kill_1t >= 35.0:
                        miglior_ratio_scambio = efficienza_ingaggio
                        miglior_attaccante_nome = f"**{mia_u['etichetta']}** (infligge ~{ris_scontro['danno_totale']:.1f} danni, pari al **{perc_kill_1t:.0f}%** della vita nemica in 1 turno)"

                matrice_matchup[col_label] = col_percentuali
                if miglior_attaccante_nome:
                    raccomandazioni_tattiche.append(f"🎯 Contro **{col_label}**: Incarico prioritario consigliato a {miglior_attaccante_nome}.")
                else:
                    raccomandazioni_tattiche.append(f"⚠️ Contro **{col_label}**: Nessuna tua singola unità supera il 35% di danno in 1 turno. Necessario **Attacco Combinato** di più unità!")

            df_mu = pd.DataFrame(matrice_matchup, index=[u["etichetta"] for u in unita_totali_schierate])
            st.markdown("#### Matrice Percentuale di Eliminazione in 1 Turno (% Salute Rimossa)")
            st.dataframe(df_mu.style.background_gradient(cmap="YlOrBr", vmin=0, vmax=100).format("{:.1f}%"), use_container_width=True)

            with st.container(border=True):
                st.markdown("#### Piano di Battaglia Consigliato (Assegnazione Bersagli)")
                for racc in raccomandazioni_tattiche:
                    st.markdown(f"- {racc}")
        else:
            st.info("Per visualizzare la Matrice di Match-Up, assicurati di aver inserito unità nella tua armata e almeno 1 unità nella Lista Avversaria qui sopra.")

    # ==========================================
    # TAB 3: SALVATAGGIO E PERGAMENA DI ESPORTAZIONE
    # ==========================================
    with tab_export:
        st.markdown('<div class="subsection-title">Salvataggio nell\'Archivio & Pergamena Torneo</div>', unsafe_allow_html=True)
        st.caption("Salva l'intera configurazione dell'armata per richiamarla in futuro o copia il riepilogo formattato per i tuoi tornei.")

        with st.container(border=True):
            if st.button("💾 Salva Armata nell'Archivio Locale", type="primary"):
                chiave_armata = f"{st.session_state['sdg_fazione_armata']}: {st.session_state['sdg_nome_armata']}"
                st.session_state["archivio_armate"][chiave_armata] = {
                    "nome": st.session_state["sdg_nome_armata"],
                    "fazione": st.session_state["sdg_fazione_armata"],
                    "formazione": st.session_state["sdg_formazione_battaglia"],
                    "limite_punti": limite_punti,
                    "punti_totali": punti_totali,
                    "reggimenti": st.session_state["sdg_reggimenti"],
                    "ausiliari": st.session_state["sdg_ausiliari"]
                }
                salva_archivio_armate(st.session_state["archivio_armate"])
                st.toast(f"Armata '{chiave_armata}' salvata con successo nell'archivio!")
                st.rerun()

            # Generazione Testo Formato Torneo
            linee_export = [
                f"=== {st.session_state['sdg_nome_armata'].upper()} ===",
                f"Fazione: {st.session_state['sdg_fazione_armata']} | Formazione: {st.session_state['sdg_formazione_battaglia']}",
                f"Punti Totali: {punti_totali} / {limite_punti} pt | Reggimenti (Drops): {len(st.session_state['sdg_reggimenti'])} | Ausiliari: {len(st.session_state['sdg_ausiliari'])}",
                f"Ferite Totali: {ferite_totali_armata} PF | Controllo Totale: {oc_totale_armata} OC | Cast/Chant: {livello_magico_tot}/{livello_preti_tot}",
                "-" * 55
            ]

            for r_i, reg in enumerate(st.session_state["sdg_reggimenti"]):
                gen_tag = " [GENERALE]" if reg.get("is_generale", False) else ""
                d_l = st.session_state["db_unita"].get(reg["leader"], {})
                pt_l = int(d_l.get("punti", 0))
                linee_export.append(f"\nREGGIMENTO {r_i+1}:")
                linee_export.append(f"  • Leader: {reg['leader']}{gen_tag} ({pt_l} pt)")
                if reg.get("tratto_eroico", "Nessuno") != "Nessuno":
                    linee_export.append(f"    - Tratto Eroico: {reg['tratto_eroico']}")
                if reg.get("artefatto", "Nessuno") != "Nessuno":
                    linee_export.append(f"    - Artefatto: {reg['artefatto']}")
                for fol in reg["seguito"]:
                    d_f = st.session_state["db_unita"].get(fol["nome"], {})
                    molt = 2 if fol.get("rinforzata", False) else 1
                    rinf_str = " [Rinforzata]" if fol.get("rinforzata", False) else ""
                    linee_export.append(f"  • Unità: {fol['nome']}{rinf_str} ({int(d_f.get('punti', 0))*molt} pt) - {fol.get('ruolo', '')}")

            if st.session_state["sdg_ausiliari"]:
                linee_export.append("\nUNITÀ AUSILIARIE:")
                for aux in st.session_state["sdg_ausiliari"]:
                    d_a = st.session_state["db_unita"].get(aux["nome"], {})
                    molt_a = 2 if aux.get("rinforzata", False) else 1
                    rinf_a_str = " [Rinforzata]" if aux.get("rinforzata", False) else ""
                    linee_export.append(f"  • {aux['nome']}{rinf_a_str} ({int(d_a.get('punti', 0))*molt_a} pt)")

            testo_completo_export = "\n".join(linee_export)
            st.text_area("Pergamena dell'Esercito (Pronta da copiare):", value=testo_completo_export, height=320)