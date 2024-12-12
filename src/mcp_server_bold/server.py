import logging
import json
import asyncio
from enum import Enum
import xmltodict
import requests
import httpx
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from pydantic import BaseModel, Field

API_BASE_URL = "http://v3.boldsystems.org/index.php/API_Public/"
DEFAULT_PARAMETERS = {"format": "tsv"}

logger = logging.getLogger(__name__)

class BoldQuery(BaseModel):
    """Base Model to define parameters for querying the BOLD API."""
    taxon: str = Field(
        default="",
        description="""Taxonomic query (e.g., 'Aves', 'Bos taurus')"""
    )
    geo: str = Field(
        default="",
        description="""Geographic sites (countries/provinces, pipe-delimited)"""
    )
    ids: str = Field(
        default="",
        description="""Specific specimen IDs (pipe-delimited)"""
    )
    bin: str = Field(
        default="",
        description="""Barcode Index Number (BIN) URIs (pipe-delimited)"""
    )
    container: str = Field(
        default="",
        description="""Project or dataset codes (pipe-delimited)"""
    )
    institution: str = Field(
        default="",
        description="""Specimen storing institutions (pipe-delimited)"""
    )
    researchers: str = Field(
        default="",
        description="""Collector or identifier names (pipe-delimited)"""
    )


class BoldSpecQuery(BoldQuery):
    """Model for formatting BOLD specimen queries with a specific output format."""
    format: str = Field(default="tsv", examples=["xml", "tsv"])


class BoldSeqQuery(BoldQuery):
    """Model for formatting BOLD sequence (combined) queries, which includes marker information."""
    marker: str = Field(
        default="",
        description="""Marker codes like 'matK', 'rbcL', 'COI-5P' (pipe-delimited)"""
    )


class BoldTools(str, Enum):
    """Enumeration of tools available for querying BOLD API."""
    SPECIMEN = "specimen-search"
    SEQUENCE_SPECIMEN = "combined-search"


async def base_fetch(**kwargs):
    """
    Fetch specimens from BOLD API based on provided parameters.

    :param kwargs: Parameters for BOLD specimen query
    :return: JSON dump of retrieved specimen data
    """
    # Prepare query parameters
    query_params = {**DEFAULT_PARAMETERS, **kwargs}
    search = query_params.pop("search")
    logger.info(f"Fetching specimens with parameters: {query_params}")

    # Build formatted query string to add to API CALL
    query_string = '&'.join([
        f"{key}={requests.utils.quote(str(value))}"
        for key, value in query_params.items()
        if value != ""
    ])
    query_url = f"{API_BASE_URL}{search}?{query_string}"

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0)) as client:
            response = await client.get(query_url)  # Query API
            response.raise_for_status()  # Ensure we handle bad responses

        logger.info("Successfully fetched specimens.")

        # Check the format to determine how to handle the response
        if query_params.get('format') == 'tsv':
            # Convert tsv response to list[dict] before json
            json_data = []
            headers = None
            async for chunk in response.aiter_bytes():  # Stream response
                # Decode and process in chunks
                lines = chunk.decode('utf-8').splitlines()
                if headers is None:
                    headers = lines[0].split('\t')  # Read headers from the first chunk
                json_data.extend(dict(zip(headers, line.split('\t'))) for line in lines[1:])
        elif query_params.get('format') == 'xml':
            # Convert xml response to OrderedDict[str, Any] before json
            xml_data = bytearray()  # Use bytearray to accumulate chunks
            async for chunk in response.aiter_bytes():  # Stream response
                xml_data.extend(chunk)
                json_data = xmltodict.parse(xml_data.decode('utf-8'))
        else:
            logger.error("Unsupported format requested.")
            raise ValueError("Unsupported format requested.")
        return json.dumps(json_data)  # Return JSON response
    except (asyncio.TimeoutError, httpx.TimeoutException, asyncio.CancelledError) as exc:
        logger.error(
            f"{str(exc)}, likely need to narrow search to fewer specimen"
        )
        return json.dumps({
            "message":
            f"{str(exc)}, likely need to narrow search to fewer specimen"
        })
    except httpx.HTTPStatusError as exc:
        logger.error(
            f"HTTP error occurred: {exc.response.status_code} - {exc.response.text}"
        )
        return json.dumps({
            "message":
            f"HTTP error occurred: {exc.response.status_code}"
        })
    except httpx.RequestError as e:
        logger.error(f"Error fetching specimens: {str(e)}")
        return json.dumps({"message": f"HTTP RequestError occurred: {str(e)}"})
    except Exception as ex:
        logger.error(f"Error fetching specimens: {str(ex)}")
        return json.dumps({"message": f"Error occurred: {str(ex)}"})

async def serve() -> None:
    """Start the MCP BOLD server and define the available tools.
    Initializes the server and sets handlers for listing and calling tools, including
    handling input parameters and responses.

    :return: None
    """
    server = Server("mcp-server-bold")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=BoldTools.SPECIMEN,
                description="Query BOLD Rest API for a specimen",
                inputSchema=BoldSpecQuery.schema(),
            ),
            Tool(
                name=BoldTools.SEQUENCE_SPECIMEN,
                description="Query BOLD Rest API for both specimen info and nucleotide (DNA) sequence",
                inputSchema=BoldSeqQuery.schema(),
            ),
            # Add new tools here
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        # Remove None values and prepare query
        query_params = {k: v for k, v in arguments.items() if v is not None}

        # Ensure format is set, defaulting to tsv
        if 'format' not in query_params:
            query_params['format'] = 'tsv'

        logger.info(f"Calling tool with parameters: {query_params}")
        match name:
            case BoldTools.SPECIMEN:
                query_params["search"] = "specimen"
                # Fetch specimens
                specimen_data = await base_fetch(**query_params)
                return [TextContent(
                    type="text",
                    text=f"Specimen returned:\n{json.dumps(specimen_data)}"
                )]
            case BoldTools.SEQUENCE_SPECIMEN:
                query_params["search"] = "combined"
                # Fetch specimens
                combined_data = await base_fetch(**query_params)
                return [TextContent(
                    type="text",
                    text=f"Specimen with sequences returned:\n{json.dumps(combined_data)}"
                )]
            # Add other tools here
        # When don't recognize tool
        logger.error(f"Unknown tool requested: {name}")
        raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
