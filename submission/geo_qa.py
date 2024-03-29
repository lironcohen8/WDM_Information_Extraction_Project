import sys
import requests
import lxml.html
import rdflib
import urllib.parse as parse

WIKI_PREFIX = "http://en.wikipedia.org"
GRAPH_FILE_NAME = "ontology.nt"
LIST_OF_COUNTRIES_URL = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
COUTNRIES_XPATH_QUERY = "//tr/td[1]/span[1]/a/@href"
CHANNEL_ISLANDS_XPATH_QUERY = "//tr/td//a[@title = 'Channel Islands']/@href"
WESTERN_SAHARA_XPATH_QUERY = "//tr/td//a[@title = 'Western Sahara']/@href"
AFGHANISTAN_XPATH_QUERY = "//tr/td//a[@title = 'Afghanistan']/@href"
PRESIDENT_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//*[text() = 'President']/ancestor::tr/td//a[contains(@href, 'wiki')][1]/@href"
PRIME_MINISTER_XPATH_QUERY = "//table[contains(@class,'infobox')][1]//*[text() = 'Prime Minister']/ancestor::tr/td//a[contains(@href, 'wiki')][1]/@href"
POPULATION_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//*[contains(text(), 'Population')]/following::tr[1]/td[1]/text()[1]"
POPULATION_SPECIAL_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//*[text() = 'Population']/following::tr[1]/td//span/text()"
POPULATION_CHANNEL_ISLANDS_QUERY = "//table[contains(@class, 'infobox')][1]/tbody/tr[21]/td/text()[1]"
AREA_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//*[contains(text(), 'Area')]/following::tr[1]/td/text()[1]"
AREA_CHANNEL_ISLANDS_QUERY = "//table[contains(@class, 'infobox')][1]/tbody/tr[10]/td/text()[1]"
GOVERNMENT_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//*[text() = 'Government']/ancestor::tr/td//a[contains(@href, 'wiki')]/@href"
CAPITAL_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//*[text() = 'Capital']/following::a[1]/@href"
PERSON_BIRTHDATE_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//*[text() = 'Born']/parent::tr//span[@class ='bday']/text()"
PERSON_BIRTHPLACE_XPATH_QUERY_A = "//table[contains(@class, 'infobox')][1]//*[text() = 'Born']/parent::tr//td/a[last()]/@href"
PERSON_BIRTHPLACE_XPATH_QUERY_TEXT = "//table[contains(@class, 'infobox')][1]//*[text() = 'Born']/parent::tr//td/text()[last()]"
PERSON_BIRTHPLACE_ZELENSKYY_QUERY = "/html/body/div[3]/div[3]/div[5]/div[1]/table[1]/tbody/tr[12]/td/text()[4]"
PERSON_BIRTHPLACE_OUATTARA_QUERY = "/html/body/div[3]/div[3]/div[5]/div[1]/table[1]/tbody/tr[23]/td/span[3]/a/@href"

countriesSet = set()

def get_countries_urls():
    r = requests.get(LIST_OF_COUNTRIES_URL)
    doc = lxml.html.fromstring(r.content)
    countries_relative_urls = doc.xpath(COUTNRIES_XPATH_QUERY)
    countries_relative_urls.insert(189, doc.xpath(CHANNEL_ISLANDS_XPATH_QUERY)[0])
    countries_relative_urls.insert(169, doc.xpath(WESTERN_SAHARA_XPATH_QUERY)[0])
    countries_relative_urls.insert(36, doc.xpath(AFGHANISTAN_XPATH_QUERY)[0])
    countries_urls = [f"{WIKI_PREFIX}{url}" for url in countries_relative_urls]
    return countries_urls


def create_graph():
    graph = rdflib.Graph()
    countries_urls = get_countries_urls()
    for country_url in countries_urls:
        country_name = country_url.split("/")[-1]
        countriesSet.add(country_name)
    add_triplets_to_graph(graph, countries_urls)
    graph.serialize(GRAPH_FILE_NAME, format="nt", encoding="utf-8", errors="ignore")


