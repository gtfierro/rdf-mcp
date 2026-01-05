from __future__ import annotations

import asyncio
import json
import os
import sys
from collections import Counter
from contextlib import AsyncExitStack
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import gradio as gr
import urllib.error
import urllib.request
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from rdflib import Graph, URIRef
from rdflib.namespace import RDF

REPO_ROOT = Path(__file__).resolve().parent
DEFAULT_LMSTUDIO_MODEL = "openai/gpt-oss-20b"
DEFAULT_LMSTUDIO_BASE_URL = "http://localhost:1234/v1"
MAX_TOOL_ROUNDS = 3
SERVER_OPTIONS = {
    "Brick": "brick-server",
    "S223": "s223-server",
    "Watr": "watr-server",
}


@dataclass
class AppState:
    graph: Graph | None = None
    graph_path: str | None = None
    graph_summary: str | None = None
    prefixes: str | None = None
    server_choice: str | None = "watr-server"
    mcp_session: ClientSession | None = None
    mcp_exit_stack: AsyncExitStack | None = None
    mcp_tools: list[dict[str, Any]] = field(default_factory=list)


def _shorten_uri(graph: Graph, uri: Any) -> str:
    if uri is None:
        return ""
    try:
        return graph.namespace_manager.normalizeUri(uri)
    except Exception:
        return str(uri)


def _graph_summary(graph: Graph) -> str:
    triple_count = len(graph)
    type_counts = Counter(str(o) for o in graph.objects(None, RDF.type))
    top_types = ", ".join(
        f"{_shorten_uri(graph, URIRef(t))} ({c})"
        for t, c in type_counts.most_common(8)
    )
    if not top_types:
        top_types = "none"
    return f"Triples: {triple_count}. Top rdf:type values: {top_types}."


def _graph_prefixes(graph: Graph) -> str:
    lines = []
    for prefix, ns in graph.namespace_manager.namespaces():
        if prefix:
            lines.append(f"PREFIX {prefix}: <{ns}>")
    return "\n".join(lines[:25])


def _detect_server(graph: Graph) -> str:
    for _, ns in graph.namespace_manager.namespaces():
        if "brickschema.org/schema/Brick" in str(ns):
            return "brick-server"
    return "watr-server"


async def _cleanup_mcp(state: AppState) -> None:
    if state.mcp_exit_stack is not None:
        await state.mcp_exit_stack.aclose()
    state.mcp_session = None
    state.mcp_exit_stack = None
    state.mcp_tools = []


async def _start_mcp_server(server_module: str) -> tuple[ClientSession, AsyncExitStack, list[dict[str, Any]]]:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT)
    server_params = StdioServerParameters(
        command=sys.executable,
        args=["-m", server_module],
        env=env,
    )
    exit_stack = AsyncExitStack()
    stdio_transport = await exit_stack.enter_async_context(stdio_client(server_params))
    stdio, write = stdio_transport
    session = await exit_stack.enter_async_context(ClientSession(stdio, write))
    await session.initialize()
    tools_response = await session.list_tools()
    tools = [
        {
            "type": "function",
            "function": {
                "name": tool.name,
                "description": tool.description or "",
                "parameters": tool.inputSchema or {"type": "object", "properties": {}},
            },
        }
        for tool in tools_response.tools
    ]
    return session, exit_stack, tools


async def _ensure_mcp(state: AppState) -> None:
    if state.mcp_session is not None:
        return
    if state.server_choice == "s223-server":
        module = "rdf_mcp.servers.s223_server"
    elif state.server_choice == "watr-server":
        module = "rdf_mcp.servers.watr_server"
    else:
        module = "rdf_mcp.servers.brick_server"
    session, exit_stack, tools = await _start_mcp_server(module)
    state.mcp_session = session
    state.mcp_exit_stack = exit_stack
    state.mcp_tools = tools


def _local_tools() -> list[dict[str, Any]]:
    return [
        {
            "type": "function",
            "function": {
                "name": "sparql_query",
                "description": "Run a SPARQL query against the uploaded model graph.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "A SPARQL query (SELECT/ASK/CONSTRUCT/DESCRIBE).",
                        }
                    },
                    "required": ["query"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "describe_resource",
                "description": "Return the CBD (concise bounded description) of a resource.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "term": {
                            "type": "string",
                            "description": "IRI or CURIE (e.g., brick:Temperature_Sensor).",
                        }
                    },
                    "required": ["term"],
                },
            },
        },
    ]


def _format_query_results(graph: Graph, results: Any) -> str:
    result_type = getattr(results, "type", "").upper()
    if result_type == "ASK":
        return f"ASK result: {bool(results)}"
    if result_type in {"CONSTRUCT", "DESCRIBE"}:
        return results.serialize(format="turtle")
    if result_type == "SELECT":
        rows = []
        headers = [str(v) for v in results.vars]
        rows.append("\t".join(headers))
        for row in results:
            rows.append("\t".join(_shorten_uri(graph, value) for value in row))
        return "\n".join(rows) if rows else "No results."
    return str(results)


