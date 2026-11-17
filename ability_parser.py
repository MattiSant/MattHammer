import re

FASI_GIOCO_COMPLETO = [
    "Qualsiasi Fase",
    "Deployment",
    "Inizio del Turno (Start of Turn)",
    "Hero Phase (Amica)",
    "Hero Phase (Nemica)",
    "Hero Phase (Qualsiasi)",
    "Movement Phase (Amica)",
    "Movement Phase (Nemica)",
    "Movement Phase (Qualsiasi)",
    "Shooting Phase (Amica)",
    "Shooting Phase (Nemica)",
    "Shooting Phase (Qualsiasi)",
    "Charge Phase (Amica)",
    "Charge Phase (Nemica)",
    "Charge Phase (Qualsiasi)",
    "Combat Phase (Amica)",
    "Combat Phase (Nemica)",
    "Combat Phase (Qualsiasi)",
    "Fine Turno (End of Turn)"
]

word_to_num = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "un": 1, "uno": 1, "una": 1, "due": 2, "tre": 3, "quattro": 4, "cinque": 5, "sei": 6
}

def _converti_numero(val_str, default=1):
    if not val_str:
        return default
    v = val_str.strip().lower()
    if v.isdigit():
        return int(v)
    return word_to_num.get(v, default)

def estrai_fasi_da_header(testo_header):
    """
    Riconosce automaticamente la fase di AoS 4e distinguendo tra Your (Amica),
    Enemy/Opponent (Nemica) e Any (Qualsiasi), oltre a Deployment, Start/End of Turn e Reaction.
    """
    h = testo_header.lower()
    fasi = []
    
    is_amica = any(k in h for k in ["your ", "amica", "propria", "tuo ", "tua "])
    is_nemica = any(k in h for k in ["enemy ", "opponent", "nemica", "avversaria", "avversario"])

    def _aggiungi_fase(nome_base):
        if is_amica and not is_nemica:
            fasi.append(f"{nome_base} (Amica)")
        elif is_nemica and not is_amica:
            fasi.append(f"{nome_base} (Nemica)")
        else:
            fasi.append(f"{nome_base} (Qualsiasi)")

    if "deployment" in h or "schieramento" in h:
        fasi.append("Deployment")
    if "start of" in h or "inizio" in h:
        fasi.append("Inizio del Turno (Start of Turn)")
    if "hero phase" in h or "fase degli eroi" in h or "fase eroi" in h:
        _aggiungi_fase("Hero Phase")
    if "movement phase" in h or "fase di movimento" in h or "movimento" in h:
        _aggiungi_fase("Movement Phase")
    if "shooting phase" in h or "fase di tiro" in h:
        _aggiungi_fase("Shooting Phase")
    if "charge phase" in h or "fase di carica" in h:
        _aggiungi_fase("Charge Phase")
    if "combat phase" in h or "fase di combattimento" in h:
        _aggiungi_fase("Combat Phase")
    if "end of" in h or "fine turno" in h or "fine della fase" in h:
        fasi.append("Fine Turno (End of Turn)")

    if not fasi:
        fasi.append("Qualsiasi Fase")
    return list(dict.fromkeys(fasi))


