from __future__ import annotations
import re
from collections import defaultdict


def _clean_footnotes(expr: str) -> str:
    # Remove letter footnote markers attached to codes, but preserve balance markers (D)/(C).
    return re.sub(r"(?<=\d)\(([a-i])\)", "", expr, flags=re.I)


def _split_accounts(expr: str) -> list[str]:
    # Split comma / slash / "et", preserving exclusion clauses.
    expr = expr.strip()
    if not expr:
        return []
    out, buf, square, paren = [], [], 0, 0
    i = 0
    while i < len(expr):
        ch = expr[i]
        if ch == "[":
            square += 1
        elif ch == "]":
            square = max(square - 1, 0)
        elif ch == "(":
            paren += 1
        elif ch == ")":
            paren = max(paren - 1, 0)
        if square == 0 and paren == 0 and ch in ",/":
            token = "".join(buf).strip()
            if token:
                out.append(token)
            buf = []
        else:
            buf.append(ch)
        i += 1
    token = "".join(buf).strip()
    if token:
        out.append(token)
    # Do not split on "et" here: it is frequently part of an exclusion clause
    # such as "50 [sauf 502 et 509]". The exclusion parser handles "et"
    # inside the bracket explicitly.
    return out


def parse_pcg_expression(expr: str, parenthetical_side: str | None = None) -> dict:
    raw = expr
    expr = _clean_footnotes(expr)
    selectors = []
    for token in _split_accounts(expr):
        excludes = []
        m_ex = re.search(r"\[\s*sauf\s+(.+?)\s*\]", token, flags=re.I)
        if m_ex:
            excludes = [re.sub(r"\D", "", x) for x in re.split(r"\s+et\s+|,", m_ex.group(1)) if re.sub(r"\D","",x)]
            token = token[:m_ex.start()].strip()

        outer_parenthetical = token.startswith("(") and token.endswith(")")
        if outer_parenthetical:
            token = token[1:-1].strip()

        side = parenthetical_side if outer_parenthetical else None
        m_side = re.search(r"\(([DC])\)\s*$", token, flags=re.I)
        if m_side:
            side = "debit" if m_side.group(1).upper() == "D" else "credit"
            token = token[:m_side.start()].strip()

        digits = re.sub(r"\D", "", token)
        if not digits:
            selectors.append({"match_type":"unparsed","raw":token,"side":side,"exclude_prefixes":excludes})
            continue
        selectors.append({
            "match_type": "prefix",
            "account_prefix": digits,
            "side": side,
            "exclude_prefixes": excludes,
        })
    return {
        "raw_expression": raw,
        "selectors": selectors,
        "parse_status": "parsed" if selectors and all(s["match_type"]=="prefix" for s in selectors) else ("empty" if not selectors else "partial"),
    }


def _component(role, expr, page, parenthetical_side=None, operation="add"):
    return {
        "component_role": role,
        "operation": operation,
        "mapping": parse_pcg_expression(expr, parenthetical_side=parenthetical_side),
        "source": {"document_id":"fr-pcg-recueil-2026-md","page_pdf":page,"section":"IR4 - tableau de passage"},
    }


