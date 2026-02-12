#!/usr/bin/env python3
"""Tests for the brick module."""

import pytest
import os
import sys
from unittest.mock import patch, MagicMock
import tempfile
from rdflib import Graph, URIRef, Namespace, BRICK, RDFS
from rdf_mcp.servers import brick_server as brick


class TestBrickModule:
    """Test suite for the brick module."""

    @pytest.fixture
    def setup_module_path(self):
        """Set up the module path for importing brick."""
        # Add the parent directory to sys.path so we can import brick
        parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        if parent_dir not in sys.path:
            sys.path.insert(0, parent_dir)
        return parent_dir


@patch("rdf_mcp.servers.brick_server.ontology")
def test_expand_abbreviation(mock_ontology):
    """Test expand_abbreviation function."""
    from rdf_mcp.servers.brick_server import expand_abbreviation, CLASS_DICT
    from unittest.mock import patch

    with patch.dict(
        "rdf_mcp.servers.brick_server.CLASS_DICT",
        {"AHU": "Air_Handler_Unit", "VAV": "Variable_Air_Volume"},
    ):
        # Test AHU abbreviation
        result = expand_abbreviation("AHU")
        assert len(result) <= 5  # Should return no more than 5 results
        # Test that mock CLASS_DICT is used
        assert result  # Should return a non-empty list


@patch("rdf_mcp.servers.brick_server.ontology")
def test_get_terms(mock_ontology):
    """Test get_terms function."""
    mock_ontology.query.return_value = [
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Air_Temperature_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#CO2_Level_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Methane_Level_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#PM2.5_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Building"
            ),
        ),
        (MagicMock(__str__=lambda self: "https://brickschema.org/schema/Brick#Floor"),),
        (MagicMock(__str__=lambda self: "https://brickschema.org/schema/Brick#Room"),),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Office_Kitchen"
            ),
        ),
        (MagicMock(__str__=lambda self: "https://brickschema.org/schema/Brick#Site"),),
    ]
    from rdf_mcp.servers.brick_server import get_terms

    result = get_terms()

    assert isinstance(result, list)
    assert "Air_Temperature_Sensor" in result
    assert "CO2_Level_Sensor" in result
    assert "Methane_Level_Sensor" in result
    assert "PM2.5_Sensor" in result
    assert "Building" in result
    assert "Floor" in result
    assert "Room" in result
    assert "Office_Kitchen" in result
    assert "Site" in result


@patch("rdf_mcp.servers.brick_server.ontology")
def test_get_properties(mock_ontology):
    """Test get_properties function."""
    mock_ontology.query.return_value = [
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#hasUnit"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#isPointOf"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#hasPart"
            ),
        ),
        (MagicMock(__str__=lambda self: "https://brickschema.org/schema/Brick#area"),),
        (MagicMock(__str__=lambda self: "https://brickschema.org/schema/Brick#value"),),
    ]
    from rdf_mcp.servers.brick_server import get_properties

    result = get_properties()

    assert isinstance(result, list)
    assert "hasUnit" in result
    assert "isPointOf" in result
    assert "hasPart" in result
    assert "area" in result
    assert "value" in result


@patch("rdf_mcp.servers.brick_server.ontology")
def test_get_subclasses(mock_ontology):
    """Test get_subclasses function."""
    # Mock query results for subclasses of Sensor
    mock_ontology.query.return_value = [
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Temperature_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Air_Temperature_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Zone_Air_Temperature_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#CO2_Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/Brick#Humidity_Sensor"
            ),
        ),
    ]
    from rdf_mcp.servers.brick_server import get_subclasses

    result = get_subclasses("Sensor")

    # Verify it's a list
    assert isinstance(result, list)

    # Verify it contains expected subclasses
    assert "Temperature_Sensor" in result
    assert "Air_Temperature_Sensor" in result
    assert "Zone_Air_Temperature_Sensor" in result
    assert "CO2_Sensor" in result
    assert "Humidity_Sensor" in result

    # Verify the parent class was passed correctly in the query
    mock_ontology.query.assert_called_once()
    call_args = mock_ontology.query.call_args
    assert "parent" in call_args.kwargs.get("initBindings", {})

    # Test with a class that has no subclasses
    mock_ontology.reset_mock()
    mock_ontology.query.return_value = []

    result = get_subclasses("LeafClass")
    assert isinstance(result, list)
    assert len(result) == 0