def estrai_effetti_da_testo(testo_completo):
    """
    Analizza qualsiasi descrizione di abilità (nuova o già salvata nel DB)
    ed estrae modificatori statistici, danni mortali e condizioni di attivazione.
    """
    eff_match = re.search(r'(?:effect|effetto)\s*:(.*)', testo_completo, flags=re.IGNORECASE | re.DOTALL)
    testo_effetto = eff_match.group(1).lower() if eff_match else testo_completo.lower()
    full_low = testo_completo.lower()

    modificatori = {}
    condizioni = {
        "richiede_carica": False,
        "richiede_5_modelli": False,
        "solo_melee": False,
        "solo_ranged": False,
        "mortal_prob": 1.0,
        "mortal_dmg_expr": "0",
        "mortal_extra_dadi": 0,
        "mortal_extra_tipo": 6,
        "mortal_extra_soglia": "Nessuna (Somma)",
        "mortal_extra_fisso": 0.0
    }

    # 1. Rilevamento Condizioni di Innesco
    if any(k in full_low for k in [
        "if this unit charged", "charged this turn", "charged in the same turn",
        "made a charge move", "ha caricato", "se carica", "dopo una carica"
    ]):
        condizioni["richiede_carica"] = True

    if re.search(r'(\d+)\s+or\s+more\s+models|(\d+)\s+o\s+più\s+modelli', full_low):
        condizioni["richiede_5_modelli"] = True

    if "melee weapons" in testo_effetto or "armi da mischia" in testo_effetto:
        condizioni["solo_melee"] = True
    if "ranged weapons" in testo_effetto or "missile weapons" in testo_effetto or "armi da tiro" in testo_effetto:
        condizioni["solo_ranged"] = True

    # 2. Modificatori alle Statistiche (Supporta cifre e parole: "add 1", "aggiungi 2", ecc.)
    m_atk = re.search(r'(?:add|aggiungi)\s+(\d+|one|two|three)\s+(?:to\s+the\s+|alla\s+caratteristica\s+)?attacks?', testo_effetto)
    if m_atk:
        modificatori["bonus_atk"] = _converti_numero(m_atk.group(1))

    m_hit = re.search(r'(?:add|aggiungi)\s+(\d+|one|two)\s+(?:to\s+|ai\s+)?(?:the\s+)?hit\s+rolls?', testo_effetto)
    if m_hit:
        modificatori["mod_hit"] = _converti_numero(m_hit.group(1))

    m_hit_sub = re.search(r'(?:subtract|sottrai)\s+(\d+|one|two)\s+(?:from\s+|dai\s+)?(?:the\s+)?hit\s+rolls?', testo_effetto)
    if m_hit_sub:
        modificatori["mod_hit_subito"] = -_converti_numero(m_hit_sub.group(1))

    m_wnd = re.search(r'(?:add|aggiungi)\s+(\d+|one|two)\s+(?:to\s+|ai\s+)?(?:the\s+)?wound\s+rolls?', testo_effetto)
    if m_wnd:
        modificatori["mod_wnd"] = _converti_numero(m_wnd.group(1))

    m_wnd_sub = re.search(r'(?:subtract|sottrai)\s+(\d+|one|two)\s+(?:from\s+|dai\s+)?(?:the\s+)?wound\s+rolls?', testo_effetto)
    if m_wnd_sub:
        modificatori["mod_wnd_nerf"] = -_converti_numero(m_wnd_sub.group(1))

    m_rend = re.search(r'(?:add|aggiungi)\s+(\d+|one|two)\s+(?:to\s+the\s+|alla\s+caratteristica\s+)?rend', testo_effetto)
    if m_rend:
        modificatori["bonus_rend"] = _converti_numero(m_rend.group(1))

    m_dmg = re.search(r'(?:add|aggiungi)\s+(\d+|one|two)\s+(?:to\s+the\s+|alla\s+caratteristica\s+)?damage', testo_effetto)
    if m_dmg:
        modificatori["bonus_dmg"] = _converti_numero(m_dmg.group(1))

    m_save = re.search(r'(?:add|aggiungi)\s+(\d+|one|two)\s+(?:to\s+|ai\s+)?(?:the\s+)?save\s+rolls?', testo_effetto)
    if m_save:
        modificatori["bonus_save"] = _converti_numero(m_save.group(1))

    m_move = re.search(r'(?:add|aggiungi)\s+(\d+|one|two|three)\"?\s+(?:to\s+the\s+|alla\s+caratteristica\s+)?move', testo_effetto)
    if m_move:
        modificatori["bonus_movimento"] = _converti_numero(m_move.group(1))

    m_oc = re.search(r'(?:add|aggiungi)\s+(\d+|one|two|three)\s+(?:to\s+the\s+|al\s+)?control', testo_effetto)
    if m_oc:
        modificatori["bonus_controllo"] = _converti_numero(m_oc.group(1))

    m_ward = re.search(r'ward\s*\(?([456])\+\)?', testo_effetto)
    if m_ward:
        modificatori["ward_nativo"] = int(m_ward.group(1))

    if re.search(r'critical\s+hits?\s+on\s+(?:unmodified\s+)?5\+|critico\s+al\s+5\+', testo_effetto):
        modificatori["crit_on"] = 5

    # Effetti Critici conferiti da abilità (es. Scriptor Mortis -> Crit (Mortal))
    if "crit (mortal)" in testo_effetto:
        modificatori["crit_override"] = "Crit (Mortal)"
    elif "crit (auto-wound)" in testo_effetto:
        modificatori["crit_override"] = "Crit (Auto-wound)"
    elif "crit (2 hits)" in testo_effetto:
        modificatori["crit_override"] = "Crit (2 Hits)"

    # 3. Danni Mortali (Mortal Damage / Mortal Wounds)
    # Evita falsi positivi quando l'abilità dice solo "Crit (Mortal)"
    testo_senza_crit = testo_effetto.replace("crit (mortal)", "")
    if any(k in testo_senza_crit for k in ["mortal damage", "mortal wound", "danni mortali", "ferite mortali", "mortali"]):
        # Soglia (es. "on a 2+", "al 3+")
        m_soglia = re.search(r'(?:on\s+a|on\s+an|al|con\s+un|for\s+each)\s+([2-6])\+', testo_senza_crit)
        soglia_val = int(m_soglia.group(1)) if m_soglia else 1

        # Caso 1: "Roll a D3. On a 2+, inflict an amount of mortal damage equal to the roll" (Slaughterpriest / simili)
        if re.search(r'roll\s+a\s+d3.*equal\s+to\s+the\s+roll', testo_senza_crit, flags=re.DOTALL):
            # Su un D3, tirando 2 o 3 infliggi 2 o 3 danni -> Media esatta = (0 + 2 + 3)/3 = 1.67 danni
            condizioni["mortal_extra_dadi"] = 1
            condizioni["mortal_extra_tipo"] = 3
            condizioni["mortal_extra_soglia"] = f"{max(2, soglia_val)}+"
            condizioni["mortal_dmg_expr"] = "D3_EQUAL"
            modificatori["mortal_extra_fisso"] = round((2 + 3) / 3.0 if soglia_val == 2 else 1.0, 2)

        # Caso 2: "Roll X dice. For each Y+, inflict 1 mortal damage"
        elif re.search(r'(?:roll|tira)\s+(\d+)\s+(?:dice|d6|dadi)', testo_senza_crit):
            m_nd = re.search(r'(?:roll|tira)\s+(\d+)\s+(?:dice|d6|dadi)', testo_senza_crit)
            n_dadi = int(m_nd.group(1))
            soglia_str = f"{soglia_val}+" if soglia_val >= 2 else "4+"
            condizioni["mortal_extra_dadi"] = n_dadi
            condizioni["mortal_extra_tipo"] = 6
            condizioni["mortal_extra_soglia"] = soglia_str
            modificatori["mortal_extra_dadi"] = n_dadi
            modificatori["mortal_extra_tipo"] = 6
            modificatori["mortal_extra_soglia"] = soglia_str

        # Caso 3: "Roll a dice / Roll a D3. On a 2+, inflict D3 / D6 / N mortal damage" (es. Black Coach)
        else:
            # Determina su che dado si fa il test di attivazione (default D6, o D3 se specificato prima della soglia)
            testo_prima_soglia = testo_senza_crit[:m_soglia.start()] if m_soglia else testo_senza_crit
            dado_test = 3 if ("roll a d3" in testo_prima_soglia or "tira un d3" in testo_prima_soglia) else 6
            prob_attivazione = 1.0 if soglia_val <= 1 else max(0.0, (dado_test - soglia_val + 1) / float(dado_test))

            # Quanto danno infligge se ha successo? (es. "inflict D3 mortal", "inflict 2D6 mortal", "inflict 3 mortal")
            m_dmg_expr = re.search(r'(?:inflict|infliggi)\s+(\d*d[36](?:\+\d+)?|\d+)\s+(?:mortal|danni\s+mortali|ferite\s+mortali)', testo_senza_crit)
            expr_danno = m_dmg_expr.group(1).upper() if m_dmg_expr else "D3"

            condizioni["mortal_prob"] = prob_attivazione
            condizioni["mortal_dmg_expr"] = expr_danno

            # Calcolo media analitica esatta per i riassunti rapidi
            if expr_danno.isdigit():
                media_dmg = float(expr_danno)
            elif "D3" in expr_danno:
                molt_d = int(expr_danno.split("D")[0]) if expr_danno.split("D")[0].isdigit() else 1
                media_dmg = molt_d * 2.0
            elif "D6" in expr_danno:
                molt_d = int(expr_danno.split("D")[0]) if expr_danno.split("D")[0].isdigit() else 1
                media_dmg = molt_d * 3.5
            else:
                media_dmg = 2.0

            danno_medio_atteso_mortali = round(prob_attivazione * media_dmg, 2)
            condizioni["mortal_extra_fisso"] = danno_medio_atteso_mortali
            modificatori["mortal_extra_fisso"] = danno_medio_atteso_mortali

    return modificatori, condizioni