BASE_BALANCE_ROWS = [
    # label, section, page, gross/normal, contra
    ("Capital souscrit non appelé","asset",440,"109",""),
    ("Frais d'établissement","asset",440,"201","2801, 2901"),
    ("Frais de développement","asset",440,"203","2803, 2903"),
    ("Concessions, brevets, licences, marques, procédés, solutions informatiques, droits et valeurs similaires","asset",440,"205","2805, 2905"),
    ("Fonds commercial","asset",440,"207","2807, 2907"),
    ("Autres immobilisations incorporelles","asset",440,"206, 208","2806, 2808, 2906, 2908"),
    ("Immobilisations incorporelles en cours, avances et acomptes","asset",440,"232, 237","2932"),
    ("Terrains","asset",440,"211, 212","2911, 2812, 2912"),
    ("Constructions","asset",440,"213, 214","2813, 2814, 2913, 2914"),
    ("Installations techniques, matériel et outillage industriels","asset",440,"215","2815, 2915"),
    ("Autres immobilisations corporelles","asset",440,"218","2818, 2918"),
    ("Immobilisations corporelles en cours, avances et acomptes","asset",440,"231, 238","2931"),
    ("Participations","asset",440,"261, 262, 266","2961, 2962, 2966"),
    ("Créances rattachées à des participations","asset",440,"267, 268","2967, 2968"),
    ("Titres immobilisés de l’activité de portefeuille","asset",440,"273","2973"),
    ("Autres titres immobilisés","asset",440,"271, 272, 27682, 277","2971, 2972, 2974"),
    ("Prêts","asset",440,"274, 27684","2975, 2976"),
    ("Autres immobilisations financières","asset",440,"275, 2761, 27685, 27688",""),
    ("Matières premières et autres approvisionnements","asset",441,"31, 32","391, 392"),
    ("En-cours de production","asset",441,"33, 34","393, 394"),
    ("Produits finis","asset",441,"35","395"),
    ("Marchandises","asset",441,"37","397"),
    ("Avances et acomptes versés sur commandes","asset",441,"4091",""),
    ("Créances Clients et comptes rattachés","asset",441,"411, 413, 416, 418","491"),
    ("Autres créances","asset",441,"4096, 4097, 4098, 425, 439, 44(D), 45(D) [sauf 4562], 462, 465, 467","495, 496"),
    ("Charges constatées d’avance","asset",441,"486",""),
    ("Capital souscrit appelé, non versé","asset",441,"4562",""),
    ("Actions propres","asset",441,"","590"),
    ("Autres titres","asset",441,"502, 50 [sauf 502 et 509]","590"),
    ("Instruments financiers à terme et jetons détenus","asset",441,"52(D)",""),
    ("Disponibilités","asset",441,"51(D), 53",""),
    ("Frais d’émission des emprunts","asset",441,"481",""),
    ("Primes de remboursement des emprunts","asset",441,"169",""),
    ("Écarts de conversion et différences d’évaluation - Actif","asset",441,"474, 476",""),
    ("Capital","liability",442,"101, 108",""),
    ("Primes d'émission, de fusion, d'apport","liability",442,"104",""),
    ("Écarts de réévaluation","liability",442,"105",""),
    ("Écart d’équivalence","liability",442,"107",""),
    ("Réserve légale","liability",442,"1061",""),
    ("Réserves statutaires ou contractuelles","liability",442,"1062, 1063",""),
    ("Réserves réglementées","liability",442,"1064",""),
    ("Autres réserves","liability",442,"1068",""),
    ("Report à nouveau","liability",442,"11",""),
    ("Résultat de l'exercice [bénéfice ou perte]","liability",442,"12",""),
    ("Subventions d'investissement","liability",442,"13",""),
    ("Provisions réglementées","liability",442,"14",""),
    ("Fonds non remboursables","liability",442,"1671",""),
    ("Avances conditionnées","liability",442,"1673, 1674",""),
    ("Droits du concédant","liability",442,"229",""),
    ("Provisions pour risques","liability",442,"151",""),
    ("Provisions pour charges","liability",442,"152",""),
    ("Emprunts obligataires convertibles","liability",442,"161",""),
    ("Autres emprunts obligataires","liability",442,"163",""),
    ("Emprunts et dettes auprès des établissements de crédit","liability",442,"164, 51(C)",""),
    ("Emprunts et dettes financières diverses","liability",442,"165, 166, 168, 17",""),
    ("Instruments financiers à terme","liability",442,"52(C)",""),
    ("Avances et acomptes reçus sur commandes en cours","liability",442,"4191",""),
    ("Dettes fournisseurs et comptes rattachés","liability",442,"401, 403, 4081, 4088",""),
    ("Dettes fiscales et sociales","liability",442,"421, 422, 424, 426, 427, 428, 431, 437, 438, 44(C)",""),
    ("Dettes sur immobilisations et comptes rattachés","liability",442,"269, 279, 404, 405, 4084, 4088",""),
    ("Autres dettes","liability",442,"4196, 4197, 4198, 45(C), 464, 468, 509",""),
    ("Produits constatés d’avance","liability",442,"487",""),
    ("Écarts de conversion et différences d’évaluation - Passif","liability",442,"475, 477",""),
]