def add_triplets_to_graph(g, countries_urls):
    for country_url in countries_urls:
        country_name = country_url.split("/")[-1]
        r = requests.get(country_url)
        doc = lxml.html.fromstring(r.content)
        add_country_triplet_to_graph(g, doc, country_name, PRESIDENT_XPATH_QUERY, 'president_of')
        add_country_triplet_to_graph(g, doc, country_name, PRIME_MINISTER_XPATH_QUERY, 'prime_minister_of')
        add_country_triplet_to_graph(g, doc, country_name, AREA_XPATH_QUERY, 'area_of')
        add_country_triplet_to_graph(g, doc, country_name, GOVERNMENT_XPATH_QUERY, 'government_in')
        add_country_triplet_to_graph(g, doc, country_name, CAPITAL_XPATH_QUERY, 'capital_of')
        if (country_name in ("Belarus", "Dominican_Republic", "Malta", "Russia")):
            add_country_triplet_to_graph(g, doc, country_name, POPULATION_SPECIAL_XPATH_QUERY, 'population_of')
        elif country_name == "Channel_Islands":
            add_country_triplet_to_graph(g, doc, country_name, POPULATION_CHANNEL_ISLANDS_QUERY, 'population_of')
            add_country_triplet_to_graph(g, doc, country_name, AREA_CHANNEL_ISLANDS_QUERY, 'area_of')
        else:
            add_country_triplet_to_graph(g, doc, country_name, POPULATION_XPATH_QUERY, 'population_of')


def add_country_triplet_to_graph(g, doc, country_name, xpath_query, relation):
    query_result_list = doc.xpath(xpath_query)
    if len(query_result_list) == 0:
        return
    if relation == 'government_in':
        for result_url in query_result_list:
            result_name = result_url.split("/")[-1].strip()
            g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{result_name}"),
                rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
                rdflib.URIRef(f"{WIKI_PREFIX}/{country_name}")))
    else:
        result_url = query_result_list[0]
        result_name = result_url.split("/")[-1].strip().split()[0]
        g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{result_name}"),
            rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
            rdflib.URIRef(f"{WIKI_PREFIX}/{country_name}")))
        if relation in ['president_of', 'prime_minister_of']:
             add_person_triplets_to_graph(g, result_name, f"{WIKI_PREFIX}{result_url}")


def add_person_triplets_to_graph(g, person_name, person_url):
    r = requests.get(person_url)
    doc = lxml.html.fromstring(r.content)
    add_person_bday_triplet_to_graph(g, doc, person_name, PERSON_BIRTHDATE_XPATH_QUERY, 'born_on')
    add_person_bplace_triplet_to_graph(g, doc, person_name, 'born_in')


def add_person_bplace_triplet_to_graph(g, doc, person_name, relation):
    if person_name == "Volodymyr_Zelenskyy":
        zelenskyy_birthplace = doc.xpath(PERSON_BIRTHPLACE_ZELENSKYY_QUERY)[0].split()[-1][:-1]
        g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{person_name}"),
                rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
                rdflib.URIRef(f"{WIKI_PREFIX}/{zelenskyy_birthplace}")))
        return
    elif person_name == "Alassane_Ouattara":
        ouattara_birthplace = doc.xpath(PERSON_BIRTHPLACE_OUATTARA_QUERY)[0].split('/')[-1]
        g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{person_name}"),
                rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
                rdflib.URIRef(f"{WIKI_PREFIX}/{ouattara_birthplace}")))
        return
    else:
        query_result_list = doc.xpath(PERSON_BIRTHPLACE_XPATH_QUERY_A)
        if len(query_result_list) > 0:
            result_url = query_result_list[0]
            result_name = result_url.split("/")[-1].strip()
            if result_name not in countriesSet:
                query_result_list = doc.xpath(PERSON_BIRTHPLACE_XPATH_QUERY_TEXT)
                if len(query_result_list) > 0:
                    result_url = query_result_list[0]
                    result_name = result_url.replace(',','').strip().replace(' ','_')
                    if result_name not in countriesSet:
                        return
            g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{person_name}"),
                    rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
                    rdflib.URIRef(f"{WIKI_PREFIX}/{result_name}")))


