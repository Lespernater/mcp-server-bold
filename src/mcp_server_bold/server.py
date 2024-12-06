import logging
import xmltodict
import requests
import httpx
import json
from pathlib import Path
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    TextContent,
    Tool,
)
from enum import Enum
from pydantic import BaseModel, Field

API_BASE_URL = "http://v3.boldsystems.org/index.php/API_Public/"
DEFAULT_PARAMETERS = {"format": "tsv"}
logger = logging.getLogger(__name__)

class BoldQuery(BaseModel):
    taxon: str = Field(default="", description="""Taxonomic query (e.g., 'Aves', 'Bos taurus')""")
    geo: str = Field(default="", description="""Geographic sites (countries/provinces, pipe-delimited)""")
    ids: str = Field(default="", description="""Specific specimen IDs (pipe-delimited)""")
    bin: str = Field(default="", description="""Barcode Index Number (BIN) URIs (pipe-delimited)""")
    container: str = Field(default="", description="""Project or dataset codes (pipe-delimited)""")
    institution: str = Field(default="", description="""Specimen storing institutions (pipe-delimited)""")
    researchers: str = Field(default="", description="""Collector or identifier names (pipe-delimited)""")


class BoldSpecQuery(BoldQuery):
    format: str = Field(default="tsv", examples=["xml", "tsv"])


class BoldSeqQuery(BoldQuery):
    marker: str = Field(default="", description="""Marker codes like 'matK', 'rbcL', 'COI-5P' (pipe-delimited)""")


class BoldTools(str, Enum):
    SPECIMEN = "specimen-search"
    SEQUENCE_SPECIMEN = "sequence-specimen-search"


async def base_fetch(search="specimen", **kwargs):
    """
    Fetch specimens from BOLD API based on provided parameters.

    :param kwargs: Parameters for BOLD specimen query
    :return: JSON of retrieved specimen data
    """
    # Prepare query parameters
    query_params = {**DEFAULT_PARAMETERS, **kwargs}
    logger.info(f"Fetching specimens with parameters: {query_params}")

    assert (search in ["specimen", "combined"])

    try:
        async with httpx.AsyncClient() as client:
            # Build formatted query string to add to API CALL
            query_string = '&'.join([
                f"{key}={requests.utils.quote(str(value))}"
                for key, value in query_params.items()
                if value != ""
            ])
            query_url = f"{API_BASE_URL}{search}?{query_string}"
            response = await client.get(query_url)  # Query API
        response.raise_for_status()  # Raise any errors
        logger.info("Successfully fetched specimens.")

        # Check the format parameter to determine how to handle the response
        if query_params.get('format') == 'tsv':
            # Convert tsv response to a list of dictionary before json, with commentary on length
            tsv_data = response.text.splitlines()
            headers = tsv_data[0].split('\t')
            json_data = [dict(zip(headers, row.split('\t'))) for row in tsv_data[1:2000]]
            length = len(json_data)
        elif query_params.get('format') == 'xml':
            # Convert xml response to an OrderedDict[str, Any] before json, with commentary on length
            xml_data = response.text
            json_data = xmltodict.parse(xml_data)
            length = len(json_data)
        else:
            logger.error("Unsupported format requested.")
            raise ValueError("Unsupported format requested.")
        if length > 2000:  # Add truncated message
            logger.info("Truncating fetched specimens (length).")
            trunc_json = [{"message": f"True length is {length} total specimens but truncated here to first 2000."}]
            json_out = {"commentary": trunc_json, "data": json_data}
        else:
            json_out = json_data
        return json.dumps(json_out)  # Return JSON response
    except (httpx.HTTPStatusError, httpx.RequestError) as e:
        logger.error(f"Error fetching specimens: {str(e)}")
        raise


async def fetch_bold_specimens(**kwargs):
    """
    Fetch specimen records

    :param kwargs: Parameters for BOLD specimen query
    :return: JSON of retrieved data
    """
    return base_fetch(search="specimen",**kwargs)


async def fetch_bold_seq_specimens(**kwargs):
    """
    Fetch combined specimen and sequence records

    :param kwargs: Parameters for BOLD combined query
    :return: JSON of retrieved data
    """
    return base_fetch(search="combined",**kwargs)


async def serve() -> None:
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

        # Ensure format is set, defaulting to xml
        if 'format' not in query_params:
            query_params['format'] = 'xml'

        logger.info(f"Calling tool with parameters: {query_params}")
        match name:
            case BoldTools.SPECIMEN:
                # Fetch specimens
                specimen_data = await fetch_bold_specimens(**query_params)
                return [TextContent(
                    type="text",
                    text=f"Specimen returned:\n{json.dumps(specimen_data)}"
                )]
            case BoldTools.SEQUENCE_SPECIMEN:
                # Fetch specimens
                specimen_data = await fetch_bold_seq_specimens(**query_params)
                return [TextContent(
                    type="text",
                    text=f"Specimen with sequences returned:\n{json.dumps(specimen_data)}"
                )]
            # Add other tools here
        # When don't recognize tool
        logger.error(f"Unknown tool requested: {name}")
        raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