ABRIDGED_BALANCE_ROWS = [
    ("Capital souscrit non appelé","asset",449,"109",""),
    ("Frais d’établissement","asset",449,"201","2801, 2901"),
    ("Immobilisations incorporelles","asset",449,"203, 205, 206, 207, 208, 232, 237","2803, 2903, 2805, 2905, 2806, 2906, 2807, 2907, 2808, 2908, 2932"),
    ("Immobilisations corporelles","asset",449,"211, 212, 213, 214, 215, 218, 231, 238","2911, 2812, 2912, 2813, 2913, 2814, 2914, 2815, 2915, 2818, 2918, 2931"),
    ("Immobilisations financières","asset",449,"261, 262, 266, 267, 268, 271, 272, 273, 274, 275, 2761, 27682, 27684, 27685, 27688, 277","2961, 2962, 2966, 2967, 2968, 2971, 2972, 2973, 2974, 2975, 2976"),
    ("Stocks et en-cours","asset",449,"31, 32, 33, 34, 35, 37","391, 392, 393, 394, 395, 397"),
    ("Avances et acomptes versés sur commandes","asset",449,"4091",""),
    ("Créances Clients et comptes rattachés","asset",449,"411, 413, 416, 418","491"),
    ("Autres créances","asset",449,"409 [sauf 4091], 425, 439, 44(D), 45(D), 462, 465, 467","495, 496"),
    ("Charges constatées d’avance","asset",450,"486",""),
    ("Valeurs mobilières de placement","asset",450,"50 [sauf 509]","590"),
    ("Disponibilités","asset",450,"51(D), 53",""),
    ("Comptes de régularisation","asset",450,"169, 474, 476, 481",""),
    ("Capital","liability",449,"101, 108",""),
    ("Primes d’émission, de fusion, d’apport","liability",449,"104",""),
    ("Écarts de réévaluation et d’équivalence","liability",449,"105, 107",""),
    ("Réserves","liability",449,"106",""),
    ("Report à nouveau","liability",449,"11",""),
    ("Résultat de l’exercice","liability",449,"12",""),
    ("Subventions d’investissement","liability",449,"13",""),
    ("Provisions réglementées","liability",449,"14",""),
    ("Autres fonds propres","liability",449,"167, 229",""),
    ("Provisions","liability",449,"15",""),
    ("Emprunts et dettes assimilées","liability",449,"16 [sauf 167 et 169], 17, 51(C)",""),
    ("Avances et acomptes reçus sur commandes en cours","liability",449,"4191",""),
    ("Fournisseurs et comptes rattachés","liability",449,"401, 403, 4081, 4088",""),
    ("Autres dettes","liability",449,"269, 279, 404, 405, 4084, 4088, 4196, 4197, 4198, 42 [sauf 425], 43 [sauf 439], 44(C), 45(C), 464, 468, 509",""),
    ("Produits constatés d’avance","liability",450,"487",""),
    ("Comptes de régularisation","liability",450,"475, 477",""),
]

BASE_INCOME_ROWS = [
    # label, section, page, product_expr, charge_expr
    ("Ventes de marchandises","product",445,"707, 708, (7097), (7098)",""),
    ("Production vendue","product",445,"701, 702, 703, 704, 705, 706, 708, (7091), (7092), (7094), (7095), (7096), (7098)",""),
    ("Production stockée","product",445,"71",""),
    ("Production immobilisée","product",445,"72",""),
    ("Subventions","product",445,"74",""),
    ("Reprises sur amortissements, dépréciations et provisions","product",445,"781",""),
    ("Produits des cessions d’immobilisations incorporelles et corporelles","product",445,"757",""),
    ("Autres produits","product",445,"75 [sauf 757 et 755]",""),
    ("Achats de marchandises","charge",445,"","607, 608, (609)"),
    ("Variation de stocks - marchandises","charge",445,"","6037"),
    ("Achats de matières premières et autres approvisionnements","charge",445,"","601, 602, 608, (609)"),
    ("Variation de stocks - matières premières et approvisionnements","charge",445,"","6031, 6032"),
    ("Autres achats et charges externes","charge",445,"","604, 605, 606, 608, (609), 61 [sauf 619], (619), 62 [sauf 629], (629)"),
    ("Impôts, taxes et versements assimilés","charge",445,"","63"),
    ("Salaires","charge",445,"","641, 648, (649)"),
    ("Cotisations sociales","charge",445,"","645, 647, 648, (649)"),
    ("Dotations aux amortissements des immobilisations","charge",445,"","6811"),
    ("Dotations aux dépréciations des immobilisations","charge",445,"","6816"),
    ("Dotations aux dépréciations de l’actif circulant","charge",445,"","6817"),
    ("Dotations aux provisions","charge",445,"","6815"),
    ("Valeurs comptables des immobilisations incorporelles et corporelles cédées","charge",445,"","657"),
    ("Autres charges","charge",445,"","65 [sauf 657 et 655]"),
    ("Bénéfice attribué ou perte transférée","product",446,"755",""),
    ("Perte supportée ou bénéfice transféré","charge",446,"","655"),
    ("Produits financiers - De participation","product",446,"761",""),
    ("Produits financiers - Autres valeurs mobilières et créances de l'actif immobilisé","product",446,"762, 764",""),
    ("Produits financiers - Autres intérêts et produits assimilés","product",446,"763, 765",""),
    ("Produits financiers - Reprises sur dépréciations et provisions","product",446,"786",""),
    ("Produits financiers - Différences positives de change","product",446,"766",""),
    ("Produits des cessions d’immobilisations financières","product",446,"7671, 7672",""),
    ("Produits nets sur cessions de valeurs mobilières de placement et d’instruments de trésorerie","product",446,"7673, 7674",""),
    ("Charges financières - Dotations aux amortissements, dépréciations et provisions","charge",446,"","686"),
    ("Charges financières - Intérêts et charges assimilées","charge",446,"","661, 664, 665"),
    ("Charges financières - Différences négatives de change","charge",446,"","666"),
    ("Valeurs comptables des immobilisations financières cédées","charge",446,"","6671, 6672"),
    ("Charges nettes sur cessions de valeurs mobilières de placement et d’instruments de trésorerie","charge",446,"","6673, 6674"),
    ("Produits exceptionnels","product",446,"77, 787",""),
    ("Charges exceptionnelles","charge",446,"","67, 687"),
    ("Participation des salariés aux résultats","charge",446,"","691"),
    ("Impôts sur les bénéfices","charge",446,"","695, 696, 6981, (6989), (699)"),
]

