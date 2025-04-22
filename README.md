This repository contains code for [Model Context Protocol](https://modelcontextprotocol.io/introduction) servers supporting use of the Brick and 223P ontologies.

Make sure you have [uv](https://docs.astral.sh/uv/) installed. 

This project uses [Black](https://black.readthedocs.io/) for code formatting. To format your code, run:

```bash
uv run black .
```

There are 2 MCP servers in this repository.

## Brick MCP Server

Loads latest 1.4 Brick ontology from [https://brickschema.org/schema/1.4/Brick.ttl](https://brickschema.org/schema/1.4/Brick.ttl)

It defines these tools:
- `expand_abbreviation`: uses the [Smash](https://dl.acm.org/doi/abs/10.14778/3685800.3685830) algorithm to attempt expanding common abbreviations (e.g. `AHU`) into Brick classes (e.g. `Air_Handling_Unit`)
- `get_terms`: returns a list of Brick classes
- `get_properties`: returns a list of Brick properties and object types
- `get_possible_properties`: returns a list of Brick properties and object types that can be used with a given Brick class
- `get_definition_brick`: returns the definition of a Brick class as the [CBD](https://www.w3.org/submissions/CBD/) of the Brick class

## 223P MCP Server

Loads latest 223P from [https://open223.info/223p.ttl](https://open223.info/223p.ttl)
- `get_terms`: returns a list of S223 classes
- `get_properties`: returns a list of S223 properties (not object types)
- `get_possible_properties`: returns a list of S223 properties and object types that can be used with a given S223 class
- `get_definition_223p`: returns the definition of a S223 class as the [CBD](https://www.w3.org/submissions/CBD/) of the S223 class

## Running the servers

### Claude Desktop

Should be as simple as `uv run mcp install brick.py`, then open Claude Desktop and look at the tools settings to ensure everything is working. 

<details>
<summary>I had to make some edits for these to work on my own Claude Desktop installation. Here's what my `claude_desktop_config.json` file look like:</summary>

```json
{
  "mcpServers": {
    "BrickOntology": {
      "command": "/Users/gabe/.cargo/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "rdflib",
        "--with",
        "oxrdflib",
        "mcp",
        "run",
        "/Users/gabe/src/rdf-mcp/brick.py"
      ]
    },
    "S223Ontology": {
      "command": "/Users/gabe/.cargo/bin/uv",
      "args": [
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "rdflib",
        "--with",
        "oxrdflib",
        "mcp",
        "run",
        "/Users/gabe/src/rdf-mcp/s223.py"
      ]
    }
  }
}
```
</details>

### Pydantic

```python
import asyncio
from devtools import pprint
from pydantic_ai import Agent, capture_run_messages
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.mcp import MCPServerStdio

server = MCPServerStdio(
    "uv",
    args=[
        "run",
        "--with",
        "mcp[cli]",
        "--with",
        "rdflib",
        "--with",
        "oxrdflib",
        "mcp",
        "run",
        "brick.py"
    ],
)

model = OpenAIModel(
        model_name="gemma-3-27b-it-qat",
        # i'm using LM Studio here, but you could use any other provider that exposes
        # an OpenAI-like API
        provider=OpenAIProvider(base_url="http://localhost:1234/v1", api_key="lm_studio"),
    )

agent = Agent(
    model,
    mcp_servers=[server],
)

prompt = """Create a simple Brick model of a AHU box with 3 sensors: RAT, SAT and OAT. Also include a SF with a SF command

Look up definitions of concepts and their relationships to ensure you are building a valid Brick model.
Use the tool to determine what properties a term can have. Only use the predicates defined by the ontology.
Output a turtle file with the Brick model.
"""
async def main():
    with capture_run_messages() as messages:
        async with agent.run_mcp_servers():
            result = await agent.run(prompt)
    pprint(messages)
    print(result.output)

asyncio.run(main())
```
