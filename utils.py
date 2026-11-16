import re

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