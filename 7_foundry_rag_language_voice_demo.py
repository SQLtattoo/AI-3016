#!/usr/bin/env python3
"""
AI-3016 Demo 7: Foundry Agent with RAG, Azure Language MCP, and Voice Live

The same file has two roles:
  * Normal mode runs a privacy-aware banking agent with typed or live voice I/O.
  * --serve-language-mcp starts a local MCP server that wraps Azure AI Language
    PII redaction. The normal mode starts this server as a child process.

Raw customer text is sent to the redaction tool before it is logged, searched,
or included in the typed agent prompt. Voice Live receives the source audio as
part of its real-time session, but this application never prints raw transcripts.

Examples:
    python 7_foundry_rag_language_voice_demo.py
    python 7_foundry_rag_language_voice_demo.py --voice
"""

import argparse
import asyncio
import base64
import json
import os
import sys
import threading
from array import array
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator, Dict, List, Optional
from urllib.parse import urlsplit

from azure.core.credentials import AzureKeyCredential
from azure.identity import DefaultAzureCredential
from azure.search.documents import SearchClient
from azure.search.documents.models import VectorizedQuery
from dotenv import load_dotenv

from azure_openai_auth import clean_env_value, create_azure_openai_client, has_usable_secret


load_dotenv()

SCRIPT_PATH = Path(__file__).resolve()
VOICE_SAMPLE_RATE = 24_000
VOICE_CHUNK_SIZE = 1_200
VOICE_CHANNELS = 1
VOICE_NOISE_GATE_THRESHOLD = int(
    os.getenv("VOICE_LIVE_NOISE_GATE_THRESHOLD", "500")
)
VOICE_NOISE_GATE_RELEASE_CHUNKS = 3

SYSTEM_PROMPT = """You are Aria, a privacy-aware banking support agent.
Use only the supplied bank-policy evidence. Do not repeat or infer personal data.
Give general information, cite source titles, and never request passwords, PINs,
full account numbers, or full government identifiers. If evidence is insufficient,
say so and recommend the appropriate customer-service channel."""


def require_env(name: str) -> str:
    value = clean_env_value(name)
    if not value:
        raise RuntimeError(f"Missing required environment variable: {name}")
    return value


def resolve_foundry_service_endpoint(name: str, domain: str) -> str:
    explicit_endpoint = clean_env_value(name)
    if explicit_endpoint:
        return explicit_endpoint

    foundry_endpoint = clean_env_value("AZURE_OPENAI_ENDPOINT") or clean_env_value(
        "ENDPOINT_URL"
    )
    hostname = urlsplit(foundry_endpoint).hostname
    if not hostname:
        raise RuntimeError(
            f"Missing required environment variable: {name} "
            "(or AZURE_OPENAI_ENDPOINT for automatic discovery)"
        )
    resource_name = hostname.split(".", maxsplit=1)[0]
    return f"https://{resource_name}.{domain}/"


def create_default_credential() -> DefaultAzureCredential:
    return DefaultAzureCredential(
        exclude_environment_credential=True,
        exclude_managed_identity_credential=True,
    )


def create_language_client():
    try:
        from azure.ai.textanalytics import TextAnalyticsClient
    except ImportError as exc:
        raise RuntimeError(
            "Azure Language support is not installed. Run "
            "`pip install -r requirements-optional.txt`."
        ) from exc

    endpoint = resolve_foundry_service_endpoint(
        "AZURE_LANGUAGE_ENDPOINT", "cognitiveservices.azure.com"
    )
    key = clean_env_value("AZURE_LANGUAGE_KEY")
    credential = AzureKeyCredential(key) if has_usable_secret(key) else create_default_credential()
    return TextAnalyticsClient(endpoint=endpoint, credential=credential)


def run_language_mcp_server() -> None:
    """Expose Azure AI Language PII redaction as a local stdio MCP tool."""
    try:
        from mcp.server.fastmcp import FastMCP
    except ImportError as exc:
        raise RuntimeError(
            "MCP support is not installed. Run `pip install -r requirements-optional.txt`."
        ) from exc

    language_client = create_language_client()
    server = FastMCP("azure-language-pii")

    @server.tool()
    def redact_customer_text(text: str, language: str = "en") -> Dict[str, Any]:
        """Redact PII from customer text before downstream processing."""
        result = language_client.recognize_pii_entities([text], language=language)[0]
        if result.is_error:
            raise RuntimeError(f"Azure Language PII analysis failed: {result.error.message}")

        return {
            "redacted_text": result.redacted_text,
            "entity_categories": sorted({entity.category for entity in result.entities}),
            "entity_count": len(result.entities),
        }

    server.run(transport="stdio")