@patch("rdf_mcp.servers.brick_server.ontology")
def test_get_brick_tags(mock_ontology):
    """Test get_brick_tags function."""
    # Mock query results for tags of Zone_Air_Temperature_Sensor
    mock_ontology.query.return_value = [
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Zone"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Air"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Temperature"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Sensor"
            ),
        ),
    ]
    from rdf_mcp.servers.brick_server import get_brick_tags

    result = get_brick_tags("Zone_Air_Temperature_Sensor")

    # Verify it's a list
    assert isinstance(result, list)

    # Verify it contains expected tags
    assert "Zone" in result
    assert "Air" in result
    assert "Temperature" in result
    assert "Sensor" in result

    # Verify the term was passed correctly in the query
    mock_ontology.query.assert_called_once()
    call_args = mock_ontology.query.call_args
    assert "term" in call_args.kwargs.get("initBindings", {})

    # Test with a class that has no tags
    mock_ontology.reset_mock()
    mock_ontology.query.return_value = []

    result = get_brick_tags("ClassWithoutTags")
    assert isinstance(result, list)
    assert len(result) == 0


@patch("rdf_mcp.servers.brick_server.get_terms")
@patch("rdf_mcp.servers.brick_server.get_properties")
def test_validate_brick_term_valid_class(mock_get_properties, mock_get_terms):
    """Test validate_brick_term with a valid class."""
    mock_get_terms.return_value = [
        "Air_Handling_Unit",
        "Temperature_Sensor",
        "Zone",
    ]
    mock_get_properties.return_value = ["hasPoint", "hasPart", "feeds"]

    from rdf_mcp.servers.brick_server import validate_brick_term

    result = validate_brick_term("Air_Handling_Unit")

    assert isinstance(result, dict)
    assert result["valid"] is True
    assert result["type"] == "class"
    assert result["term"] == "Air_Handling_Unit"
    assert result["suggestions"] == []


@patch("rdf_mcp.servers.brick_server.get_terms")
@patch("rdf_mcp.servers.brick_server.get_properties")
def test_validate_brick_term_valid_property(mock_get_properties, mock_get_terms):
    """Test validate_brick_term with a valid property."""
    mock_get_terms.return_value = ["Air_Handling_Unit", "Temperature_Sensor"]
    mock_get_properties.return_value = ["hasPoint", "hasPart", "feeds"]

    from rdf_mcp.servers.brick_server import validate_brick_term

    result = validate_brick_term("hasPoint")

    assert isinstance(result, dict)
    assert result["valid"] is True
    assert result["type"] == "property"
    assert result["term"] == "hasPoint"
    assert result["suggestions"] == []


@patch("rdf_mcp.servers.brick_server.get_terms")
@patch("rdf_mcp.servers.brick_server.get_properties")
def test_validate_brick_term_invalid_with_suggestions(
    mock_get_properties, mock_get_terms
):
    """Test validate_brick_term with an invalid term, should return suggestions."""
    mock_get_terms.return_value = [
        "Air_Handling_Unit",
        "Air_Handler",
        "Air_Temperature_Sensor",
        "Zone",
    ]
    mock_get_properties.return_value = ["hasPoint", "hasPart", "feeds"]

    from rdf_mcp.servers.brick_server import validate_brick_term

    result = validate_brick_term("AirHandlingUnit")  # Typo: should be Air_Handling_Unit

    assert isinstance(result, dict)
    assert result["valid"] is False
    assert result["type"] == "unknown"
    assert result["term"] == "AirHandlingUnit"
    assert isinstance(result["suggestions"], list)
    assert len(result["suggestions"]) > 0
    # Suggestions should have structure with "term" and "type" keys
    if result["suggestions"]:
        assert "term" in result["suggestions"][0]
        assert "type" in result["suggestions"][0]


