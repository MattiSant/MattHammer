import streamlit as st
import numpy as np
import pandas as pd
import json
import os
import re
from core_engine import calcola_arma_analitico, _push_su_github_file

# Usa percorsi assoluti per evitare scritture in cartelle errate al riavvio
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARMIES_DB_FILE = os.path.join(BASE_DIR, "armies_db.json")
FORMATIONS_DB_FILE = os.path.join(BASE_DIR, "formations.json")
TRAITS_DB_FILE = os.path.join(BASE_DIR, "heroic_traits_db.json")
ARTEFACTS_DB_FILE = os.path.join(BASE_DIR, "artefacts_db.json")

# ==========================================
# GESTIONE ARCHIVI JSON E SUPPORTO
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
    successo, messaggio = _push_su_github_file(ARMIES_DB_FILE, armate_dict, "Aggiornamento Roster Armata")
    if not successo:
        st.warning(messaggio)
    return True

def carica_formazioni_db():
    if os.path.exists(FORMATIONS_DB_FILE):
        try:
            with open(FORMATIONS_DB_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return {}
    return {}

def carica_db_supporto(file_path):
    if os.path.exists(file_path):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                dati = json.load(f)
                if isinstance(dati, dict):
                    # Se è già il nuovo formato (chiavi = nomi), restituisce le chiavi
                    if "Generali" not in dati:
                        return list(dati.keys())
                    # Se è il vecchio formato a liste
                    return dati.get("Generali", ["Nessuno"])
                return ["Nessuno"]
        except Exception:
            return ["Nessuno"]
    return ["Nessuno"]

db_tratti_eroici = carica_db_supporto(TRAITS_DB_FILE)
db_artefatti = carica_db_supporto(ARTEFACTS_DB_FILE)

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
        {"nome": "Sylvaneth: Kurnoth Hunters With Greatswords", "rinforzata": False}
    ]
}

# ==========================================
# FUNZIONI DI CALCOLO E SUPPORTO TATTICO
# ==========================================
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

def estrai_intero_sicuro(valore, default=0):
    if isinstance(valore, (int, float)):
        return int(valore)
    if isinstance(valore, str):
        match = re.search(r"\d+", valore)
        if match:
            return int(match.group(0))
    return default