def add_person_bday_triplet_to_graph(g, doc, person_name, xpath_query, relation):
    query_result_list = doc.xpath(xpath_query)
    if len(query_result_list) > 0:
        result_url = query_result_list[0]
        result_name = result_url
        g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{person_name}"),
               rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
               rdflib.URIRef(f"{WIKI_PREFIX}/{result_name}")))


def ask_question(question):
    sparql_query = parse_question_to_query(question)
    if sparql_query == None:
        return
    graph = rdflib.Graph()
    graph.parse(GRAPH_FILE_NAME, format="nt")
    raw_answer = graph.query(sparql_query)
    answer = ""
    if "Who" in question and "president" not in question and "minister" not in question:
        parsed_list_pre = [ans.pre_c for ans in list(raw_answer)]
        if len(parsed_list_pre) > 0 and parsed_list_pre[0] != None:
            parsed_list_pre = ["President of " + ans.split("/")[-1].replace('_', ' ') for ans in parsed_list_pre]
        else:
            parsed_list_pre = []
        
        parsed_list_pri = [ans.pri_c for ans in list(raw_answer)]
        if len(parsed_list_pri) > 0 and parsed_list_pri[0] != None:
            parsed_list_pri = ["Prime minister of " + ans.split("/")[-1].replace('_', ' ') for ans in parsed_list_pri]
        else:
            parsed_list_pri = []

        parsed_list = sorted(parsed_list_pre + parsed_list_pri)
        answer = ', '.join(parsed_list)
    else:
        parsed_list = sorted([ans.x.split("/")[-1].replace('_', ' ') for ans in list(raw_answer)])
        if len(parsed_list) == 0:
            return
        answer = ', '.join(parsed_list)
        if "area" in question:
            answer += " km squared"
    answer = parse.unquote(answer).replace('"','')
    print(answer)


def parse_question_to_query(question):
    question = '_'.join(question.split())
    question_word = question.split('_')[0]
    if question_word == "Who":  # questions 1,2,11
        if "president" in question:
            country_name = question.split("of_", 1)[-1][:-1]
            return generate_country_sparql_query(country_name, "president_of")
        elif "minister" in question:
            country_name = question.split("of_", 1)[-1][:-1]
            return generate_country_sparql_query(country_name, 'prime_minister_of')
        else:
            person_name = question.split("is_", 1)[-1][:-1]
            return generate_who_is_person_sparql_query(person_name)
    elif question_word == "What":  # questions 3,4,5,6
        if "population" in question:
            country_name = question.split("of_", 1)[-1][:-1]
            return generate_country_sparql_query(country_name, 'population_of')
        elif "area" in question:
            country_name = question.split("of_", 1)[-1][:-1]
            return generate_country_sparql_query(country_name, 'area_of')
        elif "government" in question:
            country_name = question.split("in_", 1)[-1][:-1]
            return generate_country_sparql_query(country_name, 'government_in')
        else:
            country_name = question.split("of_", 1)[-1][:-1]
            return generate_country_sparql_query(country_name, 'capital_of')
    elif question_word == "When":  # questions 7,9
        if "president" in question:
            country_name = question.split("of_", 1)[-1][:-6]
            return generate_born_person_sparql_query(country_name, 'born_on', 'president_of')
        elif "minister" in question:
            country_name = question.split("of_", 1)[-1][:-6]
            return generate_born_person_sparql_query(country_name, 'born_on', 'prime_minister_of')
    elif question_word == "Where":  # questions 8,10
        if "president" in question:
            country_name = question.split("of_", 1)[-1][:-6]
            return generate_born_person_sparql_query(country_name, 'born_in', 'president_of')
        elif "minister" in question:
            country_name = question.split("of_", 1)[-1][:-6]
            return generate_born_person_sparql_query(country_name, 'born_in', 'prime_minister_of')
    elif question_word == "List":  # question 13
        if "contains" in question:
            substring = question.split("_")[-1]
            return generate_substring_sparql_query(substring)
        else: # our question: List all countries that their names and their capitals' names end with the string <str>
            substring = question.split("_")[-1]
            return generate_country_capital_ends_sparql_query(substring)
    else:  # questions 12,14
        if "are_also" in question:
            form1 = question.split("many_", 1)[-1].split("_are", 1)[0]
            form2 = question.split("also_", 1)[-1][:-1]
            return generate_forms_sparql_query(form1, form2)
        else:
            country_name = question.split("in_", 1)[-1][:-1]
            return generate_born_count_sparql_query(country_name)
        