ABRIDGED_INCOME_ROWS = [
    ("Montant net du chiffre d’affaires","product",452,"701, 702, 703, 704, 705, 706, 707, 708, (709)",""),
    ("Autres produits","product",452,"71, 72, 74, 75 [sauf 755], 781",""),
    ("Achats et autres charges externes","charge",452,"","601, 602, 603, 604, 605, 606, 607, 608, (609), 61 [sauf 619], (619), 62 [sauf 629], (629)"),
    ("Impôts, taxes et versements assimilés","charge",452,"","63"),
    ("Salaires","charge",452,"","641, 648, (649)"),
    ("Cotisations sociales","charge",452,"","645, 647, 648, (649)"),
    ("Dotations aux amortissements et aux dépréciations","charge",452,"","6811, 6816, 6817"),
    ("Dotations aux provisions","charge",452,"","6815"),
    ("Autres charges","charge",452,"","65 [sauf 655]"),
    ("Quote-part de résultat sur opérations faites en commun","mixed",452,"755","655"),
    ("Produits financiers - De participation","product",452,"761",""),
    ("Produits financiers - Autres valeurs mobilières et créances de l'actif immobilisé","product",453,"762, 764",""),
    ("Produits financiers - Autres intérêts et produits assimilés","product",453,"763, 765",""),
    ("Produits financiers - Reprises sur dépréciations et provisions","product",453,"786",""),
    ("Produits financiers - Différences positives de change","product",453,"766",""),
    ("Produits des cessions d’immobilisations financières","product",453,"7671, 7672",""),
    ("Produits nets sur cessions de valeurs mobilières de placement et d’instruments de trésorerie","product",453,"7673, 7674",""),
    ("Charges financières - Dotations aux amortissements, dépréciations et provisions","charge",453,"","686"),
    ("Charges financières - Intérêts et charges assimilées","charge",453,"","661, 664, 665"),
    ("Charges financières - Différences négatives de change","charge",453,"","666"),
    ("Valeurs comptables des immobilisations financières cédées","charge",453,"","6671, 6672"),
    ("Charges nettes sur cessions de valeurs mobilières de placement et d’instruments de trésorerie","charge",453,"","6673, 6674"),
    ("Produits exceptionnels","product",453,"77, 787",""),
    ("Charges exceptionnelles","charge",453,"","67, 687"),
    ("Participations des salariés aux résultats","charge",453,"","691"),
    ("Impôts sur les bénéfices","charge",453,"","695, 696, 6981, (6989), (699)"),
]


def _line(statement_id, idx, label, section, page, primary, contra="", income=False):
    components = []
    if income:
        product_expr, charge_expr = primary, contra
        if product_expr:
            components.append(_component("product", product_expr, page, parenthetical_side="debit", operation="add"))
        if charge_expr:
            components.append(_component("charge", charge_expr, page, parenthetical_side="credit", operation="add"))
    else:
        if section == "asset":
            if primary:
                components.append(_component("gross", primary, page, operation="add"))
            if contra:
                components.append(_component("amortization_depreciation", contra, page, operation="subtract"))
        else:
            if primary:
                components.append(_component("liability", primary, page, operation="add"))
    return {
        "line_id": f"{statement_id}:line:{idx:03d}",
        "line_code": f"L{idx:03d}",
        "label_source": label,
        "section": section,
        "source": {"document_id":"fr-pcg-recueil-2026-md","page_pdf":page,"section":"IR4 - tableau de passage"},
        "mapping_components": components,
    }


