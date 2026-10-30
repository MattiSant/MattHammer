import streamlit as st
import re
import json
import os
from core_engine import (
    ordina_unita_per_fazione_e_nome, 
    ordina_supporti_per_fazione_e_nome, 
    salva_nel_database
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FORMATIONS_FILE = os.path.join(BASE_DIR, "formations.json")
TRAITS_FILE = os.path.join(BASE_DIR, "heroic_traits_db.json")
ARTEFACTS_FILE = os.path.join(BASE_DIR, "artefacts_db.json")

def _carica_json_ausiliario(filepath, default):
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return default
    return default

def _salva_json_ausiliario(filepath, dati):
    successo, messaggio = _push_su_github_file(filepath, dati, "Aggiornamento Archivio Ausiliario")
    if not successo:
        st.error(messaggio)
    return successo

def estrai_intero_da_stringa(testo, default=0):
    match = re.search(r"\d+", str(testo))
    return int(match.group(0)) if match else default

def analizza_testo_copiato_robusto(testo):
    armi_estratte = []
    pattern_stat = r'(?:(\d+\")\s+)?((?:\d+|[1-9]?D\d+(?:\+\d+)?|D\d+))\s+(\d)\+\s+(\d)\+\s+(\d|---|0|-)\s+((?:\d+|[1-9]?D\d+(?:\+\d+)?|D\d+))$'
    
    # Set di parole chiave che compongono le intestazioni delle tabelle
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
    if "forgia_nome" not in st.session_state:
        st.session_state["forgia_nome"] = ""
    if "forgia_keywords" not in st.session_state:
        st.session_state["forgia_keywords"] = ""

    v_key = st.session_state["forgia_version"]

    opzioni_db = ordina_unita_per_fazione_e_nome(st.session_state["db_unita"])    
    tab_unita, tab_formazioni, tab_tratti_artefatti, tab_elimina = st.tabs([
        "📜 Forgia Warscroll",
        "⚔️ Formazioni di Battaglia",
        "✨ Tratti & Artefatti",
        "🗑️ Gestione / Elimina Unità"
    ])

    with tab_unita:
        
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
                    st.session_state["forgia_keywords"] = ", ".join(d_load.get("keywords", []))

                    abilita_caricate = d_load.get("abilita", [])
                    for ab in abilita_caricate:
                        if "modificatori" not in ab or not isinstance(ab["modificatori"], dict):
                            ab["modificatori"] = {}
                    st.session_state["forgia_abilita"] = abilita_caricate

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
        # DATI GENERALI E STATISTICHE DIFENSIVE
        # ==========================================
        st.markdown('<div class="section-header">1. Generalità e Statistiche Difensive</div>', unsafe_allow_html=True)    
        
        with st.container(border=True):
            g1, g2, g3 = st.columns([1.5, 2, 1])
            fazione = g1.selectbox("Fazione", ["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Altro"], index=["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Altro"].index(st.session_state.get("forgia_fazione", "Nighthaunt")), key=f"f_faz_{v_key}")
            st.session_state["forgia_fazione"] = fazione
            
            nome = g2.text_input("Nome Unità", value=st.session_state.get("forgia_nome", ""), key=f"f_nome_{v_key}")
            st.session_state["forgia_nome"] = nome
            
            punti = g3.number_input("Costo in Punti", min_value=10, max_value=2000, value=st.session_state.get("forgia_punti", 100), step=10, key=f"f_pt_{v_key}")
            st.session_state["forgia_punti"] = punti

            g4, g5, g6, g7 = st.columns(4)
            n_modelli = g4.number_input("Modelli Base", min_value=1, max_value=60, value=st.session_state.get("forgia_modelli", 1), key=f"f_mod_{v_key}")
            st.session_state["forgia_modelli"] = n_modelli
            
            basetta = g5.text_input("Dimensione Basetta", value=st.session_state.get("forgia_basetta", "32mm"), key=f"f_base_{v_key}")
            st.session_state["forgia_basetta"] = basetta
            
            puo_rinf = g6.checkbox("Può essere Rinforzata (x2)", value=st.session_state.get("forgia_rinf", False), key=f"f_rinf_{v_key}")
            st.session_state["forgia_rinf"] = puo_rinf
            
            campione = g7.checkbox("Presenza Campione (+1 Atk)", value=st.session_state.get("forgia_campione", False), key=f"f_camp_{v_key}")
            st.session_state["forgia_campione"] = campione

            st.markdown("---")
            st.markdown("**Statistiche Difensive (Warscroll)**")
            c1, c2, c3, c4, c5 = st.columns(5)
            move = c1.text_input("Movimento (es. 8\" Fly)", value=st.session_state.get("forgia_movimento", "6\""), key=f"f_mov_{v_key}")
            st.session_state["forgia_movimento"] = move
            
            oc = c2.number_input("Controllo (OC)", min_value=0, max_value=20, value=st.session_state.get("forgia_controllo", 1), key=f"f_oc_{v_key}")
            st.session_state["forgia_controllo"] = oc
            
            save = c3.selectbox("Save (Armatura)", ["2+", "3+", "4+", "5+", "6+", "-"], index=["2+", "3+", "4+", "5+", "6+", "-"].index(st.session_state.get("forgia_save", "4+")), key=f"f_sv_{v_key}")
            st.session_state["forgia_save"] = save
            
            salute = c4.number_input("Salute (Ferite)", min_value=1, max_value=50, value=st.session_state.get("forgia_salute", 2), key=f"f_hp_{v_key}")
            st.session_state["forgia_salute"] = salute
            
            ward = c5.selectbox("Ward (Tiro Salvezza Magico)", ["4+", "5+", "6+", "7+", "-"], index=["4+", "5+", "6+", "7+", "-"].index(st.session_state.get("forgia_ward", "7+")), key=f"f_wd_{v_key}")
            st.session_state["forgia_ward"] = ward

        # ==========================================
        # ARMI
        # ==========================================
        st.markdown('<div class="section-header">2. Profili di Combattimento (Armi)</div>', unsafe_allow_html=True)
        with st.container(border=True):
            st.caption("Copia le statistiche dal manuale (es. 'Tomb Greatblade 2 3+ 3+ 1 1') e usa l'inserimento rapido.")
            txt_armi = st.text_area("Inserimento Rapido Armi:", height=68, key=f"f_txt_armi_{v_key}")
            if st.button("Analizza e Aggiungi Armi"):
                armi_estratte = analizza_testo_copiato_robusto(txt_armi)
                if armi_estratte:
                    st.session_state["forgia_armi"].extend(armi_estratte)
                    st.session_state["forgia_version"] += 1
                    st.rerun()
                else:
                    st.error("Nessun profilo riconosciuto! Assicurati che finisca con: Attacchi, Hit, Wound, Rend, Danno.")

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

                    opzioni_critico = ["Nessuno", "Crit (Mortal)", "Crit (Auto-wound)", "Crit (2 Hits)"]
                    tipo_critico_attuale = arma.get("crit_type", "Nessuno")
                    idx_crit = opzioni_critico.index(tipo_critico_attuale) if tipo_critico_attuale in opzioni_critico else 0

                    crit = ab1.selectbox(
                        "Critico", 
                        opzioni_critico, 
                        index=idx_crit, 
                        key=f"a_crt_{idx}_{v_key}"
                    )                   

                    opzioni_anti = ["Nessuno", "HERO", "INFANTRY", "CAVALRY", "MONSTER", "WAR MACHINE", "CHARGE"]
                    tipo_anti_attuale = arma.get("anti_target", "Nessuno")
                    idx_anti = opzioni_anti.index(tipo_anti_attuale) if tipo_anti_attuale in opzioni_anti else 0

                    anti = ab2.selectbox(
                        "Anti-Keyword (+1 Rend)", 
                        opzioni_anti, 
                        index=idx_anti, 
                        key=f"a_ant_{idx}_{v_key}"
                    )
                    
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
        # 3. ABILITÀ E KEYWORDS (CON MULTI-MODIFICATORE)
        # ==========================================
        st.markdown('<div class="section-header">3. Abilità e Keywords</div>', unsafe_allow_html=True)
        with st.container(border=True):
            if st.button("➕ Aggiungi Abilità Warscroll"):
                st.session_state["forgia_abilita"].append({
                    "nome": "Nuova Abilità", 
                    "tipo": "Ability", 
                    "reazione": False, 
                    "once_per_battle": False, 
                    "valore_lancio": 0, 
                    "fasi": ["Qualsiasi Fase"], 
                    "descrizione": "",
                    "modificatori": {}
                })
                st.session_state["forgia_version"] += 1
                st.rerun()

            abilita_aggiornate = []
            fasi_gioco = [
                "Qualsiasi Fase", "Deployment", "Hero Phase (Amica)", "Hero Phase (Nemica)", 
                "Movement Phase (Amica)", "Movement Phase (Nemica)", "Shooting Phase", 
                "Charge Phase", "Combat Phase", "Fine Turno"
            ]

            LABEL_TO_KEY_AB = {
                "Attacchi Extra (+Atk)": "bonus_atk",
                "Rend Extra (+Rend)": "bonus_rend",
                "Danno Extra (+Dmg)": "bonus_dmg",
                "Hit Bonus (+Hit)": "mod_hit",
                "Wound Bonus (+Wound)": "mod_wnd",
                "Save Migliorato (+Save)": "bonus_save",
                "Ward Fisso / Aura (es. 4+, 5+)": "ward_nativo",
                "Movimento Extra (+Move)": "bonus_movimento",
                "Controllo Extra (+OC)": "bonus_controllo",
                "Critico al 5+": "crit_on"
            }
            KEY_TO_LABEL_AB = {v: k for k, v in LABEL_TO_KEY_AB.items()}

            for a_idx, ab in enumerate(st.session_state["forgia_abilita"]):
                with st.expander(f"✨ {ab.get('nome', 'Abilità')}", expanded=True):
                    aa1, aa2 = st.columns([3, 1])
                    nome_ab = aa1.text_input("Nome Abilità", value=ab.get("nome", ""), key=f"ab_nome_{a_idx}_{v_key}")
                    if aa2.button("🗑️ Elimina", key=f"ab_del_{a_idx}_{v_key}"):
                        st.session_state["forgia_abilita"].pop(a_idx)
                        st.session_state["forgia_version"] += 1
                        st.rerun()

                    r1, r2, r3 = st.columns([1.2, 1.2, 2])
                    tipo = r1.selectbox(
                        "Tipo", 
                        ["Ability", "Passive", "Spell", "Prayer"], 
                        index=["Ability", "Passive", "Spell", "Prayer"].index(ab.get("tipo", "Ability")), 
                        key=f"ab_tipo_{a_idx}_{v_key}"
                    )
                    
                    val_lancio = 0
                    if tipo in ["Spell", "Prayer"]:
                        valore_salvato = int(ab.get("valore_lancio", 5) or 5)
                        val_lancio = r1.number_input("Valore di Lancio", min_value=1, max_value=12, value=max(1, valore_salvato), key=f"ab_lan_{a_idx}_{v_key}")

                    with r2:
                        reazione = st.checkbox("È una Reazione (Reaction)?", value=ab.get("reazione", False), key=f"ab_reaz_{a_idx}_{v_key}")
                        once_per_battle = st.checkbox("Once per Battle", value=ab.get("once_per_battle", False), key=f"ab_once_{a_idx}_{v_key}")
                        
                    fasi_sel = r3.multiselect("Fasi di Attivazione", fasi_gioco, default=ab.get("fasi", ["Qualsiasi Fase"]), key=f"ab_fasi_{a_idx}_{v_key}")
                    descrizione = st.text_area("Descrizione dell'Effetto", value=ab.get("descrizione", ""), key=f"ab_desc_{a_idx}_{v_key}")

                    # Multi-Modificatori Meccanici per Abilità
                    mod_ab_esistenti = ab.get("modificatori", {})
                    default_mod_ab = [KEY_TO_LABEL_AB[k] for k in mod_ab_esistenti.keys() if k in KEY_TO_LABEL_AB]

                    scelte_mod_ab = st.multiselect(
                        "Modificatori Meccanici dell'Abilità (opzionale):",
                        list(LABEL_TO_KEY_AB.keys()),
                        default=default_mod_ab,
                        key=f"ms_mod_ab_{a_idx}_{v_key}"
                    )

                    mod_salvati_ab = {}
                    if scelte_mod_ab:
                        st.markdown("**Valori Modificatori Abilità:**")
                        for mod_lbl in scelte_mod_ab:
                            k_ab = LABEL_TO_KEY_AB[mod_lbl]
                            val_prec = mod_ab_esistenti.get(k_ab, 1 if k_ab != "ward_nativo" else 5)
                            
                            if k_ab == "crit_on":
                                st.caption("• **Critico al 5+**: Attivo con questa abilità")
                                mod_salvati_ab["crit_on"] = 5
                            elif k_ab == "ward_nativo":
                                w_val = st.selectbox("Valore Ward:", [4, 5, 6], index=[4, 5, 6].index(val_prec) if val_prec in [4, 5, 6] else 1, key=f"inp_ab_wd_{a_idx}_{v_key}")
                                mod_salvati_ab["ward_nativo"] = w_val
                            else:
                                c_val = st.number_input(f"Valore per {mod_lbl}:", min_value=-5, max_value=15, value=int(val_prec), key=f"inp_ab_{k_ab}_{a_idx}_{v_key}")
                                mod_salvati_ab[k_ab] = c_val

                    abilita_aggiornate.append({
                        "nome": nome_ab,
                        "tipo": tipo,
                        "reazione": reazione,
                        "once_per_battle": once_per_battle,
                        "valore_lancio": val_lancio,
                        "fasi": fasi_sel,
                        "descrizione": descrizione,
                        "modificatori": mod_salvati_ab
                    })
            st.session_state["forgia_abilita"] = abilita_aggiornate

            st.markdown("---")
            kw_testo = st.text_input(
                "Keywords (separate da virgola)", 
                placeholder="es. Hero, Infantry, Wizard (1), Nighthaunt", 
                value=st.session_state.get("forgia_keywords", ""), 
                key=f"f_kw_{v_key}"
            )
            st.session_state["forgia_keywords"] = kw_testo            
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

    # ==========================================
    # TAB: FORMAZIONI DI BATTAGLIA (MULTI-MODIFICATORE)
    # ==========================================
    with tab_formazioni:
        st.markdown('<div class="subsection-title">Archivio Formazioni di Battaglia</div>', unsafe_allow_html=True)
        st.caption("Configura le Formazioni ufficiali per fazione associando regole, tempistiche e modificatori numerici attivi.")
        
        formazioni_db = _carica_json_ausiliario(FORMATIONS_FILE, {})
        
        fazioni_disponibili = ["Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Grande Alleanza / Altro"]
        fazione_f = st.selectbox("Seleziona Fazione:", fazioni_disponibili, key="fg_form_faz")
        
        if fazione_f not in formazioni_db:
            formazioni_db[fazione_f] = {}
            
        form_attuali = formazioni_db.get(fazione_f, {})
        opzioni_form = ["--- Nuova Formazione ---"] + list(form_attuali.keys())
        scelta_form = st.selectbox("Formazione da modificare:", opzioni_form, key="fg_form_sel")
        
        dati_f_sel = form_attuali.get(scelta_form, {}) if scelta_form != "--- Nuova Formazione ---" else {}
        
        nome_form = st.text_input("Nome Formazione:", value="" if scelta_form == "--- Nuova Formazione ---" else scelta_form, key=f"fg_fnome_{scelta_form}")
        
        c_f1, c_f2 = st.columns([1.5, 1])
        fasi_disponibili = [
            "Passiva / Permanente", "Deployment", "Hero Phase (Fase Eroi Amica o Nemica)",
            "Movement Phase (Fase di Movimento)", "Shooting Phase (Fase di Tiro)", 
            "Charge Phase (Fase di Carica)", "Combat Phase (Fase di Combattimento)", "Fine Turno"
        ]
        fase_corrente = dati_f_sel.get("fase_attivazione", "Passiva / Permanente")
        idx_fase = fasi_disponibili.index(fase_corrente) if fase_corrente in fasi_disponibili else 0
        fase_f = c_f1.selectbox("Fase di Attivazione:", fasi_disponibili, index=idx_fase, key=f"fg_ffase_{scelta_form}")
        
        monouso = c_f2.checkbox("Monouso (Once per Battle)", value=bool(dati_f_sel.get("monouso", False)), key=f"fg_fmono_{scelta_form}")
        
        desc_form = st.text_area("Descrizione Regola Ufficiale:", value=dati_f_sel.get("descrizione", ""), height=70, key=f"fg_fdesc_{scelta_form}")

        # Mappatura etichette <-> chiavi tecniche per formazioni
        LABEL_TO_KEY_FORM = {
            "Rend Extra (+Rend)": "bonus_rend",
            "Attacchi Extra (+Atk)": "bonus_atk",
            "Danno Extra (+Dmg)": "bonus_dmg",
            "Hit Bonus (+Hit)": "mod_hit",
            "Wound Bonus (+Wound)": "mod_wnd",
            "Save Migliorato (+Save)": "bonus_save",
            "Ward Fisso (es. 5+)": "ward_nativo",
            "Movimento Extra (+Move pollici)": "bonus_movimento",
            "Controllo Extra (+OC)": "bonus_controllo",
            "Critico al 5+": "crit_on"
        }
        KEY_TO_LABEL_FORM = {v: k for k, v in LABEL_TO_KEY_FORM.items()}

        mod_esistenti_f = dati_f_sel.get("modificatori", {})
        default_mod_labels_f = [KEY_TO_LABEL_FORM[k] for k in mod_esistenti_f.keys() if k in KEY_TO_LABEL_FORM]

        scelte_mod_f = st.multiselect(
            "Modificatori Attivi della Formazione:", 
            list(LABEL_TO_KEY_FORM.keys()), 
            default=default_mod_labels_f, 
            key=f"ms_mod_form_{fazione_f}_{scelta_form}"
        )

        modificatori_salvati_f = {}
        if scelte_mod_f:
            st.markdown("**Valori Modificatori:**")
            for mod_lbl in scelte_mod_f:
                chiave_k = LABEL_TO_KEY_FORM[mod_lbl]
                val_precedente = mod_esistenti_f.get(chiave_k, 1 if chiave_k != "ward_nativo" else 5)
                
                if chiave_k == "crit_on":
                    st.caption("• **Critico al 5+**: Attivo per le unità della formazione")
                    modificatori_salvati_f["crit_on"] = 5
                elif chiave_k == "ward_nativo":
                    w_val = st.selectbox("Valore Ward:", [4, 5, 6], index=[4, 5, 6].index(val_precedente) if val_precedente in [4, 5, 6] else 1, key=f"inp_f_wd_{scelta_form}_{chiave_k}")
                    modificatori_salvati_f["ward_nativo"] = w_val
                else:
                    c_val = st.number_input(f"Valore {mod_lbl}:", min_value=-5, max_value=15, value=int(val_precedente), key=f"inp_f_{scelta_form}_{chiave_k}")
                    modificatori_salvati_f[chiave_k] = c_val

        col_s_f1, col_s_f2 = st.columns([2, 1])
        if col_s_f1.button("💾 Salva Formazione", type="primary", use_container_width=True):
            if nome_form.strip() and nome_form != "--- Nuova Formazione ---":
                if fazione_f not in formazioni_db:
                    formazioni_db[fazione_f] = {}
                formazioni_db[fazione_f][nome_form.strip()] = {
                    "fase_attivazione": fase_f,
                    "monouso": monouso,
                    "modificatori": modificatori_salvati_f,
                    "descrizione": desc_form.strip()
                }
                _salva_json_ausiliario(FORMATIONS_FILE, formazioni_db)
                st.session_state["archivio_formazioni"] = formazioni_db
                st.toast(f"Formazione '{nome_form}' registrata con successo!")
                st.rerun()

        if scelta_form != "--- Nuova Formazione ---" and col_s_f2.button("🗑️ Elimina Formazione", use_container_width=True):
            del formazioni_db[fazione_f][scelta_form]
            _salva_json_ausiliario(FORMATIONS_FILE, formazioni_db)
            st.session_state["archivio_formazioni"] = formazioni_db
            st.toast(f"Formazione '{scelta_form}' rimossa!")
            st.rerun()

    # ==========================================
    # TAB: TRATTI EROICI & ARTEFATTI (CORRETTO)
    # ==========================================
    with tab_tratti_artefatti:
        st.markdown('<div class="subsection-title">Tratti Eroici ed Artefatti di Potere</div>', unsafe_allow_html=True)
        st.caption("Configura tratti e artefatti associando molteplici modificatori attivi (Save, Hit, Wound, Atk, Rend, Dmg, Ward, ecc.).")

        # Caricamento e migrazione automatica
        raw_traits = _carica_json_ausiliario(TRAITS_FILE, {})
        traits_db = raw_traits if isinstance(raw_traits, dict) and "Generali" not in raw_traits else {
            k: {"fazione": "Generale", "descrizione": k, "modificatori": {}} 
            for k in (raw_traits.get("Generali", ["Nessuno"]) if isinstance(raw_traits, dict) else ["Nessuno"])
        }

        raw_artefacts = _carica_json_ausiliario(ARTEFACTS_FILE, {})
        artefacts_db = raw_artefacts if isinstance(raw_artefacts, dict) and "Generali" not in raw_artefacts else {
            k: {"fazione": "Generale", "descrizione": k, "modificatori": {}} 
            for k in (raw_artefacts.get("Generali", ["Nessuno"]) if isinstance(raw_artefacts, dict) else ["Nessuno"])
        }

        if "Nessuno" not in traits_db:
            traits_db["Nessuno"] = {"fazione": "Generale", "descrizione": "Nessun tratto assegnato.", "modificatori": {}}
        if "Nessuno" not in artefacts_db:
            artefacts_db["Nessuno"] = {"fazione": "Generale", "descrizione": "Nessun artefatto equipaggiato.", "modificatori": {}}

        opzioni_fazione_supporto = ["Generale", "Nighthaunt", "Blades of Khorne", "Orruk Kruleboyz", "Sylvaneth", "Altro"]

        LABEL_TO_KEY = {
            "Save Migliorato (+Save)": "bonus_save",
            "Hit Bonus (+Hit)": "mod_hit",
            "Wound Bonus (+Wound)": "mod_wnd",
            "Attacchi Extra (+Atk)": "bonus_atk",
            "Rend Extra (+Rend)": "bonus_rend",
            "Danno Extra (+Dmg)": "bonus_dmg",
            "Ward Fisso (es. 5+)": "ward_nativo",
            "Movimento Extra (+Move pollici)": "bonus_movimento",
            "Salute Extra (+PF)": "bonus_salute",
            "Controllo Extra (+OC)": "bonus_controllo",
            "Critico al 5+": "crit_on",
            "Malus Hit Subito (-Hit nemico)": "mod_hit_subito"
        }
        KEY_TO_LABEL = {v: k for k, v in LABEL_TO_KEY.items()}

        col_t, col_a = st.columns(2)

        # ------------------------------------------
        # SEZIONE TRATTI EROICI
        # ------------------------------------------
        with col_t:
            st.markdown("#### 📜 Gestione Tratti Eroici")
            lista_nomi_t = ordina_supporti_per_fazione_e_nome(traits_db)
            # Mostra nel menu a tendina: "[Nighthaunt] Ombra Inafferrabile" o "[Generale] Furia Implacabile"
            sel_t = st.selectbox(
                "Seleziona Tratto:", 
                ["--- Nuovo Tratto ---"] + lista_nomi_t, 
                format_func=lambda x: f"[{traits_db[x].get('fazione', 'Generale')}] {x}" if x in traits_db and x != "Nessuno" else x,
                key="sel_tratto_gest"
            )
            dati_t = traits_db.get(sel_t, {"fazione": "Generale", "descrizione": "", "modificatori": {}})

            nome_t = st.text_input("Nome Tratto:", value="" if sel_t == "--- Nuovo Tratto ---" else sel_t, key=f"in_nome_t_{sel_t}")
            idx_faz_t = opzioni_fazione_supporto.index(dati_t.get("fazione", "Generale")) if dati_t.get("fazione", "Generale") in opzioni_fazione_supporto else 0
            faz_t = st.selectbox("Fazione:", opzioni_fazione_supporto, index=idx_faz_t, key=f"in_faz_t_{sel_t}")
            desc_t = st.text_area("Descrizione Regola:", value=dati_t.get("descrizione", ""), height=70, key=f"in_desc_t_{sel_t}")

            mod_esistenti_t = dati_t.get("modificatori", {})
            default_mod_labels_t = [KEY_TO_LABEL[k] for k in mod_esistenti_t.keys() if k in KEY_TO_LABEL]

            scelte_mod_t = st.multiselect(
                "Modificatori Attivi:", 
                list(LABEL_TO_KEY.keys()), 
                default=default_mod_labels_t, 
                key=f"ms_mod_t_{sel_t}"
            )

            modificatori_salvati_t = {}
            if scelte_mod_t:
                st.markdown("**Valori Modificatori:**")
                for mod_lbl in scelte_mod_t:
                    chiave_k = LABEL_TO_KEY[mod_lbl]
                    val_precedente = mod_esistenti_t.get(chiave_k, 1 if chiave_k != "ward_nativo" else 5)
                    
                    if chiave_k == "crit_on":
                        st.caption("• **Critico al 5+**: Attivo")
                        modificatori_salvati_t["crit_on"] = 5
                    elif chiave_k == "ward_nativo":
                        w_val = st.selectbox("Valore Ward:", [4, 5, 6], index=[4, 5, 6].index(val_precedente) if val_precedente in [4, 5, 6] else 1, key=f"inp_t_wd_{sel_t}_{chiave_k}")
                        modificatori_salvati_t["ward_nativo"] = w_val
                    else:
                        c_val = st.number_input(f"Valore {mod_lbl}:", min_value=-5, max_value=15, value=int(val_precedente), key=f"inp_t_{sel_t}_{chiave_k}")
                        modificatori_salvati_t[chiave_k] = c_val

            bt1, bt2 = st.columns(2)
            if bt1.button("💾 Salva Tratto", type="primary", use_container_width=True):
                if nome_t.strip() and nome_t != "--- Nuovo Tratto ---":
                    traits_db[nome_t.strip()] = {
                        "fazione": faz_t,
                        "descrizione": desc_t.strip(),
                        "modificatori": modificatori_salvati_t
                    }
                    _salva_json_ausiliario(TRAITS_FILE, traits_db)
                    st.toast(f"Tratto '{nome_t}' salvato!")
                    st.rerun()

            if sel_t not in ["--- Nuovo Tratto ---", "Nessuno"] and bt2.button("🗑️ Elimina Tratto", use_container_width=True):
                del traits_db[sel_t]
                _salva_json_ausiliario(TRAITS_FILE, traits_db)
                st.toast(f"Tratto '{sel_t}' eliminato!")
                st.rerun()

        # ------------------------------------------
        # SEZIONE ARTEFATTI DI POTERE
        # ------------------------------------------
        with col_a:
            st.markdown("#### 🏺 Gestione Artefatti di Potere")
            lista_nomi_a = ordina_supporti_per_fazione_e_nome(artefacts_db)
            sel_a = st.selectbox(
                "Seleziona Artefatto:", 
                ["--- Nuovo Artefatto ---"] + lista_nomi_a, 
                format_func=lambda x: f"[{artefacts_db[x].get('fazione', 'Generale')}] {x}" if x in artefacts_db and x != "Nessuno" else x,
                key="sel_art_gest"
            )
            dati_a = artefacts_db.get(sel_a, {"fazione": "Generale", "descrizione": "", "modificatori": {}})

            nome_a = st.text_input("Nome Artefatto:", value="" if sel_a == "--- Nuovo Artefatto ---" else sel_a, key=f"in_nome_a_{sel_a}")
            idx_faz_a = opzioni_fazione_supporto.index(dati_a.get("fazione", "Generale")) if dati_a.get("fazione", "Generale") in opzioni_fazione_supporto else 0
            faz_a = st.selectbox("Fazione:", opzioni_fazione_supporto, index=idx_faz_a, key=f"in_faz_a_{sel_a}")
            desc_a = st.text_area("Descrizione Regola:", value=dati_a.get("descrizione", ""), height=70, key=f"in_desc_a_{sel_a}")

            mod_esistenti_a = dati_a.get("modificatori", {})
            default_mod_labels_a = [KEY_TO_LABEL[k] for k in mod_esistenti_a.keys() if k in KEY_TO_LABEL]

            scelte_mod_a = st.multiselect(
                "Modificatori Attivi:", 
                list(LABEL_TO_KEY.keys()), 
                default=default_mod_labels_a, 
                key=f"ms_mod_a_{sel_a}"
            )

            modificatori_salvati_a = {}
            if scelte_mod_a:
                st.markdown("**Valori Modificatori:**")
                for mod_lbl in scelte_mod_a:
                    chiave_k = LABEL_TO_KEY[mod_lbl]
                    val_precedente = mod_esistenti_a.get(chiave_k, 1 if chiave_k != "ward_nativo" else 5)
                    
                    if chiave_k == "crit_on":
                        st.caption("• **Critico al 5+**: Attivo")
                        modificatori_salvati_a["crit_on"] = 5
                    elif chiave_k == "ward_nativo":
                        w_val = st.selectbox("Valore Ward:", [4, 5, 6], index=[4, 5, 6].index(val_precedente) if val_precedente in [4, 5, 6] else 1, key=f"inp_a_wd_{sel_a}_{chiave_k}")
                        modificatori_salvati_a["ward_nativo"] = w_val
                    else:
                        c_val = st.number_input(f"Valore {mod_lbl}:", min_value=-5, max_value=15, value=int(val_precedente), key=f"inp_a_{sel_a}_{chiave_k}")
                        modificatori_salvati_a[chiave_k] = c_val

            ba1, ba2 = st.columns(2)
            if ba1.button("💾 Salva Artefatto", type="primary", use_container_width=True):
                if nome_a.strip() and nome_a != "--- Nuovo Artefatto ---":
                    artefacts_db[nome_a.strip()] = {
                        "fazione": faz_a,
                        "descrizione": desc_a.strip(),
                        "modificatori": modificatori_salvati_a
                    }
                    _salva_json_ausiliario(ARTEFACTS_FILE, artefacts_db)
                    st.toast(f"Artefatto '{nome_a}' salvato!")
                    st.rerun()

            if sel_a not in ["--- Nuovo Artefatto ---", "Nessuno"] and ba2.button("🗑️ Elimina Artefatto", use_container_width=True):
                del artefacts_db[sel_a]
                _salva_json_ausiliario(ARTEFACTS_FILE, artefacts_db)
                st.toast(f"Artefatto '{sel_a}' eliminato!")
                st.rerun()
                
    # ==========================================
    # TAB: GESTIONE ED ELIMINAZIONE UNITÀ DAL DB
    # ==========================================
    with tab_elimina:
        st.markdown('<div class="subsection-title">Eliminazione Protetta dal Database</div>', unsafe_allow_html=True)
        st.caption("Rimuovi in sicurezza profili obsoleti o non più necessari.")
        
        tutte_le_unita = [u for u in st.session_state["db_unita"].keys() if u != "--- Seleziona o Resetta ---"]
        if tutte_le_unita:
            unita_target = st.selectbox("Seleziona Unità da eliminare:", tutte_le_unita, key="del_u_tab")
            st.warning(f"Attenzione: l'eliminazione di **{unita_target}** sarà permanente nel file JSON del database.")
            
            conferma = st.checkbox("Confermo la rimozione definitiva dell'unità", key="chk_conf_del")
            if st.button("🗑️ Elimina Definitivamente", type="secondary", disabled=not conferma):
                del st.session_state["db_unita"][unita_target]
                salva_nel_database(st.session_state["db_unita"])
                st.success(f"Unità '{unita_target}' eliminata con successo dal Grimorio!")
                st.session_state["forgia_version"] += 1
                st.rerun()
        else:
            st.info("Nessuna unità presente nel database da eliminare.")