def generate_country_sparql_query(country_name, relation):

    return "select ?x where " \
            "{ " \
            f"?x <{WIKI_PREFIX}/{relation}> <{WIKI_PREFIX}/{country_name}>" \
            " }" 


def generate_born_person_sparql_query(country_name, relation, relation_title):
    return "select ?x where " \
            "{ " \
            f"?p <{WIKI_PREFIX}/{relation_title}> <{WIKI_PREFIX}/{country_name}> ." \
            f"?p <{WIKI_PREFIX}/{relation}> ?x" \
            " }"


def generate_who_is_person_sparql_query(person_name):
    return "select * where " \
            "{ " \
                "{ " \
                    "select ?pre_c where " \
                    "{ " \
                    f"<{WIKI_PREFIX}/{person_name}> <{WIKI_PREFIX}/president_of> ?pre_c ." \
                    " }" \
                " }" \
            "union" \
                "{ " \
                    "select ?pri_c where " \
                    "{ " \
                    f"<{WIKI_PREFIX}/{person_name}> <{WIKI_PREFIX}/prime_minister_of> ?pri_c ." \
                    " }" \
                " }" \
            " }"


def generate_substring_sparql_query(substring):
    return "select ?x where " \
            "{" \
            f"?c <{WIKI_PREFIX}/capital_of> ?x " \
            f"filter contains(lcase(strafter(str(?c), '{WIKI_PREFIX}/')),lcase('{substring}'))" \
            "}"


def generate_country_capital_ends_sparql_query(end_string):
    return "select ?x where " \
            "{" \
            f"?c <{WIKI_PREFIX}/capital_of> ?x " \
            f"filter (strEnds(lcase(str(?c)),lcase('{end_string}')) " \
            f"&& strEnds(lcase(str(?x)),lcase('{end_string}')))" \
            " }"


def generate_forms_sparql_query(form1, form2):
    return "select ?c (count(distinct ?c) as ?x) where " \
            "{ " \
                f"?f1 <{WIKI_PREFIX}/government_in> ?c . " \
                f"?f2 <{WIKI_PREFIX}/government_in> ?c . " \
                f"filter (strEnds(str(?f1),'/{form1}') " \
                f"&& strEnds(str(?f2),'/{form2}'))" \
            " }"


def generate_born_count_sparql_query(country_name):
    return "select ?p (count(distinct ?p) as ?x) where " \
            "{" \
            f"?p <{WIKI_PREFIX}/president_of> ?c . " \
            f"?p <{WIKI_PREFIX}/born_in> <{WIKI_PREFIX}/{country_name}> " \
            "}"


if __name__ == '__main__':
    if sys.argv[1] == "create":
        create_graph()
    elif sys.argv[1] == "question":
        ask_question(sys.argv[2])