def _mcp_result_to_dict(result: Any) -> Dict[str, Any]:
    structured = getattr(result, "structuredContent", None)
    if isinstance(structured, dict):
        return structured.get("result", structured)

    for block in getattr(result, "content", []):
        text = getattr(block, "text", None)
        if text:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
    raise RuntimeError("Azure Language MCP returned no structured result.")


@asynccontextmanager
async def language_mcp_session() -> AsyncIterator[Any]:
    try:
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
    except ImportError as exc:
        raise RuntimeError(
            "MCP support is not installed. Run `pip install -r requirements-optional.txt`."
        ) from exc

    server = StdioServerParameters(
        command=sys.executable,
        args=[str(SCRIPT_PATH), "--serve-language-mcp"],
        env=os.environ.copy(),
    )
    async with stdio_client(server) as (read_stream, write_stream):
        async with ClientSession(read_stream, write_stream) as session:
            await session.initialize()
            yield session


class BankingToolRuntime:
    """Runs the privacy and retrieval tools used by both interaction modes."""

    def __init__(self, mcp_session: Any) -> None:
        self.openai_client = create_azure_openai_client(api_version="2024-05-01-preview")
        self.search_client = SearchClient(
            endpoint=require_env("AZURE_SEARCH_ENDPOINT"),
            index_name=clean_env_value("AZURE_SEARCH_INDEX", "rag-bank-documents"),
            credential=AzureKeyCredential(require_env("AZURE_SEARCH_ADMIN_KEY")),
        )
        self.mcp_session = mcp_session
        self.chat_model = clean_env_value("DEPLOYMENT_NAME", "gpt-4o")
        self.embedding_model = clean_env_value(
            "AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME", "text-embedding-ada-002"
        )
        self.last_redacted_text: Optional[str] = None

    async def redact_customer_text(self, text: str, language: str = "en") -> Dict[str, Any]:
        result = await self.mcp_session.call_tool(
            "redact_customer_text",
            arguments={"text": text, "language": language},
        )
        protected = _mcp_result_to_dict(result)
        self.last_redacted_text = protected["redacted_text"]
        return protected

    def search_bank_knowledge(self) -> Dict[str, Any]:
        if not self.last_redacted_text:
            return {"error": "Call redact_customer_text before searching bank knowledge."}

        embedding = self.openai_client.embeddings.create(
            model=self.embedding_model,
            input=self.last_redacted_text,
        ).data[0].embedding
        results = self.search_client.search(
            search_text=self.last_redacted_text,
            vector_queries=[
                VectorizedQuery(
                    vector=embedding,
                    k_nearest_neighbors=3,
                    fields="content_vector",
                )
            ],
            select=["title", "content"],
            top=3,
        )
        documents = [
            {
                "title": result["title"],
                "snippet": result["content"][:900],
                "score": result.get("@search.score"),
            }
            for result in results
        ]
        return {"documents": documents}

    async def execute(self, name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        if name == "redact_customer_text":
            return await self.redact_customer_text(**arguments)
        if name == "search_bank_knowledge":
            return await asyncio.to_thread(self.search_bank_knowledge)
        return {"error": f"Unknown tool: {name}"}

    async def answer_typed(self, raw_customer_text: str) -> str:
        protected = await self.redact_customer_text(raw_customer_text)
        print(
            "Language MCP: redacted "
            f"{protected['entity_count']} entities "
            f"({', '.join(protected['entity_categories']) or 'none'})."
        )
        evidence = await asyncio.to_thread(self.search_bank_knowledge)
        print(f"RAG tool: retrieved {len(evidence['documents'])} policy documents.")

        response = self.openai_client.chat.completions.create(
            model=self.chat_model,
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {
                    "role": "user",
                    "content": (
                        f"Redacted customer request: {protected['redacted_text']}\n\n"
                        f"Bank-policy evidence:\n{json.dumps(evidence, indent=2)}"
                    ),
                },
            ],
            temperature=0.2,
            max_tokens=700,
        )
        return response.choices[0].message.content or "No response was generated."