def analizza_abilita_warscroll(testo_grezzo):
    """
    Analizza il testo copiato da una Warscroll AoS 4e (es. con intestazione, Declare, Effect)
    e restituisce un dizionario strutturato pronto per la Forgia e il Motore Matematico.
    """
    testo_pulito = testo_grezzo.strip()
    if not testo_pulito:
        return None

    linee = [l.strip() for l in testo_pulito.split("\n") if l.strip()]
    
    prima_riga = linee[0]
    header_lower = prima_riga.lower()
    testo_completo_lower = testo_pulito.lower()

    once_per_battle = ("once per battle" in header_lower) or ("una volta per battaglia" in header_lower)
    reazione = ("reaction:" in testo_completo_lower) or ("reazione:" in testo_completo_lower)
    
    tipo = "Ability"
    if "passive" in header_lower or "passiva" in header_lower:
        tipo = "Passive"
    elif "spell" in header_lower or "incantesimo" in header_lower or "casting value" in testo_completo_lower:
        tipo = "Spell"
    elif "prayer" in header_lower or "preghiera" in header_lower or "chanting value" in testo_completo_lower:
        tipo = "Prayer"

    valore_lancio = 0
    match_cast = re.search(r'(?:casting|chanting)\s+value\s+(\d+)', testo_completo_lower)
    if match_cast:
        valore_lancio = int(match_cast.group(1))

    fasi = estrai_fasi_da_header(prima_riga if not reazione else testo_pulito[:180])

    nome_abilita = "Abilità Importata"
    if len(linee) > 1:
        seconda_riga = linee[1]
        if ":" in seconda_riga and not seconda_riga.lower().startswith(("declare:", "effect:", "reaction:")):
            parti = seconda_riga.split(":", 1)
            nome_abilita = parti[0].strip().title()
            resto = parti[1].strip()
            desc_linee = ([resto] if resto else []) + linee[2:]
            descrizione = "\n".join(desc_linee).strip()
        else:
            nome_abilita = seconda_riga.strip().title()
            descrizione = "\n".join(linee[2:]).strip()
    else:
        descrizione = prima_riga

    if not descrizione:
        descrizione = testo_pulito

    modificatori, condizioni = estrai_effetti_da_testo(descrizione)

    return {
        "nome": nome_abilita,
        "tipo": tipo,
        "reazione": reazione,
        "once_per_battle": once_per_battle,
        "valore_lancio": valore_lancio,
        "fasi": fasi,
        "descrizione": descrizione,
        "modificatori": modificatori,
        "condizioni": condizioni
    }


