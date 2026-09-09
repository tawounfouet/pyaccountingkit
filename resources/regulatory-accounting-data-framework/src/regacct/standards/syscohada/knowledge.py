from collections import defaultdict

def build_accounting_knowledge(toc,apps):
    topics=[]
    for c in toc["chapters"]:topics.append({"topic_id":c["chapter_id"],"topic_type":"guide_chapter","part_key":c["part_key"],"title_source":c["title"],"page_start_printed":c["page_start_printed"]})
    for s in toc["sections"]:topics.append({"topic_id":s["section_id"],"topic_type":"guide_section","part_key":s["part_key"],"chapter_number":s["chapter_number"],"title_source":s["title"],"page_start_printed":s["page_start_printed"]})
    bypart=defaultdict(list);summaries=[]
    for a in apps["applications"]:
        bypart[a["part_key"]].append(a["application_id"])
        summaries.append({"application_id":a["application_id"],"application_number":a["application_number"],"title_source":a["title_source"],
                          "part_key":a["part_key"],"chapter_number":a["chapter_number"],"section_number":a["section_number"],
                          "page_start_pdf":a["page_start_pdf"],"page_end_pdf":a["page_end_pdf"],"account_mentions":a["account_mentions"],
                          "executable_rules_generated":False})
    return {"standard_id":"ohada-syscohada","edition":"2017","dataset_layer":"v2_accounting_knowledge",
            "knowledge_policy":{"guide_is_application_guidance":True,"application_examples_are_regulatory_posting_rules":False,
                                "executable_rules_generated":False,"account_mentions_are_source_evidence_or_prefix_resolution":True},
            "topics":topics,"applications":summaries,"account_to_applications":apps["account_to_applications"],
            "capability_groups":{"current_operations":bypart["PREMIERE"],"specific_operations":bypart["DEUXIEME"],
                                 "financial_statements":bypart["TROISIEME"],"consolidation_and_combination":bypart["QUATRIEME"]},
            "statistics":{"topics":len(topics),"chapters":len(toc["chapters"]),"sections":len(toc["sections"]),"applications":len(summaries),
                          "accounts_reverse_indexed":len(apps["account_to_applications"]),"current_operation_applications":len(bypart["PREMIERE"]),
                          "specific_operation_applications":len(bypart["DEUXIEME"]),"financial_statement_applications":len(bypart["TROISIEME"]),
                          "consolidation_applications":len(bypart["QUATRIEME"])}}

def build_consolidation_registry(apps):
    rows=[a for a in apps["applications"] if a["part_key"]=="QUATRIEME"]
    return {"standard_id":"ohada-syscohada","edition":"2017","dataset_layer":"consolidation_applications","applications":rows,
            "statistics":{"applications":len(rows),"first_application":min(a["application_number"] for a in rows),
                          "last_application":max(a["application_number"] for a in rows)}}