class AudioProcessor:
    """Stream 24-kHz PCM16 microphone and speaker audio for Voice Live."""

    def __init__(self, connection: Any) -> None:
        try:
            import pyaudio
        except ImportError as exc:
            raise RuntimeError(
                "Microphone support is not installed. Run "
                "`pip install -r requirements-optional.txt`."
            ) from exc

        self.pyaudio = pyaudio
        self.connection = connection
        self.audio = pyaudio.PyAudio()
        self.input_stream: Any = None
        self.output_stream: Any = None
        self.playback_buffer = bytearray()
        self.playback_buffer_lock = threading.Lock()
        self.noise_gate_release = 0
        self.loop: Optional[asyncio.AbstractEventLoop] = None

    def start(self) -> None:
        self.loop = asyncio.get_running_loop()

        def capture_callback(in_data: bytes, *_: Any):
            audio = base64.b64encode(in_data).decode("ascii")
            asyncio.run_coroutine_threadsafe(
                self.connection.input_audio_buffer.append(audio=audio), self.loop
            )
            return (None, self.pyaudio.paContinue)

        def playback_callback(_: Any, frame_count: int, *__: Any):
            byte_count = frame_count * VOICE_CHANNELS * 2
            with self.playback_buffer_lock:
                audio = bytes(self.playback_buffer[:byte_count])
                del self.playback_buffer[:byte_count]
            audio = audio.ljust(byte_count, b"\x00")

            peak = max((abs(sample) for sample in array("h", audio)), default=0)
            if peak >= VOICE_NOISE_GATE_THRESHOLD:
                self.noise_gate_release = VOICE_NOISE_GATE_RELEASE_CHUNKS
            elif self.noise_gate_release:
                self.noise_gate_release -= 1
            else:
                audio = b"\x00" * byte_count

            return (audio, self.pyaudio.paContinue)

        self.input_stream = self.audio.open(
            format=self.pyaudio.paInt16,
            channels=VOICE_CHANNELS,
            rate=VOICE_SAMPLE_RATE,
            input=True,
            frames_per_buffer=VOICE_CHUNK_SIZE,
            stream_callback=capture_callback,
        )
        self.output_stream = self.audio.open(
            format=self.pyaudio.paInt16,
            channels=VOICE_CHANNELS,
            rate=VOICE_SAMPLE_RATE,
            output=True,
            frames_per_buffer=VOICE_CHUNK_SIZE,
            stream_callback=playback_callback,
        )

    def queue_audio(self, audio: bytes) -> None:
        with self.playback_buffer_lock:
            self.playback_buffer.extend(audio)

    def clear_playback(self) -> None:
        with self.playback_buffer_lock:
            self.playback_buffer.clear()
        self.noise_gate_release = 0

    def close(self) -> None:
        for stream in (self.input_stream, self.output_stream):
            if stream:
                stream.stop_stream()
                stream.close()
        self.audio.terminate()


@asynccontextmanager
async def configured_voice_connection() -> AsyncIterator[Any]:
    try:
        from azure.ai.voicelive.aio import connect
        from azure.ai.voicelive.models import (
            AudioEchoCancellation,
            AudioInputTranscriptionOptions,
            AudioNoiseReduction,
            AzureStandardVoice,
            FunctionTool,
            InputAudioFormat,
            Modality,
            OutputAudioFormat,
            RequestSession,
            ServerVad,
            ToolChoiceLiteral,
        )
        from azure.identity.aio import DefaultAzureCredential as AsyncDefaultAzureCredential
    except ImportError as exc:
        raise RuntimeError(
            "Voice Live support is not installed. Run "
            "`pip install -r requirements-optional.txt`."
        ) from exc

    endpoint = resolve_foundry_service_endpoint(
        "AZURE_VOICELIVE_ENDPOINT", "services.ai.azure.com"
    )
    model = clean_env_value("AZURE_VOICELIVE_MODEL", "gpt-realtime")
    key = clean_env_value("AZURE_VOICELIVE_API_KEY")
    credential = (
        AzureKeyCredential(key)
        if has_usable_secret(key)
        else AsyncDefaultAzureCredential(
            exclude_environment_credential=True,
            exclude_managed_identity_credential=True,
        )
    )

    voice_tools = [
        FunctionTool(
            name="redact_customer_text",
            description=(
                "Required first step for every customer turn. Send the exact customer "
                "transcript to Azure Language and use only its redacted result afterward."
            ),
            parameters={
                "type": "object",
                "properties": {
                    "text": {"type": "string"},
                    "language": {"type": "string", "default": "en"},
                },
                "required": ["text"],
            },
        ),
        FunctionTool(
            name="search_bank_knowledge",
            description="Search bank policy using the most recently redacted customer text.",
            parameters={"type": "object", "properties": {}},
        ),
    ]

    try:
        async with connect(
            endpoint=endpoint,
            credential=credential,
            model=model,
        ) as connection:
            session = RequestSession(
                modalities=[Modality.TEXT, Modality.AUDIO],
                instructions=(
                    SYSTEM_PROMPT
                    + " For every customer turn, call redact_customer_text first, then call "
                    "search_bank_knowledge, and answer only from the returned redacted text "
                    "and policy evidence. Never speak the original transcript."
                ),
                voice=AzureStandardVoice(
                    name=clean_env_value(
                        "AZURE_VOICELIVE_VOICE", "en-US-Ava:DragonHDLatestNeural"
                    )
                ),
                input_audio_format=InputAudioFormat.PCM16,
                output_audio_format=OutputAudioFormat.PCM16,
                input_audio_transcription=AudioInputTranscriptionOptions(model="whisper-1"),
                input_audio_echo_cancellation=AudioEchoCancellation(),
                input_audio_noise_reduction=AudioNoiseReduction(
                    type="azure_deep_noise_suppression"
                ),
                turn_detection=ServerVad(
                    threshold=0.5,
                    prefix_padding_ms=400,
                    silence_duration_ms=500,
                ),
                tools=voice_tools,
                tool_choice=ToolChoiceLiteral.AUTO,
            )
            await connection.session.update(session=session)
            yield connection
    finally:
        close = getattr(credential, "close", None)
        if close:
            await close()


