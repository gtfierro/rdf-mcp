from mcp.server.fastmcp import FastMCP
from rdflib import Graph, URIRef, Literal, Namespace, BRICK, RDFS
from rdflib.term import Variable
from typing import List, Optional
from rdf_mcp.utils.smash import smash_distance
import sys

mcp = FastMCP("GraphDemo", dependencies=["rdflib", "oxrdflib"])

S223 = Namespace("http://data.ashrae.org/standard223#")
ontology = Graph().parse("https://brickschema.org/schema/1.4/Brick.ttl")


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
def get_all_brick_tags() -> list[str]:
    """Get all predefined tags in the Brick ontology"""
    query = """
    PREFIX brick: <https://brickschema.org/schema/Brick#>
    PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
    PREFIX tag: <https://brickschema.org/schema/BrickTag#>
    PREFIX owl: <http://www.w3.org/2002/07/owl#>
    SELECT DISTINCT ?tag WHERE {
        ?tag a brick:Tag .
        FILTER NOT EXISTS { ?tag owl:deprecated true }
    }"""
    results = ontology.query(query)
    return [str(row[0]).split("#")[-1] for row in results]


@mcp.tool()
def validate_brick_term(term: str, concept_type: Optional[str] = None) -> dict:
    """
    Validate if a term is a valid Brick concept and suggest alternatives if not.

    Args:
        term: The term to validate (e.g., "Air_Handling_Unit", "hasPoint")
        concept_type: Optional filter - "class" or "property". If None, checks both.

    Returns:
        Dictionary with validation results and suggestions:
        - valid: bool - whether the term is valid
        - type: str - "class", "property", or "unknown"
        - term: str - the input term
        - suggestions: list - top 5 similar terms if not valid (empty if valid)
    """
    result = {
        "valid": False,
        "type": "unknown",
        "term": term,
        "suggestions": []
    }

    # Check if it's a valid class
    if concept_type is None or concept_type == "class":
        all_classes = get_terms()
        if term in all_classes:
            result["valid"] = True
            result["type"] = "class"
            return result

    # Check if it's a valid property
    if concept_type is None or concept_type == "property":
        all_properties = get_properties()
        if term in all_properties:
            result["valid"] = True
            result["type"] = "property"
            return result

    # If not valid, suggest similar terms using SMASH algorithm
    if not result["valid"]:
        if concept_type == "class" or concept_type is None:
            # Search in classes
            all_classes = get_terms()
            class_suggestions = sorted(
                all_classes,
                key=lambda x: smash_distance(term, x)
            )[:5]
            result["suggestions"].extend([{"term": s, "type": "class"} for s in class_suggestions])

        if concept_type == "property" or concept_type is None:
            # Search in properties
            all_properties = get_properties()
            property_suggestions = sorted(
                all_properties,
                key=lambda x: smash_distance(term, x)
            )[:5]
            result["suggestions"].extend([{"term": s, "type": "property"} for s in property_suggestions])

        # If checking both types, limit to top 5 overall suggestions
        if concept_type is None and len(result["suggestions"]) > 5:
            # Sort all suggestions by SMASH distance and keep top 5
            result["suggestions"] = sorted(
                result["suggestions"],
                key=lambda x: smash_distance(term, x["term"])
            )[:5]

    print(f"Validation result for '{term}': {result}", file=sys.stderr)
    return result


@mcp.tool()
def validate_brick_tag(tag: str) -> dict:
    """
    Validate if a tag is predefined in the Brick ontology and suggest alternatives if not.

    Args:
        tag: The tag to validate (e.g., "Air", "Sensor", "Temperature")

    Returns:
        Dictionary with validation results and suggestions:
        - valid: bool - whether the tag is valid
        - tag: str - the input tag
        - suggestions: list - top 5 similar tags if not valid (empty if valid)
    """
    result = {
        "valid": False,
        "tag": tag,
        "suggestions": []
    }

    # Get all valid tags
    all_tags = get_all_brick_tags()
    
    # Check if the tag is valid
    if tag in all_tags:
        result["valid"] = True
        return result

    # If not valid, suggest similar tags using SMASH algorithm
    tag_suggestions = sorted(
        all_tags,
        key=lambda x: smash_distance(tag, x)
    )[:5]
    result["suggestions"] = tag_suggestions

    print(f"Validation result for tag '{tag}': {result}", file=sys.stderr)
    return result


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