def build_reporting_dataset(known_account_codes: set[str]) -> dict:
    specs = [
        ("pcg2026:statement:balance_base","Bilan - système de base","balance","base","Art. 821-1",(437,439),BASE_BALANCE_ROWS,False),
        ("pcg2026:statement:income_base","Compte de résultat - système de base","income","base","Art. 821-2",(443,444),BASE_INCOME_ROWS,True),
        ("pcg2026:statement:balance_abrege","Bilan - système abrégé","balance","abrege","Art. 822-1",(447,447),ABRIDGED_BALANCE_ROWS,False),
        ("pcg2026:statement:income_abrege","Compte de résultat - système abrégé","income","abrege","Art. 822-2",(451,451),ABRIDGED_INCOME_ROWS,True),
    ]
    statements = []
    reverse = defaultdict(list)
    observations = []

    for sid, name, stype, system, article, model_pages, rows, income in specs:
        lines = []
        for idx, row in enumerate(rows, start=1):
            label, section, page, primary, contra = row
            line = _line(sid, idx, label, section, page, primary, contra, income=income)
            lines.append(line)

            for comp in line["mapping_components"]:
                mapping = comp["mapping"]
                for selector in mapping["selectors"]:
                    prefix = selector.get("account_prefix")
                    if not prefix:
                        continue
                    matches = sorted(c for c in known_account_codes if c.startswith(prefix))
                    # Remove exclusions.
                    matches = [
                        c for c in matches
                        if not any(c.startswith(x) for x in selector.get("exclude_prefixes", []))
                    ]
                    if not matches:
                        observations.append({
                            "type":"selector_without_account_match",
                            "statement_id":sid,
                            "line_id":line["line_id"],
                            "selector":selector,
                            "source":comp["source"],
                        })
                    for code in matches:
                        reverse[code].append({
                            "statement_id": sid,
                            "line_id": line["line_id"],
                            "line_label": label,
                            "component_role": comp["component_role"],
                            "operation": comp["operation"],
                            "side": selector.get("side"),
                        })

        statements.append({
            "statement_id": sid,
            "name": name,
            "statement_type": stype,
            "system": system,
            "regulatory_article": article,
            "model_source": {
                "document_id":"fr-pcg-recueil-2026-md",
                "page_start_pdf":model_pages[0],
                "page_end_pdf":model_pages[1],
            },
            "mapping_source_role": "IR4_example_table_indicative",
            "lines": lines,
        })

    return {
        "standard_id":"fr-pcg",
        "edition":"2026",
        "dataset_layer":"v3_reporting",
        "statements":statements,
        "account_to_statement_lines":dict(sorted(reverse.items())),
        "observations":observations,
        "statistics":{
            "statement_templates":len(statements),
            "statement_lines":sum(len(s["lines"]) for s in statements),
            "mapping_components":sum(len(l["mapping_components"]) for s in statements for l in s["lines"]),
            "accounts_reverse_indexed":len(reverse),
            "observations":len(observations),
        },
    }


def selector_matches(code: str, net_side: str | None, selector: dict) -> bool:
    if selector.get("side") and net_side != selector["side"]:
        return False
    prefix = selector.get("account_prefix")
    if not prefix or not code.startswith(prefix):
        return False
    if any(code.startswith(x) for x in selector.get("exclude_prefixes", [])):
        return False
    return True


def evaluate_statement(statement: dict, trial_balance: list[dict]) -> dict:
    rows = []
    for line in statement["lines"]:
        total = 0.0
        component_values = []
        for comp in line["mapping_components"]:
            value = 0.0
            for row in trial_balance:
                debit = float(row.get("debit_balance",0) or 0)
                credit = float(row.get("credit_balance",0) or 0)
                net = debit-credit
                side = "debit" if net > 0 else ("credit" if net < 0 else None)
                amount = abs(net)
                if any(selector_matches(str(row["account_code"]), side, s) for s in comp["mapping"]["selectors"]):
                    value += amount
            total += value if comp["operation"] == "add" else -value
            component_values.append({"role":comp["component_role"],"value":value,"operation":comp["operation"]})
        rows.append({"line_id":line["line_id"],"label":line["label_source"],"value":total,"components":component_values})
    return {"statement_id":statement["statement_id"],"rows":rows}
