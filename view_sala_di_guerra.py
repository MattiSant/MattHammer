import streamlit as st
import numpy as np
import pandas as pd
import json
import os
from core_engine import calcola_arma_analitico

ARMIES_DB_FILE = "armies_db.json"
FORMATIONS_DB_FILE = "formations.json"

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

def carica_formazioni_db():
    if os.path.exists(FORMATIONS_DB_FILE):
        try:
            with open(FORMATIONS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

# Preset di Armate Avversarie Note (basate sulle campagne del notebook)
ARMATE_NEMICHE_NOTE = {
    "Khorne: Eroi d'Assalto (720pt)": [
        {"nome": "Blades of Khorne: Bloodsecrator", "rinforzata": False},
        {"nome": "Blades of Khorne: Aspiring Deathbringer", "rinforzata": False},
        {"nome": "Blades of Khorne: Mighty Lord of Khorne", "rinforzata": False}
    ],
    "Orruk Kruleboyz: Orda & Speartrip (720pt)": [
        {"nome": "Orruk Kruleboyz: Gutrippaz", "rinforzata": True},
        {"nome": "Orruk Kruleboyz: Hobgrot Slittaboss", "rinforzata": False},
        {"nome": "Orruk Kruleboyz: Swampcalla Shaman", "rinforzata": False}
    ],
    "Sylvaneth: Bosco & Kurnoth (720pt)": [
        {"nome": "Sylvaneth: Branchwych", "rinforzata": False},
        {"nome": "Sylvaneth: Dryads", "rinforzata": True},
        {"nome": "Sylvaneth: Kurnoth Hunters with Greatscythes", "rinforzata": False}
    ]
}

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
    st.caption("Costruttore d'armata avanzato per Reggimenti, gestione formazioni tattiche e simulatore di Match-Up.")

    # Inizializzazione Stati Formazione e Armata
    if "archivio_formazioni" not in st.session_state:
        st.session_state["archivio_formazioni"] = carica_formazioni_db()

    if "sdg_nome_armata" not in st.session_state:
        st.session_state["sdg_nome_armata"] = "Armata Path to Glory"
    if "sdg_fazione_armata" not in st.session_state:
        st.session_state["sdg_fazione_armata"] = "Nighthaunt"
    if "sdg_formazione_scelta" not in st.session_state:
        st.session_state["sdg_formazione_scelta"] = "Death Stalkers"

    # ==========================================
    # SEZIONE 1: GENERALITÀ DELL'ARMATA E FORMAZIONE
    # ==========================================
    st.markdown('<div class="section-header">Configurazione Schieramento e Formazione</div>', unsafe_allow_html=True)
    st.caption("Definisci le generalità dell'esercito, il formato della battaglia e la Formazione tattica associata con i relativi bonus.")

    with st.container(border=True):
        st.markdown('<div class="subsection-title">Generalità dell\'Esercito</div>', unsafe_allow_html=True)
        
        # Schema richiesto sulla stessa riga: Nome della Lista - Fazione - Formato Battaglia
        col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.2, 1.3, 1])
        st.session_state["sdg_nome_armata"] = col_f1.text_input("Nome della Lista", value=st.session_state["sdg_nome_armata"])
        
        lista_fazioni_disp = ["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Grande Alleanza / Altro"]
        idx_faz = lista_fazioni_disp.index(st.session_state["sdg_fazione_armata"]) if st.session_state["sdg_fazione_armata"] in lista_fazioni_disp else 0
        st.session_state["sdg_fazione_armata"] = col_f2.selectbox("Fazione", lista_fazioni_disp, index=idx_faz)

        formato_scelto = col_f3.selectbox(
            "Formato Battaglia",
            ["Path to Glory (720 pt)", "Vanguard (1000 pt)", "Strike Force (1500 pt)", "Battlehost (2000 pt)", "Personalizzato (Custom)"],
            index=0
        )

        if "720" in formato_scelto:
            limite_punti = 720
        elif "1000" in formato_scelto:
            limite_punti = 1000
        elif "1500" in formato_scelto:
            limite_punti = 1500
        elif "2000" in formato_scelto:
            limite_punti = 2000
        else:
            limite_punti = col_f4.number_input("Punti", min_value=100, max_value=5000, value=720, step=10)

        st.markdown("---")
        st.markdown('<div class="subsection-title">Formazione di Battaglia (Battle Formation)</div>', unsafe_allow_html=True)
        st.caption("Seleziona la formazione specifica della tua fazione per applicare gli effetti tattici e scegliere la fase di gioco.")

        # Carica le formazioni dal DB in base alla fazione scelta
        fazioni_disponibili_db = st.session_state["archivio_formazioni"]
        formazioni_fazione = fazioni_disponibili_db.get(st.session_state["sdg_fazione_armata"], {
            "Formazione Standard": {
                "effetto_tipo": "Nessuno", "valore_bonus": 0, "fase_attivazione": "Nessuna", "descrizione": "Nessuna abilità speciale attiva."
            }
        })

        # CORRETTO: lista pulita dei nomi delle formazioni
        lista_nomi_formazioni = list(formazioni_fazione.keys()) if isinstance(formazioni_fazione, dict) else ["Formazione Standard"]
        idx_form = lista_nomi_formazioni.index(st.session_state["sdg_formazione_scelta"]) if st.session_state["sdg_formazione_scelta"] in lista_nomi_formazioni else 0
        
        formazione_selezionata = st.selectbox("Nome Formazione", lista_nomi_formazioni, index=idx_form)
        st.session_state["sdg_formazione_scelta"] = formazione_selezionata

        # Dati della formazione selezionata
        dati_form = formazioni_fazione.get(formazione_selezionata, {
            "effetto_tipo": "Nessuno", "valore_bonus": 0, "fase_attivazione": "Hero Phase", "descrizione": "Descrizione non disponibile."
        })

        # Layout Effetti, Menu a tendina Fasi di Gioco e Descrizione
        fc1, fc2 = st.columns([1.5, 2])
        
        with fc1:
            st.markdown(f"**Effetto Principale:** `{dati_form.get('effetto_tipo', 'Nessuno')}`")
            
            fasi_gioco_aos = [
                "Deployment (Schieramento)",
                "Inizio Round di Battaglia",
                "Hero Phase (Fase Eroi Amica)",
                "Hero Phase (Fase Eroi Nemica)",
                "Movement Phase (Movimento Amico)",
                "Movement Phase (Movimento Nemico)",
                "Shooting Phase (Fase di Tiro)",
                "Charge Phase (Fase di Carica)",
                "Combat Phase (Fase di Combattimento)",
                "Fine Turno",
                "Fine Round di Battaglia"
            ]
            
            fase_salvata_db = dati_form.get("fase_attivazione", "Hero Phase (Fase Eroi Amica)")
            idx_fase = fasi_gioco_aos.index(fase_salvata_db) if fase_salvata_db in fasi_gioco_aos else 2
            
            st.selectbox("Fase di Utilizzo Consigliata", fasi_gioco_aos, index=idx_fase, key=f"fase_form_{formazione_selezionata}")

        with fc2:
            st.markdown("**Descrizione Completa & Regola:**")
            st.info(dati_form.get('descrizione', 'Nessun dettaglio inserito.'))

        
    # ==========================================
    # SEZIONE 2: COMPOSIZIONE REGGIMENTI
    # ==========================================
    st.markdown('<div class="section-header">Composizione Reggimenti</div>', unsafe_allow_html=True)
    st.caption("Assegna leader, tratti eroici, artefatti magici e unità di seguito per ciascun reggimento dell'armata.")

    col_btn_reg1, col_btn_reg2 = st.columns([1, 3])
    if col_btn_reg1.button("➕ Aggiungi Reggimento", type="primary", use_container_width=True):
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

    if col_btn_reg2.button("Svuota Roster"):
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

    opzioni_tratti = ["Nessuno", "Furia Implacabile (+1 Attacchi)", "Maestro del Campo (+2 OC)", "Cacciatore di Eroi (+1 Rend)", "Tratto Personalizzato"]
    opzioni_artefatti = ["Nessuno", "Talismano di Guardia (Ward 5+)", "Lama Squarciante (+1 Rend)", "Pietra del Vuoto (Unbind extra)", "Artefatto Personalizzato"]
    opzioni_ruolo_campo = ["Fanteria Standard (1 OC/mod)", "Cavalleria / Élite (2 OC/mod)", "Mostro (5 OC)", "Eroe (2 OC)", "Macchina da Guerra (3 OC)"]

    reggimenti_da_rimuovere = []

    for r_idx, reg in enumerate(st.session_state["sdg_reggimenti"]):
        with st.container(border=True):
            head_c1, head_c2 = st.columns([4, 1])
            etichetta_gen = " — ★ GENERALE D'ARMATA" if reg.get("is_generale", False) else ""
            head_c1.markdown(f'<div class="subsection-title">Reggimento #{r_idx+1}{etichetta_gen}</div>', unsafe_allow_html=True)
            if head_c2.button("🗑️ Rimuovi", key=f"del_reg_{r_idx}", use_container_width=True):
                reggimenti_da_rimuovere.append(r_idx)

            lc1, lc2, lc3, lc4 = st.columns([2.2, 1, 1, 1])
            lista_scelta_leader = ["--- Scegli Eroe Leader ---"] + opzioni_db
            idx_lead = lista_scelta_leader.index(reg["leader"]) if reg["leader"] in lista_scelta_leader else 0
            reg["leader"] = lc1.selectbox("Leader", lista_scelta_leader, index=idx_lead, key=f"reg_lead_{r_idx}")
            
            is_gen_chk = lc2.checkbox("Generale", value=reg.get("is_generale", False), key=f"reg_gen_{r_idx}")
            if is_gen_chk and not reg.get("is_generale", False):
                for altro_idx, altro_reg in enumerate(st.session_state["sdg_reggimenti"]):
                    altro_reg["is_generale"] = (altro_idx == r_idx)
                st.rerun()
            else:
                reg["is_generale"] = is_gen_chk

            reg["livello_mago"] = lc3.selectbox("Wizard (Lv)", [0, 1, 2], index=int(reg.get("livello_mago", 0)), key=f"reg_wiz_{r_idx}")
            reg["livello_prete"] = lc4.selectbox("Priest (Lv)", [0, 1, 2], index=int(reg.get("livello_prete", 0)), key=f"reg_pri_{r_idx}")

            tc1, tc2 = st.columns(2)
            idx_tratto = opzioni_tratti.index(reg.get("tratto_eroico", "Nessuno")) if reg.get("tratto_eroico", "Nessuno") in opzioni_tratti else 0
            reg["tratto_eroico"] = tc1.selectbox("Tratto Eroico", opzioni_tratti, index=idx_tratto, key=f"reg_trait_{r_idx}")

            idx_art = opzioni_artefatti.index(reg.get("artefatto", "Nessuno")) if reg.get("artefatto", "Nessuno") in opzioni_artefatti else 0
            reg["artefatto"] = tc2.selectbox("Artefatto di Potere", opzioni_artefatti, index=idx_art, key=f"reg_art_{r_idx}")

            if reg["leader"] in st.session_state["db_unita"]:
                d_lead = st.session_state["db_unita"][reg["leader"]]
                pt_lead = int(d_lead.get("punti", 0))
                sal_lead = int(d_lead.get("difesa", {}).get("salute_per_modello", 5)) * max(1, int(d_lead.get("n_modelli", 1)))
                st.markdown(f"**Costo Leader:** `{pt_lead} pt` | **Salute:** `{sal_lead} PF`")

            st.markdown("---")
            max_seguito = 4 if reg.get("is_generale", False) else 3
            st.markdown(f"**Seguito ({len(reg['seguito'])} / {max_seguito} slot):**")

            sc_add1, sc_add2 = st.columns([3, 1])
            unita_seg_sel = sc_add1.selectbox("Aggiungi unità di seguito:", ["--- Scegli unità ---"] + opzioni_db, key=f"sel_add_seg_{r_idx}")
            if sc_add2.button("➕ Aggiungi", key=f"btn_add_seg_{r_idx}", use_container_width=True):
                if unita_seg_sel != "--- Scegli unità ---":
                    if len(reg["seguito"]) < max_seguito:
                        reg["seguito"].append({
                            "nome": unita_seg_sel,
                            "rinforzata": False,
                            "ruolo": "Fanteria Standard (1 OC/mod)"
                        })
                        st.rerun()
                    else:
                        st.warning("Limite slot seguito raggiunto per questo reggimento.")

            seguito_da_rimuovere = []
            for f_idx, fol in enumerate(reg["seguito"]):
                d_fol_db = st.session_state["db_unita"].get(fol["nome"], {})
                molt = 2 if fol.get("rinforzata", False) else 1
                fc1, fc2, fc3, fc4 = st.columns([2.5, 1, 1.5, 0.6])
                fc1.markdown(f"• **{fol['nome']}** ({int(d_fol_db.get('n_modelli', 1))*molt} mod. — `{int(d_fol_db.get('punti', 0))*molt} pt`)")
                fol["rinforzata"] = fc2.checkbox("Rinforzata", value=fol.get("rinforzata", False), key=f"fol_rinf_{r_idx}_{f_idx}")
                idx_ruolo = opzioni_ruolo_campo.index(fol.get("ruolo", "Fanteria Standard (1 OC/mod)")) if fol.get("ruolo") in opzioni_ruolo_campo else 0
                fol["ruolo"] = fc3.selectbox("Ruolo", opzioni_ruolo_campo, index=idx_ruolo, key=f"fol_role_{r_idx}_{f_idx}", label_visibility="collapsed")
                if fc4.button("✖", key=f"del_fol_{r_idx}_{f_idx}"):
                    seguito_da_rimuovere.append(f_idx)

            if seguito_da_rimuovere:
                for idx_f_del in sorted(seguito_da_rimuovere, reverse=True):
                    reg["seguito"].pop(idx_f_del)
                st.rerun()

    if reggimenti_da_rimuovere:
        for idx_r_del in sorted(reggimenti_da_rimuovere, reverse=True):
            st.session_state["sdg_reggimenti"].pop(idx_r_del)
        st.rerun()

    # ==========================================
    # AGGREGAZIONE DATI DELL'ARMATA
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

    for r_idx, reg in enumerate(st.session_state["sdg_reggimenti"]):
        if reg.get("is_generale", False) and reg["leader"] in st.session_state["db_unita"]:
            ha_generale = True

        livello_magico_tot += int(reg.get("livello_mago", 0))
        livello_preti_tot += int(reg.get("livello_prete", 0))

        if reg["leader"] in st.session_state["db_unita"]:
            n_eroi += 1
            d_u = st.session_state["db_unita"][reg["leader"]]
            pt_u = int(d_u.get("punti", 0))
            n_mod_u = max(1, int(d_u.get("n_modelli", 1)))
            sal_mod_u = max(1, int(d_u.get("difesa", {}).get("salute_per_modello", 5)))
            hp_u = n_mod_u * sal_mod_u
            oc_u = stima_controllo_unita("Eroe (2 OC)", n_mod_u)

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

        for fol in reg["seguito"]:
            if fol["nome"] in st.session_state["db_unita"]:
                d_f = st.session_state["db_unita"][fol["nome"]]
                rinf = bool(fol.get("rinforzata", False))
                molt = 2 if rinf else 1
                pt_f = int(d_f.get("punti", 0)) * molt
                n_mod_f = max(1, int(d_f.get("n_modelli", 1))) * molt
                sal_mod_f = max(1, int(d_f.get("difesa", {}).get("salute_per_modello", 1)))
                hp_f = n_mod_f * sal_mod_f
                oc_f = stima_controllo_unita(fol.get("ruolo", "Fanteria Standard (1 OC/mod)"), n_mod_f)

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

    # ==========================================
    # SEZIONE 3: CRUSCOTTO E DIAGNOSI
    # ==========================================
    st.markdown('<div class="section-header">Cruscotto Tattico e Diagnosi della Lista</div>', unsafe_allow_html=True)
    st.caption("Verifica dei punti, controllo dei vincoli 4e e analisi approfondita delle sinergie d'armata.")

    with st.container(border=True):
        st.markdown('<div class="subsection-title">Controllo Punti e Regolamento</div>', unsafe_allow_html=True)
        perc_punti = min(1.0, punti_totali / float(limite_punti)) if limite_punti > 0 else 0.0
        st.progress(perc_punti, text=f"Punti Spesi: {punti_totali} / {limite_punti} pt ({(punti_totali/float(limite_punti))*100:.1f}%)")

        v1, v2, v3 = st.columns(3)
        if punti_totali <= limite_punti and punti_totali > 0:
            v1.success(f"Punti in Regola ({punti_totali}/{limite_punti})")
        elif punti_totali > limite_punti:
            v1.error(f"Sforamento di +{punti_totali - limite_punti} pt!")
        else:
            v1.warning("Nessuna unità inserita")

        if ha_generale:
            v2.success("Generale Designato: Sì")
        else:
            v2.error("Manca il Generale!")

        n_reg_attivi = len(st.session_state["sdg_reggimenti"])
        v3.success(f"Reggimenti (Drops): {n_reg_attivi}")

    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Pool Ferite Armata", f"{ferite_totali_armata} PF", f"{modelli_totali_armata} Modelli")
    m2.metric("Danno Medio (vs Save 4+)", f"{(danno_melee_armata + danno_tiro_armata):.1f} Danni", f"Mischia: {danno_melee_armata:.1f}")
    m3.metric("Potere Arcano", f"{livello_magico_tot} Cast / Unbind", f"{livello_preti_tot} Preghiere")
    m4.metric("Controllo Mappa (OC)", f"{oc_totale_armata} Punti OC", f"{len(unita_totali_schierate)} Unità")

    tab_diag, tab_matchup, tab_export = st.tabs([
        "Check-Up Strategico & Carenze",
        "Matrice Match-Up vs Armata Nemica",
        "Salvataggio & Pergamena Torneo"
    ])

    with tab_diag:
        st.markdown('<div class="subsection-title">Avvertimenti dello Stratega e Sinergie</div>', unsafe_allow_html=True)
        st.caption("Analisi specialistica focalizzata sui match-up contro Khorne, Kruleboyz e Sylvaneth.")

        with st.container(border=True):
            if len(unita_totali_schierate) == 0:
                st.info("Inserisci unità nei reggimenti per visualizzare la diagnosi strategica.")
            else:
                consigli_speciali = []
                
                # Sinergie specifiche Nighthaunt rilevate dal notebook
                if any("Knight of Shrouds" in u["chiave_db"] for u in unita_totali_schierate) and any("Guardian of Souls" in u["chiave_db"] for u in unita_totali_schierate):
                    consigli_speciali.append("✨ **Sinergia Warlord & Supporto:** Il *Knight of Shrouds* si cura con l'abilità *Stolen Hours*[cite: 2], mentre il *Guardian of Souls* potenzia i tiri per ferire con la lanterna (+1 Wound)[cite: 2]. Sfruttali insieme al centro della mischia.")
                
                if any("Spirit Hosts" in u["chiave_db"] for u in unita_totali_schierate):
                    consigli_speciali.append("🛡️ **Ancoraggio Difensivo (Spirit Hosts):** La loro abilità *Drawn to War* fornisce un eccezionale **Ward (4+)** a tutti gli eroi Nighthaunt di fanteria amici vicini[cite: 1, 2]. Ottimo scudo contro i danni mortali dei Kruleboyz e gli eroi di Khorne.")

                if any("Scriptor Mortis" in u["chiave_db"] for u in unita_totali_schierate):
                    consigli_speciali.append("⚖️ **Anticarro / Anti-Warlord (Scriptor Mortis):** Condanna il Warlord tank nemico (es. quello con Save al 2+) per conferire *Crit (Mortal)* alle tue unità fanteria vicine, bypassando completamente l'armatura[cite: 1, 2]!")

                if max_rend_armata < 2:
                    consigli_speciali.append("⚠️ **Attenzione al Rend:** La tua armata ha un Rend massimo limitato. Sfrutta la formazione *Death Stalkers* per aggiungere +1 Rend permanente al tuo bersaglio principale[cite: 1] e combina Fell Blades (-1 Save) per sfondare le corazze.")

                for cs in consigli_speciali:
                    st.markdown(f"- {cs}")

    # ==========================================
    # TAB 2: MATRICE MATCH-UP CON ARMATE NOTE
    # ==========================================
    with tab_matchup:
        st.markdown('<div class="subsection-title">Simulatore di Match-Up (Importa Armate Note o Personalizzate)</div>', unsafe_allow_html=True)
        st.caption("Seleziona un'armata avversaria nota (es. Khorne, Kruleboyz, Sylvaneth) oppure aggiungi unità nemiche singole per calcolare la percentuale di ferite inflitte in 1 turno.")

        with st.container(border=True):
            # Importa armata nota
            im1, im2 = st.columns([2, 1])
            scelta_armata_nota = im1.selectbox("Importa Armata Avversaria Nota:", ["--- Scegli armata nemica pre-configurata ---"] + list(ARMATE_NEMICHE_NOTE.keys()))
            if im2.button("Importa Armata", type="primary", use_container_width=True):
                if scelta_armata_nota != "--- Scegli armata nemica pre-configurata ---":
                    st.session_state["sdg_nemici_matchup"] = [dict(x) for x in ARMATE_NEMICHE_NOTE[scelta_armata_nota]]
                    st.toast(f"Armata '{scelta_armata_nota}' importata con successo!")
                    st.rerun()

            st.markdown("---")
            mc1, mc2, mc3 = st.columns([2.5, 1, 1])
            nemico_sel = mc1.selectbox("Oppure aggiungi singola unità nemica:", ["--- Scegli unità nemica dal DB ---"] + opzioni_db, key="sel_enemy_mu")
            nemico_rinf = mc2.checkbox("Rinforzata (x2)", value=False, key="chk_enemy_rinf")
            if mc3.button("➕ Aggiungi Nemico", use_container_width=True):
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
                st.markdown("**Armata Avversaria Attiva:** " + " | ".join(nem_str_list))
                if st.button("Svuota Armata Nemica"):
                    st.session_state["sdg_nemici_matchup"] = []
                    st.rerun()

        if len(unita_totali_schierate) > 0 and len(st.session_state["sdg_nemici_matchup"]) > 0:
            matrice_matchup = {}
            consigli_matchup = []

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

                col_label = f"{nem_item['nome']}" + (" (x2)" if nem_item["rinforzata"] else "")
                col_percentuali = []

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

                matrice_matchup[col_label] = col_percentuali
                consigli_matchup.append(f"🎯 **Target Priority:** Concentra i tuoi attacchi su **{col_label}** usando la formazione *Death Stalkers* per azzerarne la difesa.")

            df_mu = pd.DataFrame(matrice_matchup, index=[u["etichetta"] for u in unita_totali_schierate])
            st.markdown("#### Matrice di Efficienza (% Salute Nemica Rimossa in 1 Turno)")
            st.dataframe(df_mu.style.background_gradient(cmap="YlOrBr", vmin=0, vmax=100).format("{:.1f}%"), use_container_width=True)

            with st.container(border=True):
                st.markdown("#### Suggerimenti Tattici di Battaglia")
                for cm in consigli_matchup:
                    st.markdown(f"- {cm}")
        else:
            st.info("Schiera unità nella tua armata e importa un'armata nemica (o aggiungi singoli nemici) per generare la matrice.")

    # ==========================================
    # TAB 3: SALVATAGGIO E ESPORTAZIONE
    # ==========================================
    with tab_export:
        st.markdown('<div class="subsection-title">Salvataggio & Esportazione Torneo</div>', unsafe_allow_html=True)
        st.caption("Salva l'armata nell'archivio JSON o copia il testo formattato per i tornei Path to Glory.")

        with st.container(border=True):
            if st.button("💾 Salva Armata nell'Archivio", type="primary"):
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
                st.toast(f"Armata '{chiave_armata}' salvata con successo!")
                st.rerun()

            linee_export = [
                f"=== {st.session_state['sdg_nome_armata'].upper()} ===",
                f"Fazione: {st.session_state['sdg_fazione_armata']} | Formazione: {st.session_state['sdg_formazione_battaglia']}",
                f"Punti Totali: {punti_totali} / {limite_punti} pt | Reggimenti: {len(st.session_state['sdg_reggimenti'])}",
                f"Ferite Totali: {ferite_totali_armata} PF | Controllo: {oc_totale_armata} OC",
                "-" * 55
            ]

            for r_i, reg in enumerate(st.session_state["sdg_reggimenti"]):
                gen_tag = " [GENERALE]" if reg.get("is_generale", False) else ""
                d_l = st.session_state["db_unita"].get(reg["leader"], {})
                linee_export.append(f"\nREGGIMENTO {r_i+1}:")
                linee_export.append(f"  • Leader: {reg['leader']}{gen_tag} ({int(d_l.get('punti', 0))} pt)")
                if reg.get("tratto_eroico", "Nessuno") != "Nessuno":
                    linee_export.append(f"    - Tratto: {reg['tratto_eroico']}")
                if reg.get("artefatto", "Nessuno") != "Nessuno":
                    linee_export.append(f"    - Artefatto: {reg['artefatto']}")
                for fol in reg["seguito"]:
                    d_f = st.session_state["db_unita"].get(fol["nome"], {})
                    molt = 2 if fol.get("rinforzata", False) else 1
                    rinf_str = " [Rinforzata]" if fol.get("rinforzata", False) else ""
                    linee_export.append(f"  • Seguito: {fol['nome']}{rinf_str} ({int(d_f.get('punti', 0))*molt} pt)")

            testo_completo_export = "\n".join(linee_export)
            st.text_area("Pergamena dell'Esercito:", value=testo_completo_export, height=300)