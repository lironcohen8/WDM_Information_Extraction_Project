import requests
import lxml.html
import rdflib

WIKI_PREFIX = "http://en.wikipedia.org"
LIST_OF_COUNTRIES_URL = "https://en.wikipedia.org/wiki/List_of_countries_by_population_(United_Nations)"
PRESIDENTS_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[text() = 'President']/ancestor::tr/td/a/@href"
PRIME_MINISTERS_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[text() = 'Prime Minister']/ancestor::tr/td/a/@href"
POPULATION_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[contains(text(), 'Population')]/following::tr[1]/td/text()[1]"
AREA_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[contains(text(), 'Area')]/following::tr[1]/td/text()[1]"
GOVERNMENT_XPATH_QUERY = "//table[contains(@class, 'infobox')]//a[text() = 'Government']/ancestor::tr/td/a/@href"
CAPITAL_XPATH_QUERY = "//table[contains(@class, 'infobox')]//th[text() = 'Capital']/following::a[1]/@href"

def get_countries_urls():
    r = requests.get(LIST_OF_COUNTRIES_URL)
    doc = lxml.html.fromstring(r.content)
    countries_relative_urls = doc.xpath("//tr/td[1]/span[1]/a/@href")
    countries_urls = [f"{WIKI_PREFIX}{url}" for url in countries_relative_urls]
    return countries_urls
    # TODO: Add Western Sahara (170) and Channel Islands (190)


def create_ontology():
    g = rdflib.Graph()
    countries_urls = get_countries_urls()
    add_entities_to_graph(g, countries_urls)
    g.serialize("ontology.nt", format="nt")


def add_entities_to_graph(g, countries_urls):
    for country_url in countries_urls:
        country_name = country_url.split("/")[-1]
        # print(country_name)
        r = requests.get(country_url)
        doc = lxml.html.fromstring(r.content)
        add_country_entity_to_graph(g, doc, country_name, PRESIDENTS_XPATH_QUERY, 'president_of')
        add_country_entity_to_graph(g, doc, country_name, PRIME_MINISTERS_XPATH_QUERY, 'prime_minister_of')
        add_country_entity_to_graph(g, doc, country_name, POPULATION_XPATH_QUERY, 'population_of')
        add_country_entity_to_graph(g, doc, country_name, AREA_XPATH_QUERY, 'area_of')
        add_country_entity_to_graph(g, doc, country_name, GOVERNMENT_XPATH_QUERY, 'government_in')
        add_country_entity_to_graph(g, doc, country_name, CAPITAL_XPATH_QUERY, 'capital_of')


def add_country_entity_to_graph(g, doc, country_name, query, relation):
    query_result_list = doc.xpath(query)
    if len(query_result_list) > 0:
        result_url = query_result_list[0]
        result_name = result_url.split("/")[-1].strip().split(" ")[0]
        print(result_name, "-", relation, "-", country_name)
        g.add((rdflib.URIRef(result_name),
               rdflib.URIRef(relation),
               rdflib.URIRef(country_name)))

# TODO: Add squared in answer of area
# TODO: Add comma separating in answer in government
# TODO: Add encodings to fix president of Mexico for example
# TODO: Check Russia values

if __name__ == '__main__':
    create_ontology()