def applica_abilita_attive_a_mod_globali(abilita_lista, mod_globali_base, bersaglio=None, attive_flags=None):
    """
    Applica i modificatori e i danni mortali extra delle abilità di warscroll
    al dizionario mod_globali (usato da calcola_arma_analitico e simula_monte_carlo),
    rispettando 'ha_caricato', le dimensioni del bersaglio e le spunte utente.
    Funziona anche sulle abilità già salvate in units_db.json grazie al fallback automatico sul testo!
    """
    mod = dict(mod_globali_base)
    ha_caricato = bool(mod.get("ha_caricato", False))
    n_mod_bersaglio = int(bersaglio.get("n_modelli", max(1, bersaglio.get("salute", 10) // 2))) if bersaglio else 10

    for idx, ab in enumerate(abilita_lista or []):
        if attive_flags is not None and not attive_flags.get(idx, True):
            continue

        # Se l'abilità proviene da un vecchio salvataggio senza 'condizioni', le estrae al volo dalla descrizione
        mods_salvati = ab.get("modificatori", {})
        cond_salvate = ab.get("condizioni", {})
        mods_auto, cond_auto = estrai_effetti_da_testo(ab.get("descrizione", ""))

        cond = {**cond_auto, **cond_salvate}
        mods = {**mods_auto, **mods_salvati}

        # 1. Verifica condizione CARICA (es. Black Coach, Bladegheist Revenants)
        if cond.get("richiede_carica", False) and not ha_caricato:
            continue

        # 2. Verifica condizione ORDA (es. Grimghast Reapers: 5+ modelli nel bersaglio)
        if cond.get("richiede_5_modelli", False) and n_mod_bersaglio < 5:
            continue

        # 3. Applica bonus alle caratteristiche
        mod["bonus_atk"] = mod.get("bonus_atk", 0) + int(mods.get("bonus_atk", 0))
        mod["mod_hit"] = mod.get("mod_hit", 0) + int(mods.get("mod_hit", 0))
        mod["mod_wnd"] = mod.get("mod_wnd", 0) + int(mods.get("mod_wnd", 0))
        mod["bonus_rend"] = mod.get("bonus_rend", 0) + int(mods.get("bonus_rend", 0))
        mod["bonus_dmg"] = mod.get("bonus_dmg", 0) + int(mods.get("bonus_dmg", 0))
        if mods.get("crit_on") == 5:
            mod["crit_on"] = 5
        if "crit_override" in mods:
            mod["crit_override"] = mods["crit_override"]

        # 4. Applica Danni Mortali Extra (sia basati su N dadi a soglia, sia basati su espressione/probabilità)
        m_dadi = int(mods.get("mortal_extra_dadi", cond.get("mortal_extra_dadi", 0)))
        m_fisso = float(mods.get("mortal_extra_fisso", cond.get("mortal_extra_fisso", 0.0)))

        if m_dadi > 0:
            mod["mortal_extra_dadi"] = mod.get("mortal_extra_dadi", 0) + m_dadi
            mod["mortal_extra_tipo"] = int(mods.get("mortal_extra_tipo", cond.get("mortal_extra_tipo", 6)))
            if str(mod.get("mortal_extra_soglia", "Nessuna (Somma)")).startswith("Nessuna"):
                mod["mortal_extra_soglia"] = mods.get("mortal_extra_soglia", cond.get("mortal_extra_soglia", "Nessuna (Somma)"))
        elif m_fisso > 0:
            mod["mortal_extra_fisso"] = mod.get("mortal_extra_fisso", 0.0) + m_fisso

    return mod