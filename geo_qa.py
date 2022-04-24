import sys
from pytz import country_names

import requests
import lxml.html
import rdflib

WIKI_PREFIX = "http://en.wikipedia.org"
GRAPH_FILE_NAME = "ontology.nt"
LIST_OF_COUNTRIES_URL = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
COUTNRIES_XPATH_QUERY = "//tr/td[1]/span[1]/a/@href"
CHANNEL_ISLANDS_XPATH_QUERY = "//tr/td//a[@title = 'Channel Islands']/@href"
WESTERN_SAHARA_XPATH_QUERY = "//tr/td//a[@title = 'Western Sahara']/@href"
AFGHANISTAN_XPATH_QUERY = "//tr/td//a[@title = 'Afghanistan']/@href"
PRESIDENT_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//a[text() = 'President']/ancestor::tr/td//a/@href"
PRIME_MINISTER_XPATH_QUERY = "//table[contains(@class,'infobox')][1]//a[text() = 'Prime Minister']/ancestor::tr/td//a/@href"
POPULATION_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//a[contains(text(), 'Population')]/following::tr[1]/td/text()[1]"
AREA_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//a[contains(text(), 'Area')]/following::tr[1]/td/text()[1]"
GOVERNMENT_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//a[text() = 'Government']/ancestor::tr/td//a/@href"
CAPITAL_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//th[text() = 'Capital']/following::a[1]/@href"
PERSON_BIRTHDATE_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//th[text() = 'Born']/parent::tr//span[@class ='bday']/text()"
PERSON_BIRTHPLACE_XPATH_QUERY = "//table[contains(@class, 'infobox')][1]//th[text() = 'Born']/parent::tr//td//text()[last()]"
#//table[contains(@class, 'infobox')]//th[text() = 'Born']/parent::tr//td/a[last()]
#//table[contains(@class, 'infobox')]//th[text() = 'Born']/parent::tr//td/text()[last()]

def get_countries_urls():
    r = requests.get(LIST_OF_COUNTRIES_URL)
    doc = lxml.html.fromstring(r.content)
    countries_relative_urls = doc.xpath(COUTNRIES_XPATH_QUERY)
    countries_relative_urls.insert(189, doc.xpath(CHANNEL_ISLANDS_XPATH_QUERY)[0])
    countries_relative_urls.insert(169, doc.xpath(WESTERN_SAHARA_XPATH_QUERY)[0])
    countries_relative_urls.insert(36, doc.xpath(AFGHANISTAN_XPATH_QUERY)[0])
    countries_urls = [f"{WIKI_PREFIX}{url}" for url in countries_relative_urls]
    #TODO checks countries_urls = ["http://en.wikipedia.org/wiki/Hungary"]
    return countries_urls


def create_graph():
    graph = rdflib.Graph()
    countries_urls = get_countries_urls()
    add_entities_to_graph(graph, countries_urls)
    graph.serialize(GRAPH_FILE_NAME, format="nt")


def add_entities_to_graph(g, countries_urls):
    for country_url in countries_urls:
        country_name = country_url.split("/")[-1]
        print(country_name)
        r = requests.get(country_url)
        doc = lxml.html.fromstring(r.content)
        add_country_entity_to_graph(g, doc, country_name, PRESIDENT_XPATH_QUERY, 'president_of')
        add_country_entity_to_graph(g, doc, country_name, PRIME_MINISTER_XPATH_QUERY, 'prime_minister_of')
        add_country_entity_to_graph(g, doc, country_name, POPULATION_XPATH_QUERY, 'population_of')
        add_country_entity_to_graph(g, doc, country_name, AREA_XPATH_QUERY, 'area_of')
        add_country_entity_to_graph(g, doc, country_name, GOVERNMENT_XPATH_QUERY, 'government_in')
        add_country_entity_to_graph(g, doc, country_name, CAPITAL_XPATH_QUERY, 'capital_of')


def add_country_entity_to_graph(g, doc, country_name, xpath_query, relation):
    query_result_list = doc.xpath(xpath_query)
    for result_url in query_result_list:
        result_name = result_url.split("/")[-1].strip().split()[0]
        #result_name = "_".join(result_name.split() )

        # TODO delete after debug print(result_name, "-", relation, "-", country_name)
        g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{result_name}"),
               rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
               rdflib.URIRef(f"{WIKI_PREFIX}/{country_name}")))
        if relation in ['president_of', 'prime_minister_of']:
            add_person_entities_to_graph(g, result_name, f"{WIKI_PREFIX}{result_url}")