async def run_voice_agent(runtime: BankingToolRuntime) -> None:
    async with configured_voice_connection() as connection:
        from azure.ai.voicelive.models import FunctionCallOutputItem, ItemType, ServerEventType

        audio = AudioProcessor(connection)
        pending_call: Optional[Dict[str, Any]] = None
        print("Voice Live agent ready. Speak naturally; press Ctrl+C to stop.")
        try:
            async for event in connection:
                if event.type == ServerEventType.SESSION_UPDATED:
                    audio.start()
                elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STARTED:
                    audio.clear_playback()
                    print("Listening...")
                elif event.type == ServerEventType.INPUT_AUDIO_BUFFER_SPEECH_STOPPED:
                    print("Protecting and retrieving...")
                elif event.type == ServerEventType.RESPONSE_AUDIO_DELTA:
                    audio.queue_audio(event.delta)
                elif event.type == ServerEventType.CONVERSATION_ITEM_CREATED:
                    if event.item.type == ItemType.FUNCTION_CALL:
                        pending_call = {
                            "name": event.item.name,
                            "call_id": event.item.call_id,
                            "previous_item_id": event.item.id,
                        }
                        print(f"Tool call: {event.item.name}")
                elif event.type == ServerEventType.RESPONSE_FUNCTION_CALL_ARGUMENTS_DONE:
                    if pending_call and event.call_id == pending_call["call_id"]:
                        pending_call["arguments"] = event.arguments
                elif event.type == ServerEventType.RESPONSE_DONE and pending_call:
                    if "arguments" not in pending_call:
                        continue
                    arguments = json.loads(pending_call["arguments"] or "{}")
                    result = await runtime.execute(pending_call["name"], arguments)
                    output = FunctionCallOutputItem(
                        call_id=pending_call["call_id"],
                        output=json.dumps(result),
                    )
                    await connection.conversation.item.create(
                        previous_item_id=pending_call["previous_item_id"],
                        item=output,
                    )
                    pending_call = None
                    await connection.response.create()
                elif event.type == ServerEventType.ERROR:
                    raise RuntimeError(f"Voice Live error: {event.error.message}")
        finally:
            audio.close()


async def run_typed_agent(runtime: BankingToolRuntime, question: Optional[str]) -> None:
    print("AI-3016 Demo 7: Foundry RAG + Azure Language MCP + Voice Live")
    print("Typed mode protects each turn before retrieval. Type 'exit' to quit.\n")
    next_question = question
    while True:
        if next_question is None:
            try:
                next_question = input("customer > ").strip()
            except (EOFError, KeyboardInterrupt):
                break
        if next_question.lower() in {"exit", "quit"}:
            break
        if next_question:
            answer = await runtime.answer_typed(next_question)
            print(f"aria > {answer}\n")
        if question is not None:
            break
        next_question = None


async def run_demo(args: argparse.Namespace) -> None:
    async with language_mcp_session() as mcp_session:
        runtime = BankingToolRuntime(mcp_session)
        if args.voice:
            await run_voice_agent(runtime)
        else:
            await run_typed_agent(runtime, args.question)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a privacy-aware Foundry agent with RAG, Language MCP, and Voice Live"
    )
    parser.add_argument("--voice", action="store_true", help="Use Voice Live microphone mode")
    parser.add_argument("--question", help="Run one typed question and exit")
    parser.add_argument("--serve-language-mcp", action="store_true", help=argparse.SUPPRESS)
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    if args.serve_language_mcp:
        run_language_mcp_server()
        return

    try:
        asyncio.run(run_demo(args))
    except KeyboardInterrupt:
        print("\nStopped.")
    except RuntimeError as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()