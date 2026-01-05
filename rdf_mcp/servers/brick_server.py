from mcp.server.fastmcp import FastMCP
from rdflib import Graph, URIRef, Literal, Namespace, BRICK, RDFS, OWL, SKOS
from rdflib.term import Variable
from typing import List, Optional
from rdf_mcp.utils.smash import smash_distance
from rdf_mcp.utils import ClassEmbedder
import sys

mcp = FastMCP("GraphDemo", dependencies=["rdflib", "oxrdflib"])

S223 = Namespace("http://data.ashrae.org/standard223#")
ontology = Graph().parse("https://github.com/BrickSchema/Brick/releases/download/nightly/Brick.ttl", format="ttl")

emb = ClassEmbedder(
  ontology,
  [BRICK.Entity],
  [RDFS.label, SKOS.definition],
)


@mcp.tool()
def guess_class(text: str) -> list[tuple[str, float]]:
    """Guess the most likely Brick classes for a given text input"""
    results = emb.get(text, n=5)
    return [(uri, score) for uri, score in results]


@mcp.tool()
def expand_abbreviation(abbreviation: str) -> list[str]:
    """Expand an abbreviation to its full form using the Brick ontology"""
    # return the top 5 matches from the class dictionary
    closest_matches = sorted(
        CLASS_DICT.keys(), key=lambda x: smash_distance(abbreviation, x)
    )[:5]
    print(f"closest match to {abbreviation} is {closest_matches}", file=sys.stderr)
    return closest_matches


@mcp.tool()
def get_terms() -> list[str]:
    """Get all terms in the Brick ontology graph"""
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX s223: <http://data.ashrae.org/standard223#>
    SELECT ?class WHERE {
        { ?class a owl:Class }
        UNION
        { ?class a rdfs:Class }
        FILTER NOT EXISTS { ?class owl:deprecated true }
        FILTER NOT EXISTS { ?class brick:aliasOf ?alias }
    }"""
    results = ontology.query(query)
    # return [str(row[0]).split('#')[-1] for row in results]
    r = [str(row[0]).split("#")[-1] for row in results]
    return r


@mcp.tool()
def get_properties() -> list[str]:
    """Get all properties in the Brick ontology graph"""
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX s223: <http://data.ashrae.org/standard223#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?prop WHERE {
        { ?prop rdfs:subPropertyOf ?property }
        UNION
        { ?prop a owl:ObjectProperty }
        UNION
        { ?prop a owl:DataProperty }
    }"""
    results = ontology.query(query)
    # return [str(row[0]).split('#')[-1] for row in results]
    r = [str(row[0]).split("#")[-1] for row in results]
    return r


@mcp.tool()
def get_subclasses(parent_class: str) -> list[str]:
    """Get all classes that inherit from a specific parent class in the Brick ontology"""
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    SELECT DISTINCT ?subclass WHERE {
        ?subclass rdfs:subClassOf* ?parent .
        ?subclass a owl:Class .
        FILTER NOT EXISTS { ?subclass owl:deprecated true }
        FILTER (?subclass != ?parent)
    }"""
    results = ontology.query(query, initBindings={"parent": BRICK[parent_class]})
    return [str(row[0]).split("#")[-1] for row in results]


@mcp.tool()
def get_brick_tags(term: str) -> list[str]:
    """Get all tags associated with a Brick class or term"""
    query = """
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX tag: <https://brickschema.org/schema/BrickTag#>
    SELECT DISTINCT ?tag WHERE {
        ?term brick:hasAssociatedTag ?tag .
    }"""
    results = ontology.query(query, initBindings={"term": BRICK[term]})
    return [str(row[0]).split("#")[-1] for row in results]


@mcp.tool()
def get_possible_properties(class_: str) -> list[tuple[str, str]]:
    """Returns pairs of possible (property, object type) for a given brick class"""
    query = """
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX s223: <http://data.ashrae.org/standard223#>
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
    SELECT ?path ?type WHERE {
        ?from brick:aliasOf?/rdfs:subClassOf* ?fromp .
        { ?shape brick:aliasOf?/sh:targetClass ?fromp }
        UNION
        { ?fromp a sh:NodeShape . BIND(?fromp as ?shape) }
        ?shape sh:property ?prop .
        ?prop sh:path ?path .
         FILTER (!isBlank(?path))
        OPTIONAL { { ?prop sh:node ?type } UNION { ?prop sh:class ?type } }
    }
    """
    res = list(ontology.query(query, initBindings={"from": BRICK[class_]}).bindings)
    print(res, file=sys.stderr)
    path_object_pairs = set([(r[Variable("path")], r[Variable("type")]) for r in res])
    return list(path_object_pairs)


@mcp.tool()
def get_definition_brick(class_: str) -> str:
    """Get the definition of cyber-physical concepts from the Brick ontology."""
    return ontology.cbd(BRICK[class_]).serialize(format="turtle")


@mcp.resource("rdf://describe/{term}")
def get_definition(term: str) -> str:
    """Get the definition of cyber-physical concepts like sensors from the Brick ontology."""
    return ontology.cbd(BRICK[term]).serialize(format="turtle")


# build a dictionary of all classes in the Brick ontology
def build_class_dict() -> dict[str, str]:
    """Build a dictionary of all classes in the Brick ontology"""
    class_dict = {}
    for term in get_terms():
        class_uri = BRICK[term]
        label = ontology.value(subject=class_uri, predicate=RDFS.label)
        if label:
            label = str(label)
        else:
            label = str(term).split("#")[-1]
        class_dict[label] = term
    return class_dict


# Initialize CLASS_DICT as an empty dict so it can be patched in tests
CLASS_DICT = {}

# TODO: add a "most likely class" tool


def main():
    global CLASS_DICT
    CLASS_DICT = build_class_dict()
    print(f"{CLASS_DICT}", file=sys.stderr)
    print("mcp ready", file=sys.stderr)
    mcp.run()


if __name__ == "__main__":
    main()