def add_person_entities_to_graph(g, person_name, person_url):
    r = requests.get(person_url)
    doc = lxml.html.fromstring(r.content)
    add_person_entity_to_graph(g, doc, person_name, PERSON_BIRTHDATE_XPATH_QUERY, 'born_on')
    add_person_entity_to_graph(g, doc, person_name, PERSON_BIRTHPLACE_XPATH_QUERY, 'born_in')


def add_person_entity_to_graph(g, doc, person_name, xpath_query, relation):
    query_result_list = doc.xpath(xpath_query)
    if len(query_result_list) > 0:
        result_url = query_result_list[0]
        result_name = result_url.split(" ")[-1].strip()
        # TODO delete after debug print(person_name, "-", relation, "-", result_name)
        g.add((rdflib.URIRef(f"{WIKI_PREFIX}/{person_name}"),
               rdflib.URIRef(f"{WIKI_PREFIX}/{relation}"),
               rdflib.URIRef(f"{WIKI_PREFIX}/{result_name}")))


def ask_question(question):
    sparql_query = parse_question_to_query(question)
    graph = rdflib.Graph()
    graph.parse(GRAPH_FILE_NAME, format="nt")
    raw_answer = graph.query(sparql_query)
    answer = ""
    if "Who" in question and "president" not in question and "minister" not in question:
        parsed_list = [ans.pre_c for ans in list(raw_answer)]
        if parsed_list[0] != None:
            answer = "President of " + parsed_list[0].split("/")[-1].replace('_', ' ')
        parsed_list = [ans.pri_c for ans in list(raw_answer)]
        if parsed_list[0] != None:
            answer = "Prime minister of "  + parsed_list[0].split("/")[-1].replace('_', ' ')
    else:
        parsed_list = sorted([ans.x.split("/")[-1].replace('_', ' ') for ans in list(raw_answer)])
        answer = ', '.join(parsed_list)
        if "area" in question:
            answer += " km squared"
    print(answer)


def parse_question_to_query(question):
    question = '_'.join(question.split())
    question_word = question.split('_')[0]
    if question_word == "Who":  # questions 1,2,11
        if "president" in question:
            country_name = question.split("of_", 1)[-1][:-1]
            return generate_country_sparql_query( country_name, "president_of")
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
            f"filter contains(lcase(str(?c)),lcase('{substring}'))" \
            "}"


def generate_country_capital_ends_sparql_query(end_string):
    return "select ?x where " \
            "{" \
            f"?c <{WIKI_PREFIX}/capital_of> ?x " \
            f"filter (strEnds(lcase(str(?c)),lcase('{end_string}')) " \
            f"&& strEnds(lcase(str(?x)),lcase('{end_string}')))" \
            " }"


def generate_forms_sparql_query(form1, form2):
    return "select ?x where " \
            "{ " \
            f"?f1 <{WIKI_PREFIX}/government_in> ?x . " \
            f"?f2 <{WIKI_PREFIX}/government_in> ?x . " \
            f"filter (contains(lcase(str(?f1)),lcase('{form1}')) " \
            f"&& contains(lcase(str(?f2)),lcase('{form2}')))" \
            " }"


def generate_born_count_sparql_query(country_name):
    return "select (count(distinct ?p) as ?x) where " \
            "{" \
            f"?p <{WIKI_PREFIX}/president_of> ?c ." \
            f"?p born_in <{WIKI_PREFIX}/{country_name}>" \
            "}"


# TODO: Add encodings to fix president of Mexico for example
# TODO: Ask about substrings that are included in Wiki prefix
# TODO: fix birth place query
# TODO: Check on NOVA

# TODO: Edge cases: DO NOT DELETE THESE TODOS
# Add Western Sahara (170) and Channel Islands (190) and afghanistan
# infobox[1] because hungary had more than 1 infobox
# split by of was wrong in president of isle of man, added 1


if __name__ == '__main__':
    if sys.argv[1] == "create":
        create_graph()
    elif sys.argv[1] == "question":
        ask_question(sys.argv[2])