@patch("rdf_mcp.servers.brick_server.get_terms")
@patch("rdf_mcp.servers.brick_server.get_properties")
def test_validate_brick_term_with_type_filter(mock_get_properties, mock_get_terms):
    """Test validate_brick_term with concept_type filter."""
    mock_get_terms.return_value = ["Air_Handling_Unit", "Temperature_Sensor"]
    mock_get_properties.return_value = ["hasPoint", "hasPart"]

    from rdf_mcp.servers.brick_server import validate_brick_term

    # Test with concept_type="class"
    result = validate_brick_term("Air_Handling_Unit", concept_type="class")
    assert result["valid"] is True
    assert result["type"] == "class"

    # Test with concept_type="property"
    result = validate_brick_term("hasPoint", concept_type="property")
    assert result["valid"] is True
    assert result["type"] == "property"

    # Test invalid term with concept_type="class" - should only suggest classes
    result = validate_brick_term("InvalidTerm", concept_type="class")
    assert result["valid"] is False
    if result["suggestions"]:
        # All suggestions should be classes
        assert all(s["type"] == "class" for s in result["suggestions"])


@patch("rdf_mcp.servers.brick_server.ontology")
def test_get_all_brick_tags(mock_ontology):
    """Test get_all_brick_tags function."""
    # Mock query results for all tags in the ontology
    mock_ontology.query.return_value = [
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Air"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Temperature"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Sensor"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Zone"
            ),
        ),
        (
            MagicMock(
                __str__=lambda self: "https://brickschema.org/schema/BrickTag#Point"
            ),
        ),
    ]
    from rdf_mcp.servers.brick_server import get_all_brick_tags

    result = get_all_brick_tags()

    # Verify it's a list
    assert isinstance(result, list)

    # Verify it contains expected tags
    assert "Air" in result
    assert "Temperature" in result
    assert "Sensor" in result
    assert "Zone" in result
    assert "Point" in result

    # Verify the query was called
    mock_ontology.query.assert_called_once()


@patch("rdf_mcp.servers.brick_server.get_all_brick_tags")
def test_validate_brick_tag_valid(mock_get_all_brick_tags):
    """Test validate_brick_tag with a valid tag."""
    mock_get_all_brick_tags.return_value = [
        "Air",
        "Temperature",
        "Sensor",
        "Zone",
        "Point",
        "Command",
        "Status",
    ]

    from rdf_mcp.servers.brick_server import validate_brick_tag

    result = validate_brick_tag("Temperature")

    assert isinstance(result, dict)
    assert result["valid"] is True
    assert result["tag"] == "Temperature"
    assert result["suggestions"] == []


@patch("rdf_mcp.servers.brick_server.get_all_brick_tags")
def test_validate_brick_tag_invalid_with_suggestions(mock_get_all_brick_tags):
    """Test validate_brick_tag with an invalid tag, should return suggestions."""
    mock_get_all_brick_tags.return_value = [
        "Air",
        "Temperature",
        "Sensor",
        "Zone",
        "Point",
        "Command",
        "Status",
        "Setpoint",
    ]

    from rdf_mcp.servers.brick_server import validate_brick_tag

    result = validate_brick_tag("Temprature")  # Typo: should be Temperature

    assert isinstance(result, dict)
    assert result["valid"] is False
    assert result["tag"] == "Temprature"
    assert isinstance(result["suggestions"], list)
    assert len(result["suggestions"]) > 0
    assert len(result["suggestions"]) <= 5  # Should suggest at most 5 tags
    # Temperature should be in the suggestions as it's the closest match
    assert "Temperature" in result["suggestions"]


@patch("rdf_mcp.servers.brick_server.get_all_brick_tags")
def test_validate_brick_tag_case_sensitivity(mock_get_all_brick_tags):
    """Test validate_brick_tag handles case variations."""
    mock_get_all_brick_tags.return_value = [
        "Air",
        "Temperature",
        "Sensor",
        "Zone",
    ]

    from rdf_mcp.servers.brick_server import validate_brick_tag

    # Test exact match
    result = validate_brick_tag("Air")
    assert result["valid"] is True

    # Test case variation - should be invalid since tags are case-sensitive
    result = validate_brick_tag("air")
    assert result["valid"] is False
    assert isinstance(result["suggestions"], list)
    # "Air" should be suggested as it's similar
    assert "Air" in result["suggestions"]
