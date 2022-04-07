import sys

import requests
import lxml.html
import rdflib

WIKI_PREFIX = "http://en.wikipedia.org"
GRAPH_FILE_NAME = "ontology.nt"
LIST_OF_COUNTRIES_URL = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
PRESIDENT_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[text() = 'President']/ancestor::tr/td/a/@href"
PRIME_MINISTER_XPATH_QUERY = "//table[contains(@class,'infobox')]//a[text() = 'Prime Minister']/ancestor::tr/td/a/@href"
POPULATION_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[contains(text(), 'Population')]/following::tr[1]/td/text()[1]"
AREA_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[contains(text(), 'Area')]/following::tr[1]/td/text()[1]"
GOVERNMENT_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[text() = 'Government']/ancestor::tr/td/a/@href"
CAPITAL_XPATH_QUERY = "//table[contains(@class, 'infobox')]//th[text() = 'Capital']/following::a[1]/@href"
PERSON_BIRTHDATE_XPATH_QUERY = "//table[contains(@class, 'infobox')]//th[text() = 'Born']/parent::tr//span[@class ='bday']/text()"
PERSON_BIRTHPLACE_XPATH_QUERY = "//table[contains(@class, 'infobox')]//th[text() = 'Born']/parent::tr//td/text()[last()]"


def get_countries_urls():
    r = requests.get(LIST_OF_COUNTRIES_URL)
    doc = lxml.html.fromstring(r.content)
    countries_relative_urls = doc.xpath("//tr/td[1]/span[1]/a/@href")
    countries_urls = [f"{WIKI_PREFIX}{url}" for url in countries_relative_urls]
    return countries_urls
    # TODO: Add Western Sahara (170) and Channel Islands (190)


def create_graph():
    graph = rdflib.Graph()
    countries_urls = get_countries_urls()
    add_entities_to_graph(graph, countries_urls)
    graph.serialize(GRAPH_FILE_NAME, format="nt")


def add_entities_to_graph(g, countries_urls):
    for country_url in countries_urls:
        country_name = country_url.split("/")[-1]
        # print(country_name)
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
    if len(query_result_list) > 0:
        result_url = query_result_list[0]
        result_name = result_url.split("/")[-1].strip().split(" ")[0]
        print(result_name, "-", relation, "-", country_name)
        g.add((rdflib.URIRef(result_name),
               rdflib.URIRef(relation),
               rdflib.URIRef(country_name)))
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
        print(person_name, "-", relation, "-", result_name)
        g.add((rdflib.URIRef(person_name),
               rdflib.URIRef(relation),
               rdflib.URIRef(result_name)))


def ask_question(question):
    sparql_query = parse_question_to_query(question)
    graph = rdflib.Graph()
    graph.parse(GRAPH_FILE_NAME, format="nt")
    answer = graph.query(sparql_query)
    print(answer)


def parse_question_to_query(question):
    question_word = question.split(' ')[0]
    if question_word == "Who":  # questions 1,2,11
        if "president" in question:
            country_name = question.split("of ")[-1][:-1]
            return generate_country_sparql_query(country_name, 'president_of')
        elif "minister" in question:
            country_name = question.split("of ")[-1][:-1]
            return generate_country_sparql_query(country_name, 'prime_minister_of')
        else:
            # TODO: complete
            pass
    elif question_word == "What":  # questions 3,4,5,6
        if "population" in question:
            country_name = question.split("of ")[-1][:-1]
            return generate_country_sparql_query(country_name, 'population_of')
        elif "area" in question:
            country_name = question.split("of ")[-1][:-1]
            return generate_country_sparql_query(country_name, 'area_of')
        elif "government" in question:
            country_name = question.split("in ")[-1][:-1]
            return generate_country_sparql_query(country_name, 'government_in')
        else:
            country_name = question.split("of ")[-1][:-1]
            return generate_country_sparql_query(country_name, 'capital_of')
    elif question_word == "When":  # questions 7,9
        if "president" in question:
            country_name = question.split("of ")[-1][:-6]
            return generate_person_sparql_query(country_name, 'born_on', 'president_of')
        elif "minister" in question:
            country_name = question.split("of ")[-1][:-6]
            return generate_person_sparql_query(country_name, 'born_on', 'prime_minister_of')
    elif question_word == "Where":  # questions 8,10
        if "president" in question:
            country_name = question.split("of ")[-1][:-6]
            return generate_person_sparql_query(country_name, 'born_in', 'president_of')
        elif "minister" in question:
            country_name = question.split("of ")[-1][:-6]
            return generate_person_sparql_query(country_name, 'born_in', 'prime_minister_of')
    elif question_word == "List":  # question 13
        substring = question.split(" ")[-1]
        return generate_substring_sparql_query(substring)
    else:  # questions 12,14
        if "are also" in question:
            form1 = question.split("many ")[-1].split(" are")[0]
            form2 = question.split("also ")[-1][:-1]
            return generate_forms_sparql_query(form1, form2)
        else:
            country_name = question.split("in ")[-1][:-1]
            return generate_born_count_sparql_query(country_name)
        

def generate_country_sparql_query(country_name, relation):
    return "select ?p " \
            f"where ?p {relation} {country_name}"


def generate_person_sparql_query(country_name, relation, relation_title):
    return "select ?d where " \
            "{" \
            f"?p {relation_title} {country_name} ." \
            f"?p {relation} ?d" \
            "}"


def generate_substring_sparql_query(substring):
    return "select ?n where " \
            "{" \
            "?n capital_of ?c ." \
            f"filter contains(?c,{substring})" \
            "}"


def generate_forms_sparql_query(form1, form2):
    return "select count(distinct ?c) where " \
            "{" \
            "?fs government_in ?c ." \
            f"filter contains(?fs,{form1})" \
            f"filter contains(?fs,{form2})" \
            "}"


def generate_born_count_sparql_query(country_name):
    return "select count(distinct ?p) where " \
            "{" \
            "?p president_of ?c ." \
            f"?p born_in {country_name}" \
            "}"


# TODO: Add squared in answer of area
# TODO: Add comma separating in answer in government
# TODO: Add encodings to fix president of Mexico for example
# TODO: Check Russia values
# TODO: fix birth place query
# TODO: Add new question


if __name__ == '__main__':
    if sys.argv[1] == "create":
        create_graph()
    elif sys.argv[1] == "question":
        ask_question(sys.argv[2])