def _expand_term(graph: Graph, term: str) -> str:
    if term.startswith("http://") or term.startswith("https://"):
        return term
    try:
        return str(graph.namespace_manager.expand_curie(term, False))
    except Exception:
        return term


def _run_local_tool(name: str, args: dict[str, Any], state: AppState) -> str:
    if state.graph is None:
        return "No model graph loaded."
    if name == "sparql_query":
        query = args.get("query", "")
        if not query.strip():
            return "SPARQL query is empty."
        try:
            results = state.graph.query(query)
        except Exception as exc:
            return f"SPARQL error: {exc}"
        return _format_query_results(state.graph, results)
    if name == "describe_resource":
        term = args.get("term", "")
        if not term:
            return "Term is empty."
        expanded = _expand_term(state.graph, term)
        try:
            return state.graph.cbd(URIRef(expanded)).serialize(format="turtle")
        except Exception as exc:
            return f"Describe error: {exc}"
    return f"Unknown local tool: {name}"


def _tool_call_name(tool_call: Any) -> str:
    if isinstance(tool_call, dict):
        return tool_call.get("function", {}).get("name", "")
    func = getattr(tool_call, "function", None)
    if func is None:
        return ""
    return getattr(func, "name", "")


def _tool_call_args(tool_call: Any) -> dict[str, Any]:
    if isinstance(tool_call, dict):
        args = tool_call.get("function", {}).get("arguments", {})
    else:
        func = getattr(tool_call, "function", None)
        args = getattr(func, "arguments", {}) if func else {}
    if isinstance(args, str):
        try:
            return json.loads(args)
        except json.JSONDecodeError:
            return {}
    if isinstance(args, dict):
        return args
    return {}


def _tool_call_id(tool_call: Any, fallback: str) -> str:
    if isinstance(tool_call, dict):
        return tool_call.get("id") or fallback
    return getattr(tool_call, "id", None) or fallback


def _format_mcp_result(result: Any) -> str:
    content = getattr(result, "content", None)
    if content is None:
        return str(result)
    parts = []
    for item in content:
        text = getattr(item, "text", None)
        if text is not None:
            parts.append(text)
        else:
            parts.append(str(item))
    return "\n".join(parts) if parts else str(result)


def _system_prompt(state: AppState) -> str:
    summary = state.graph_summary or "No summary available."
    prefixes = state.prefixes or ""
    return (
        "You are an assistant for an RDF model uploaded by the user. The model represents a cyber-physical system like a building, HVAC system, water treatment plant or train, or similar."
        "You are knowledgeable about RDF, ontologies, and SPARQL. And you can make appropriate and useful suggestions and guesses as to what the user is asking based on a deep domain knowledge."
        "Verify terms exist in the model or ontology before using them; do not make up terms or properties. "
        "When a user asks about 'properties', determine from context if they mean an rdf property (i.e. edge) or a Property instance in the model."
        "Use tools to answer questions precisely.\n\n"
        f"Model summary: {summary}\n\n"
        "Use `sparql_query` to answer questions about instances in the model. "
        "Use `describe_resource` for a concise bounded description of an entity. "
        "Use MCP tools for ontology concepts, properties, and definitions.\n\n"
        "Common prefixes (if needed in SPARQL):\n"
        f"{prefixes}"
    )


async def _ensure_tools(state: AppState) -> list[dict[str, Any]]:
    await _ensure_mcp(state)
    return _local_tools() + state.mcp_tools


def _lmstudio_chat(
    base_url: str,
    api_key: str | None,
    model: str,
    messages: list[dict[str, Any]],
    tools: list[dict[str, Any]],
) -> dict[str, Any]:
    endpoint = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": messages,
        "tools": tools,
        "tool_choice": "auto",
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    data = json.dumps(payload).encode("utf-8")
    request = urllib.request.Request(endpoint, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=120) as response:
            body = response.read().decode("utf-8")
    except urllib.error.URLError as exc:
        raise RuntimeError(f"LM Studio request failed: {exc}") from exc
    parsed = json.loads(body)
    choices = parsed.get("choices") or []
    if not choices:
        raise RuntimeError(f"LM Studio returned no choices: {parsed}")
    return choices[0].get("message", {})


