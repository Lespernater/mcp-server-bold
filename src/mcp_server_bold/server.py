import logging
import xmltodict
import requests  # Using requests instead of httpx
import httpx
import json
from urllib.parse import urlparse
from pathlib import Path
from typing import Sequence
from mcp.server import Server
from mcp.server.session import ServerSession
from mcp.server.stdio import stdio_server
import mcp.types as types
from mcp.types import (
    ClientCapabilities,
    TextContent,
    Tool,
    ListRootsResult,
    RootsCapability,
)
from enum import Enum
from pydantic import BaseModel, Field

# Defaults
API_BASE_URL = "http://v3.boldsystems.org/index.php/API_Public/specimen"
DEFAULT_PARAMETERS = {"format": "xml"}

class BoldQuery(BaseModel):
    format: str = Field(default="xml", examples=["xml", "tsv"])
    taxon: str = Field(default="", description="""Taxonomic query (e.g., 'Aves', 'Bos taurus')""")
    geo: str = Field(default="", description="""Geographic sites (countries/provinces, pipe-delimited)""")
    ids: str = Field(default="", description="""Specific specimen IDs (pipe-delimited)""")
    bin: str = Field(default="", description="""Barcode Index Number (BIN) URIs (pipe-delimited)""")
    container: str = Field(default="", description="""Project or dataset codes (pipe-delimited)""")
    institution: str = Field(default="", description="""Specimen storing institutions (pipe-delimited)""")
    researchers: str = Field(default="", description="""Collector or identifier names (pipe-delimited)""")


class BoldTools(str, Enum):
    SPECIMEN = "specimen-search"


async def serve() -> None:
    logger = logging.getLogger(__name__)

    server = Server("mcp-server-bold")

    async def fetch_bold_specimens(**kwargs):
        """
        Fetch specimens from BOLD API based on provided parameters.

        :param kwargs: Parameters for BOLD specimen query
        :return: JSON of retrieved specimen data
        """
        # Prepare query parameters
        query_params = {**DEFAULT_PARAMETERS, **kwargs} if isinstance(DEFAULT_PARAMETERS, dict) else {}
        logger.info(f"Fetching specimens with parameters: {query_params}")

        try:
            async with httpx.AsyncClient() as client:
                # Build formatted query string to add to API CALL
                query_string = '&'.join([
                    f"{key}={requests.utils.quote(str(value))}" for key, value in query_params.items() if value != ""
                ])

                # Query API
                response = await client.get(f"{API_BASE_URL}?{query_string}")
            response.raise_for_status()  # Raise any errors
            logger.info("Successfully fetched specimens.")

            # Check the format parameter to determine how to handle the response
            if query_params.get('format') == 'tsv':
                # For TSV format, convert response to a structured dictionary
                tsv_data = response.text.splitlines()
                headers = tsv_data[0].split('\t')
                json_list = [dict(zip(headers, row.split('\t'))) for row in tsv_data[1:]]
                return json.dumps(json_list)  # Return JSON response
            elif query_params.get('format') == 'xml':
                # Convert XML response to JSON
                xml_data = response.text
                json_data = xmltodict.parse(xml_data)
                return json.dumps(json_data)  # Return JSON response
            else:
                logger.error("Unsupported format requested.")
                raise ValueError("Unsupported format requested.")
        except (httpx.HTTPStatusError, httpx.RequestError) as e:
            logger.error(f"Error fetching specimens: {str(e)}")
            raise

    async def read_log_file():
        logger = logging.getLogger(__name__)
        log_file_path = Path("server.log")  # Path to the log file

        try:
            with log_file_path.open("r") as log_file:
                log_contents = log_file.read()
                logger.info("Log file read successfully.")
                return log_contents
        except Exception as e:
            logger.error(f"Error reading log file: {str(e)}")
            return "Could not read log file."


    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name=BoldTools.SPECIMEN,
                description="Query BOLD Rest API for a specimen",
                inputSchema=BoldQuery.schema(),
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
            # Add other tools here
        # When don't recognize tool
        logger.error(f"Unknown tool requested: {name}")
        raise ValueError(f"Unknown tool: {name}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options, raise_exceptions=True)