def calcola_output_unita_su_bersaglio(dati_unita_db, rinforzata, bersaglio_test):
    armi = dati_unita_db.get("armi", [])
    n_mod_base = max(1, estrai_intero_sicuro(dati_unita_db.get("n_modelli", 1), default=1))
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
            r_val = estrai_intero_sicuro(a.get("rend", 0), default=0)
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
        .warscroll-box {
            background: linear-gradient(135deg, #1c150e 0%, #120e0a 100%);
            border: 2px solid #8c6d46;
            border-radius: 6px;
            padding: 12px;
            margin-top: 8px;
            margin-bottom: 12px;
            color: #f4ecd8;
        }
        .ability-box {
            background: rgba(45, 29, 17, 0.6);
            border-left: 4px solid #b38b4d;
            border: 1px solid #5c4730;
            padding: 8px 12px;
            margin: 6px 0;
            border-radius: 3px;
        }
        .ability-box-reaction {
            background: rgba(55, 18, 18, 0.65);
            border-left: 4px solid #c0392b;
            border: 1px solid #78281f;
            padding: 8px 12px;
            margin: 6px 0;
            border-radius: 3px;
        }
    </style>
    """, unsafe_allow_html=True)

    st.title("MattHammer — Sala di Guerra")
    st.caption("Costruttore d'armata avanzato per Reggimenti (AoS 4e), gestione formazioni e simulatore di Match-Up.")

    # Inizializzazione Session State
    if "archivio_formazioni" not in st.session_state:
        st.session_state["archivio_formazioni"] = carica_formazioni_db()
    if "archivio_armate" not in st.session_state:
        st.session_state["archivio_armate"] = carica_archivio_armate()
    if "sdg_roster_version" not in st.session_state:
        st.session_state["sdg_roster_version"] = 0
    if "sdg_reggimenti" not in st.session_state or not isinstance(st.session_state["sdg_reggimenti"], list) or len(st.session_state["sdg_reggimenti"]) == 0:
        st.session_state["sdg_reggimenti"] = [
            {
                "leader": "--- Scegli Eroe Leader ---",
                "is_generale": True,
                "rinforzato": False,
                "tratto_eroico": "Nessuno",
                "artefatto": "Nessuno",
                "seguito": []
            }
        ]
    if "sdg_ausiliari" not in st.session_state:
        st.session_state["sdg_ausiliari"] = []
    if "sdg_nemici_matchup" not in st.session_state:
        st.session_state["sdg_nemici_matchup"] = []
    
    if "db_tratti_eroici" not in st.session_state:
        st.session_state["db_tratti_eroici"] = carica_db_supporto(TRAITS_DB_FILE).get("Generali", ["Nessuno"])
    if "db_artefatti" not in st.session_state:
        st.session_state["db_artefatti"] = carica_db_supporto(ARTEFACTS_DB_FILE).get("Generali", ["Nessuno"])

    db_tratti_eroici = st.session_state["db_tratti_eroici"]
    db_artefatti = st.session_state["db_artefatti"]

    if "sdg_nome_armata" not in st.session_state:
        st.session_state["sdg_nome_armata"] = "Armata Path to Glory"
    if "sdg_fazione_armata" not in st.session_state:
        st.session_state["sdg_fazione_armata"] = "Nighthaunt"
    if "sdg_formazione_scelta" not in st.session_state:
        st.session_state["sdg_formazione_scelta"] = "Death Stalkers"

    opzioni_db = [k for k in st.session_state["db_unita"].keys() if k != "--- Seleziona o Resetta ---"]

    # ==========================================
    # SEZIONE 1: GENERALITÀ DELL'ARMATA E FORMAZIONE
    # ==========================================
    st.markdown('<div class="section-header">Configurazione Schieramento e Formazione</div>', unsafe_allow_html=True)
    st.caption("Definisci le generalità dell'esercito, il formato della battaglia e la Formazione tattica associata con i relativi bonus.")

    with st.container(border=True):
        st.markdown('<div class="subsection-title">Generalità dell\'Esercito</div>', unsafe_allow_html=True)
        
        col_f1, col_f2, col_f3, col_f4 = st.columns([1.5, 1.2, 1.3, 1])
        st.session_state["sdg_nome_armata"] = col_f1.text_input("Nome della Lista", value=st.session_state["sdg_nome_armata"])
        
        lista_fazioni_disp = ["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Grande Alleanza / Altro"]
        idx_faz = lista_fazioni_disp.index(st.session_state["sdg_fazione_armata"]) if st.session_state["sdg_fazione_armata"] in lista_fazioni_disp else 0
        st.session_state["sdg_fazione_armata"] = col_f2.selectbox("Fazione", lista_fazioni_disp, index=idx_faz)

        formato_scelto = col_f3.selectbox(
            "Formato Battaglia",
            ["Path to Glory (720 pt Personalizzati)", "Path to Glory Standard (600 pt)", "Vanguard (1000 pt)", "Strike Force (1500 pt)", "Battlehost (2000 pt)", "Personalizzato (Custom)"],
            index=0
        )

        if "720" in formato_scelto:
            limite_punti = 720
        elif "600" in formato_scelto:
            limite_punti = 600
        elif "1000" in formato_scelto:
            limite_punti = 1000
        elif "1500" in formato_scelto:
            limite_punti = 1500
        elif "2000" in formato_scelto:
            limite_punti = 2000
        else:
            limite_punti = col_f4.number_input("Punti Custom", min_value=100, max_value=5000, value=720, step=10)

        st.markdown("---")
        st.markdown('<div class="subsection-title">Formazione di Battaglia (Battle Formation)</div>', unsafe_allow_html=True)
        st.caption("Formazione ufficiale associata all'armata. Regole, fasi d'attivazione e modificatori numerici sono pre-impostati da database.")

        fazioni_disponibili_db = st.session_state["archivio_formazioni"]
        formazioni_fazione = fazioni_disponibili_db.get(st.session_state["sdg_fazione_armata"], {
            "Formazione Standard": {
                "fase_attivazione": "Nessuna", "monouso": False, "tipo_effetto": "Nessuno", "valore_modificatore": "0", "descrizione": "Nessuna abilità speciale attiva."
            }
        })

        lista_nomi_formazioni = list(formazioni_fazione.keys()) if isinstance(formazioni_fazione, dict) else ["Formazione Standard"]
        idx_form = lista_nomi_formazioni.index(st.session_state["sdg_formazione_scelta"]) if st.session_state["sdg_formazione_scelta"] in lista_nomi_formazioni else 0
        
        formazione_selezionata = st.selectbox("Nome Formazione", lista_nomi_formazioni, index=idx_form)
        st.session_state["sdg_formazione_scelta"] = formazione_selezionata

        dati_form = formazioni_fazione.get(formazione_selezionata, {
            "fase_attivazione": "Hero Phase", "monouso": False, "tipo_effetto": "Nessuno", "valore_modificatore": "0", "descrizione": "Descrizione non disponibile."
        })

        fc1, fc2, fc3 = st.columns([1.2, 1, 1.8])
        with fc1:
            st.markdown(f"**Categoria Effetto:** `{dati_form.get('tipo_effetto', 'Nessuno')}`")
            st.markdown(f"**Modificatore Fisso:** `{dati_form.get('valore_modificatore', '+0')}`")

        with fc2:
            st.markdown(f"**Fase di Attivazione:**\n`{dati_form.get('fase_attivazione', 'Nessuna')}`")
            is_monouso_str = "Sì (Una volta per battaglia)" if dati_form.get('monouso', False) else "No (Ricorrente / Passiva)"
            st.markdown(f"**Monouso:** `{is_monouso_str}`")

        with fc3:
            st.markdown("**Regola & Descrizione Ufficiale:**")
            st.info(dati_form.get('descrizione', 'Nessun dettaglio inserito.'))

    # ==========================================
    # SEZIONE 2: COMPOSIZIONE REGGIMENTI
    # ==========================================
    st.markdown('<div class="section-header">Composizione Reggimenti</div>', unsafe_allow_html=True)
    st.caption("Il Reggimento #1 è guidato dal Generale d'Armata. I leader devono possedere la keyword HERO.")

    col_btn_reg1, col_btn_reg2 = st.columns([1, 3])
    if col_btn_reg1.button("➕ Aggiungi Reggimento", type="primary", use_container_width=True):
        st.session_state["sdg_reggimenti"].append({
            "leader": "--- Scegli Eroe Leader ---",
            "is_generale": False,
            "rinforzato": False,
            "tratto_eroico": "Nessuno",
            "artefatto": "Nessuno",
            "seguito": []
        })
        st.rerun()

    if col_btn_reg2.button("Svuota Roster Completo"):
        # 1. Pulisce tutte le chiavi dei widget di Streamlit legate ai reggimenti
        chiavi_da_eliminare = [
            k for k in st.session_state.keys()
            if k.startswith("reg_lead_") or k.startswith("reg_trait_") or k.startswith("reg_art_") or k.startswith("fol_")
        ]
        for k in chiavi_da_eliminare:
            del st.session_state[k]

        # 2. Resetta la struttura dati del Reggimento #1
        st.session_state["sdg_reggimenti"] = [{
            "leader": "--- Scegli Eroe Leader ---",
            "is_generale": True,
            "rinforzato": False,
            "tratto_eroico": "Nessuno",
            "artefatto": "Nessuno",
            "seguito": []
        }]
        st.session_state["sdg_ausiliari"] = []
        
        # 3. Incrementa la versione per costringere Streamlit a ricreare i widget da zero
        st.session_state["sdg_roster_version"] += 1
        st.rerun()

    eroi_db_filtrati = []
    for k_unita in opzioni_db:
        dati_u_temp = st.session_state["db_unita"].get(k_unita, {})
        keywords_u = [str(kw).upper() for kw in dati_u_temp.get("keywords", ["HERO"])]
        if "HERO" in keywords_u or not dati_u_temp.get("keywords"): 
            eroi_db_filtrati.append(k_unita)

    if not eroi_db_filtrati:
        eroi_db_filtrati = opzioni_db

    reggimenti_da_rimuovere = []

    for r_idx, reg in enumerate(st.session_state["sdg_reggimenti"]):
        if r_idx == 0:
            reg["is_generale"] = True

        with st.container(border=True):
            head_c1, head_c2 = st.columns([4, 1])
            etichetta_gen = " — ★ GENERALE D'ARMATA (Reggimento Principale)" if reg.get("is_generale", False) else f" — Reggimento #{r_idx+1}"
            head_c1.markdown(f'<div class="subsection-title">{etichetta_gen}</div>', unsafe_allow_html=True)
            
            if r_idx > 0:
                if head_c2.button("🗑️ Rimuovi", key=f"del_reg_{r_idx}", use_container_width=True):
                    reggimenti_da_rimuovere.append(r_idx)

            lc1, lc2 = st.columns([2.5, 1.5])
            lista_scelta_leader = ["--- Scegli Eroe Leader ---"] + eroi_db_filtrati
            idx_lead = lista_scelta_leader.index(reg["leader"]) if reg["leader"] in lista_scelta_leader else 0
            
            # Selectbox Leader con chiave dinamica di versione
            reg["leader"] = lc1.selectbox(
                "Leader (Solo Eroi)", 
                lista_scelta_leader, 
                index=idx_lead, 
                key=f"reg_lead_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

            ruolo_magico_str = "Nessun Potere Arcano"
            if reg["leader"] in st.session_state["db_unita"]:
                dati_l_db = st.session_state["db_unita"][reg["leader"]]
                kw_l = dati_l_db.get("keywords", [])
                lvl_w = estrai_livello_potere(kw_l, "Wizard")
                lvl_p = estrai_livello_potere(kw_l, "Priest")
                
                pezzi_ruolo = []
                if lvl_w > 0: pezzi_ruolo.append(f"🔮 Mago ({lvl_w})")
                if lvl_p > 0: pezzi_ruolo.append(f"✨ Prete ({lvl_p})")
                if pezzi_ruolo:
                    ruolo_magico_str = " | ".join(pezzi_ruolo)

            lc2.markdown(f"**Ruolo Magico/Religioso:**\n`{ruolo_magico_str}`")

            tc1, tc2 = st.columns(2)
            idx_tratto = db_tratti_eroici.index(reg.get("tratto_eroico", "Nessuno")) if reg.get("tratto_eroico", "Nessuno") in db_tratti_eroici else 0
            
            # Selectbox Tratto Eroico con chiave dinamica di versione
            reg["tratto_eroico"] = tc1.selectbox(
                "Tratto Eroico (Heroic Trait)", 
                db_tratti_eroici, 
                index=idx_tratto, 
                key=f"reg_trait_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

            idx_art = db_artefatti.index(reg.get("artefatto", "Nessuno")) if reg.get("artefatto", "Nessuno") in db_artefatti else 0
            
            # Selectbox Artefatto con chiave dinamica di versione
            reg["artefatto"] = tc2.selectbox(
                "Artefatto di Potere", 
                db_artefatti, 
                index=idx_art, 
                key=f"reg_art_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )

            if reg["leader"] in st.session_state["db_unita"]:
                d_lead = st.session_state["db_unita"][reg["leader"]]
                stat_c = d_lead.get("statistiche_cerchio", {})
                dif_lead = d_lead.get("difesa", {})
                
                mov_val = stat_c.get("movimento", "6\"")
                oc_val = stat_c.get("controllo", 2)
                sv_val = stat_c.get("save", f"{dif_lead.get('save', 5)}+")
                hp_val = stat_c.get("salute", dif_lead.get("salute_per_modello", 5))
                wd_val = stat_c.get("ward", f"{dif_lead.get('ward', 5)}+")

                st.markdown(f"""
                <div class="warscroll-box">
                    <strong style="color: #f5d680;">📜 Sunto Warscroll — {reg['leader']}</strong><br>
                    <b>Punti:</b> {d_lead.get('punti', 0)} pt | <b>Basetta:</b> {d_lead.get('dimensione_basetta', 'Standard')} | <b>Movimento:</b> {mov_val} | <b>Controllo (OC):</b> {oc_val} | <b>Save:</b> {sv_val} | <b>Salute:</b> {hp_val} | <b>Ward:</b> {wd_val}
                </div>
                """, unsafe_allow_html=True)

                abilita_leader = d_lead.get("abilita", [])
                if abilita_leader:
                    st.markdown("**Abilità della Warscroll:**")
                    for ab in abilita_leader:
                        is_reaz = ab.get("reazione", False)
                        classe_box = "ability-box-reaction" if is_reaz else "ability-box"
                        reaz_txt = "🔴 Reaction: " if is_reaz else "🟢 "
                        fasi_txt = ", ".join(ab.get("fasi", ["Generica"]))
                        st.markdown(f"""
                        <div class="{classe_box}">
                            <small style="color: #d8c29d;"><b>[{fasi_txt}]</b></small><br>
                            <b>{reaz_txt}{ab.get('nome', 'Abilità')}</b>: {ab.get('descrizione', '')}
                        </div>
                        """, unsafe_allow_html=True)

            st.markdown("---")
            max_seguito = 4 if reg.get("is_generale", False) else 3
            st.markdown(f"**Seguito ({len(reg['seguito'])} / {max_seguito} slot occupati):**")

            sc_add1, sc_add2 = st.columns([3, 1])
            unita_seg_sel = sc_add1.selectbox(
                "Aggiungi unità di seguito:", 
                ["--- Scegli unità ---"] + opzioni_db, 
                key=f"sel_add_seg_{r_idx}_v{st.session_state['sdg_roster_version']}"
            )    
            if sc_add2.button("➕ Aggiungi", key=f"btn_add_seg_{r_idx}", use_container_width=True):
                if unita_seg_sel != "--- Scegli unità ---":
                    if len(reg["seguito"]) < max_seguito:
                        reg["seguito"].append({
                            "nome": unita_seg_sel,
                            "rinforzata": False
                        })
                        st.rerun()
                    else:
                        st.warning("Limite slot seguito raggiunto per questo reggimento.")

            seguito_da_rimuovere = []
            for f_idx, fol in enumerate(reg["seguito"]):
                d_fol_db = st.session_state["db_unita"].get(fol["nome"], {})
                puo_rinf = d_fol_db.get("può_essere_rinforzata", True)
                molt = 2 if fol.get("rinforzata", False) else 1
                
                fc1, fc2, fc3 = st.columns([3, 1.5, 0.6])
                fc1.markdown(f"• **{fol['nome']}** ({estrai_intero_sicuro(d_fol_db.get('n_modelli', 1))*molt} mod. — `{estrai_intero_sicuro(d_fol_db.get('punti', 0))*molt} pt`)")
                
                if puo_rinf:
                    fol["rinforzata"] = fc2.checkbox("Rinforzata (x2)", value=fol.get("rinforzata", False), key=f"fol_rinf_{r_idx}_{f_idx}")
                else:
                    fc2.caption("Non rinforzabile")
                    fol["rinforzata"] = False

                if fc3.button("✖", key=f"del_fol_{r_idx}_{f_idx}"):
                    seguito_da_rimuovere.append(f_idx)

                stat_cf = d_fol_db.get("statistiche_cerchio", {})
                dif_f = d_fol_db.get("difesa", {})
                m_f = stat_cf.get("movimento", "6\"")
                oc_f = stat_cf.get("controllo", 1)
                s_f = stat_cf.get("save", f"{dif_f.get('save', 6)}+")
                w_f = stat_cf.get("ward", f"{dif_f.get('ward', 5)}+")
                
                st.markdown(f"""
                <div style="font-size: 0.88rem; background: rgba(0,0,0,0.25); border-left: 2px solid #8c6d46; padding: 5px 8px; border-radius: 4px; margin-bottom: 6px;">
                    Move: <b>{m_f}</b> | OC Base: <b>{oc_f}</b> | Save: <b>{s_f}</b> | Ward: <b>{w_f}</b> | Basetta: <b>{d_fol_db.get('dimensione_basetta', 'Standard')}</b>
                </div>
                """, unsafe_allow_html=True)

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

        if reg["leader"] in st.session_state["db_unita"]:
            n_eroi += 1
            d_u = st.session_state["db_unita"][reg["leader"]]
            pt_u = estrai_intero_sicuro(d_u.get("punti", 0))
            n_mod_u = max(1, estrai_intero_sicuro(d_u.get("n_modelli", 1), default=1))
            dif_u = d_u.get("difesa", {})
            sal_mod_u = max(1, estrai_intero_sicuro(d_u.get("statistiche_cerchio", {}).get("salute", dif_u.get("salute_per_modello", 5)), default=5))
            hp_u = n_mod_u * sal_mod_u
            oc_u = estrai_intero_sicuro(d_u.get("statistiche_cerchio", {}).get("controllo", 2), default=2)

            kw_u = d_u.get("keywords", [])
            livello_magico_tot += estrai_livello_potere(kw_u, "Wizard")
            livello_preti_tot += estrai_livello_potere(kw_u, "Priest")

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
                pt_f = estrai_intero_sicuro(d_f.get("punti", 0)) * molt
                n_mod_f = max(1, estrai_intero_sicuro(d_f.get("n_modelli", 1), default=1)) * molt
                dif_f = d_f.get("difesa", {})
                sal_mod_f = max(1, estrai_intero_sicuro(d_f.get("statistiche_cerchio", {}).get("salute", dif_f.get("salute_per_modello", 1)), default=1))
                hp_f = n_mod_f * sal_mod_f
                oc_f = estrai_intero_sicuro(d_f.get("statistiche_cerchio", {}).get("controllo", 1), default=1) * n_mod_f

                kw_f = d_f.get("keywords", [])
                livello_magico_tot += estrai_livello_potere(kw_f, "Wizard")
                livello_preti_tot += estrai_livello_potere(kw_f, "Priest")

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
        if 0 < punti_totali <= limite_punti:
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
        st.caption("Seleziona un'armata avversaria nota oppure aggiungi unità nemiche singole per calcolare la percentuale di ferite inflitte in 1 turno.")

        with st.container(border=True):
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
                stat_nem = d_nem.get("statistiche_cerchio", {})
                molt_n = 2 if nem_item.get("rinforzata", False) else 1
                
                sv_n = estrai_intero_sicuro(stat_nem.get("save", dif_nem.get("save", 4)), default=4)
                wd_n = estrai_intero_sicuro(stat_nem.get("ward", dif_nem.get("ward", 7)), default=7)
                n_mod_n = estrai_intero_sicuro(d_nem.get("n_modelli", 1), default=1) * molt_n
                sal_mod_n = estrai_intero_sicuro(stat_nem.get("salute", dif_nem.get("salute_per_modello", 1)), default=1)
                hp_n = max(1, n_mod_n * sal_mod_n)
                pt_n = estrai_intero_sicuro(d_nem.get("punti", 0)) * molt_n

                col_label = f"{nem_item['nome']}" + (" (x2)" if nem_item["rinforzata"] else "")
                col_percentuali = []
                kw_nemico = [str(k).upper() for k in d_nem.get("keywords", [])]
                is_nemico_etereo = (
                    "nighthaunt" in nem_item["nome"].lower()
                    or "nighthaunt" in d_nem.get("fazione", "").lower()
                    or any(k in ["NIGHTHAUNT", "ETHEREAL", "ETHEREO", "SPIRIT"] for k in kw_nemico)
                )

                is_nemico_etereo = ("nighthaunt" in nem_item["nome"].lower()) or ("nighthaunt" in d_nem.get("fazione", "").lower())
                bersaglio_nem_struct = {
                    "save": sv_n, "ward": wd_n, "salute": hp_n, "keywords": ["INFANTRY", "HERO"],
                    "cover": False, "aod": False, "bonus_save_extra": 0,
                    "obscuring": False, "bersaglio_ha_caricato": False,
                    "mod_ward_penalita": 0, "blocca_ward": False, "mod_wnd_nerf": 0,
                    "immune_rend": is_nemico_etereo
                }

                for mia_u in unita_totali_schierate:
                    d_mia = st.session_state["db_unita"].get(mia_u["chiave_db"], {})
                    ris_scontro = calcola_output_unita_su_bersaglio(d_mia, mia_u["rinforzata"], bersaglio_nem_struct)
                    perc_kill_1t = min(100.0, (ris_scontro["danno_totale"] / float(hp_n)) * 100.0)
                    col_percentuali.append(round(perc_kill_1t, 1))

                matrice_matchup[col_label] = col_percentuali
                consigli_matchup.append(f"🎯 **Target Priority:** Concentra i tuoi attacchi su **{col_label}** usando la formazione *Death Stalkers* per azzerarne la difesa[cite: 1].")

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
                    "formazione": st.session_state["sdg_formazione_scelta"],
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
                f"Fazione: {st.session_state['sdg_fazione_armata']} | Formazione: {st.session_state['sdg_formazione_scelta']}",
                f"Punti Totali: {punti_totali} / {limite_punti} pt | Reggimenti: {len(st.session_state['sdg_reggimenti'])}",
                f"Ferite Totali: {ferite_totali_armata} PF | Controllo: {oc_totale_armata} OC",
                "-" * 55
            ]

            for r_i, reg in enumerate(st.session_state["sdg_reggimenti"]):
                gen_tag = " [GENERALE]" if reg.get("is_generale", False) else ""
                d_l = st.session_state["db_unita"].get(reg["leader"], {})
                linee_export.append(f"\nREGGIMENTO {r_i+1}:")
                linee_export.append(f"  • Leader: {reg['leader']}{gen_tag} ({estrai_intero_sicuro(d_l.get('punti', 0))} pt)")
                if reg.get("tratto_eroico", "Nessuno") != "Nessuno":
                    linee_export.append(f"    - Tratto: {reg['tratto_eroico']}")
                if reg.get("artefatto", "Nessuno") != "Nessuno":
                    linee_export.append(f"    - Artefatto: {reg['artefatto']}")
                for fol in reg["seguito"]:
                    d_f = st.session_state["db_unita"].get(fol["nome"], {})
                    molt = 2 if fol.get("rinforzata", False) else 1
                    rinf_str = " [Rinforzata]" if fol.get("rinforzata", False) else ""
                    linee_export.append(f"  • Seguito: {fol['nome']}{rinf_str} ({estrai_intero_sicuro(d_f.get('punti', 0))*molt} pt)")

            testo_completo_export = "\n".join(linee_export)
            st.text_area("Pergamena dell'Esercito:", value=testo_completo_export, height=300)