# validate_brick_tag Function Usage

The `validate_brick_tag` function is now available as an MCP tool in the brick server. It validates whether a tag is predefined in the Brick ontology and suggests alternatives if not.

## Function Signature

```python
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
```

## Usage Examples

### Example 1: Valid Tag

```python
from rdf_mcp.servers.brick_server import validate_brick_tag

result = validate_brick_tag("Temperature")
print(result)
# Output:
# {
#     "valid": True,
#     "tag": "Temperature",
#     "suggestions": []
# }
```

### Example 2: Invalid Tag with Suggestions

```python
result = validate_brick_tag("Temprature")  # Typo
print(result)
# Output:
# {
#     "valid": False,
#     "tag": "Temprature",
#     "suggestions": ["Temperature", "Sensor", "Air", "Point", "Zone"]
#     # Suggestions are ordered by similarity using the SMASH distance algorithm
# }
```

### Example 3: Case-Sensitive Validation

```python
result = validate_brick_tag("air")  # Lowercase
print(result)
# Output:
# {
#     "valid": False,
#     "tag": "air",
#     "suggestions": ["Air", "Water", "Steam", "Alarm", "Fire"]
#     # "Air" is suggested as the most similar match
# }
```

## Related Functions

### get_all_brick_tags()

The `validate_brick_tag` function uses `get_all_brick_tags()` to retrieve all predefined tags from the Brick ontology:

```python
from rdf_mcp.servers.brick_server import get_all_brick_tags

all_tags = get_all_brick_tags()
print(f"Total tags: {len(all_tags)}")
# Returns a list of all valid Brick tags
```

### get_brick_tags(term: str)

To get tags associated with a specific Brick class or term:

```python
from rdf_mcp.servers.brick_server import get_brick_tags

tags = get_brick_tags("Zone_Air_Temperature_Sensor")
print(tags)
# Output: ["Zone", "Air", "Temperature", "Sensor"]
```

## MCP Tool Integration

The `validate_brick_tag` function is automatically exposed as an MCP tool with the `@mcp.tool()` decorator. This means it can be accessed through the MCP server interface.

### Starting the Brick Server

```bash
# Start the brick server
uv run brick-server
```

### Using the Tool via MCP

Once the server is running, you can call the `validate_brick_tag` tool through the MCP protocol to validate tags in your Brick models.

## Algorithm

The function uses the **SMASH distance algorithm** to find similar tags when the input is invalid. SMASH (Smart Matching Algorithm for String Similarity) is particularly effective at handling:

- Typos and misspellings
- Abbreviations
- Acronyms
- Case variations

This provides intelligent suggestions that help users find the correct tag even when they make mistakes or don't remember the exact tag name.

## Comparison with validate_brick_term

Both functions follow a similar pattern but validate different concepts:

| Feature | validate_brick_term | validate_brick_tag |
|---------|-------------------|-------------------|
| What it validates | Classes and properties | Tags |
| concept_type parameter | Yes (optional: "class" or "property") | No |
| Returns type field | Yes | No |
| Use case | Validating Brick class and property names | Validating tag names |

## Testing

The function is thoroughly tested in `tests/test_brick.py` with the following test cases:

- `test_get_all_brick_tags()` - Tests retrieving all tags from the ontology
- `test_validate_brick_tag_valid()` - Tests validation of valid tags
- `test_validate_brick_tag_invalid_with_suggestions()` - Tests suggestion generation for invalid tags
- `test_validate_brick_tag_case_sensitivity()` - Tests case-sensitive matching

Run tests with:

```bash
cd rdf-mcp
uv run pytest tests/test_brick.py -v