async def _chat_lmstudio(
    message: str,
    history: list[dict[str, str]],
    state: AppState,
    model_name: str,
    base_url: str,
    api_key: str,
) -> str:
    if state.graph is None:
        return "Upload a .ttl model first."
    await _ensure_mcp(state)
    model = model_name.strip() or DEFAULT_LMSTUDIO_MODEL
    base_url = base_url.strip() or DEFAULT_LMSTUDIO_BASE_URL

    messages: list[dict[str, Any]] = [{"role": "system", "content": _system_prompt(state)}]
    for item in history:
        if isinstance(item, dict) and item.get("role") and item.get("content") is not None:
            messages.append({"role": item["role"], "content": item["content"]})
    messages.append({"role": "user", "content": message})

    tools = _local_tools() + state.mcp_tools

    for _ in range(MAX_TOOL_ROUNDS):
        try:
            msg = await asyncio.to_thread(
                _lmstudio_chat, base_url, api_key, model, messages, tools
            )
        except Exception as exc:
            return f"LM Studio error: {exc}"
        content = msg.get("content") or ""
        tool_calls = msg.get("tool_calls") or []
        assistant_message: dict[str, Any] = {"role": "assistant", "content": content}
        if tool_calls:
            assistant_message["tool_calls"] = tool_calls
        messages.append(assistant_message)
        if not tool_calls:
            return content or "No response from model."
        for idx, tool_call in enumerate(tool_calls):
            tool_name = _tool_call_name(tool_call)
            tool_args = _tool_call_args(tool_call)
            tool_call_id = _tool_call_id(tool_call, f"call_{idx}")
            if tool_name in {"sparql_query", "describe_resource"}:
                result_text = _run_local_tool(tool_name, tool_args, state)
            else:
                try:
                    result = await state.mcp_session.call_tool(tool_name, tool_args)
                except Exception as exc:
                    result_text = f"MCP tool error ({tool_name}): {exc}"
                else:
                    result_text = _format_mcp_result(result)
            messages.append(
                {
                    "role": "tool",
                    "tool_call_id": tool_call_id,
                    "content": result_text,
                }
            )
    return "Tool call loop exceeded; try a more specific question."


async def _handle_upload(
    file_path: str | None, state: AppState
) -> tuple[AppState, str]:
    if not file_path:
        return state, "No file selected."
    if not file_path.endswith(".ttl"):
        return state, "Please upload a .ttl file."
    await _cleanup_mcp(state)
    graph = Graph()
    try:
        graph.parse(file_path, format="turtle")
    except Exception as exc:
        return state, f"Failed to parse Turtle file: {exc}"
    state.graph = graph
    state.graph_path = file_path
    state.graph_summary = _graph_summary(graph)
    state.prefixes = _graph_prefixes(graph)
    if not state.server_choice:
        state.server_choice = _detect_server(graph)
    status = f"Loaded {Path(file_path).name}. {state.graph_summary}"
    return state, status


async def _chat_submit(
    message: str,
    history: list[dict[str, str]],
    state: AppState,
    model_name: str,
    base_url: str,
    api_key: str,
) -> tuple[str, list[dict[str, str]], AppState]:
    if not message.strip():
        return "", history, state
    response = await _chat_lmstudio(
        message, history, state, model_name, base_url, api_key
    )
    history = history + [
        {"role": "user", "content": message},
        {"role": "assistant", "content": response},
    ]
    return "", history, state


def build_demo() -> gr.Blocks:
    with gr.Blocks(title="RDF MCP Gradio Demo") as demo:
        gr.Markdown(
            "# RDF MCP Demo\n"
            "Upload a Turtle (.ttl) model, then chat about it. The app registers the selected MCP "
            "server and exposes its tools to the LLM."
        )

        state = gr.State(AppState())

        with gr.Row():
            file_input = gr.File(
                label="Upload .ttl model",
                file_types=[".ttl"],
                type="filepath",
            )
            model_name = gr.Textbox(
                label="LM Studio model",
                value=DEFAULT_LMSTUDIO_MODEL,
            )
            base_url = gr.Textbox(
                label="LM Studio base URL",
                value=DEFAULT_LMSTUDIO_BASE_URL,
            )
            api_key = gr.Textbox(
                label="LM Studio API key (optional)",
                type="password",
            )
            server_choice = gr.Dropdown(
                label="MCP server",
                choices=list(SERVER_OPTIONS.keys()),
                value="Watr",
            )

        status = gr.Markdown("No model loaded.")

        chatbot = gr.Chatbot(label="Model chat")
        user_input = gr.Textbox(label="Question", placeholder="Ask about the model...")
        send_button = gr.Button("Send")
        clear_button = gr.Button("Clear chat")

        async def _set_server_choice(choice: str, state: AppState) -> AppState:
            next_choice = SERVER_OPTIONS.get(choice, "watr-server")
            if state.server_choice != next_choice:
                await _cleanup_mcp(state)
                state.server_choice = next_choice
            return state

        server_choice.change(
            _set_server_choice,
            inputs=[server_choice, state],
            outputs=[state],
        )

        file_input.change(
            _handle_upload,
            inputs=[file_input, state],
            outputs=[state, status],
        )

        user_input.submit(
            _chat_submit,
            inputs=[user_input, chatbot, state, model_name, base_url, api_key],
            outputs=[user_input, chatbot, state],
        )
        send_button.click(
            _chat_submit,
            inputs=[user_input, chatbot, state, model_name, base_url, api_key],
            outputs=[user_input, chatbot, state],
        )
        def _clear_chat(
            existing_state: AppState,
        ) -> tuple[list[dict[str, str]], AppState]:
            return [], existing_state

        clear_button.click(
            _clear_chat,
            inputs=[state],
            outputs=[chatbot, state],
        )

    return demo


if __name__ == "__main__":
    demo_app = build_demo()
    demo_app.queue()
    demo_app.launch()
