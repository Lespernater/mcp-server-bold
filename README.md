
# BOLD MCP Server

A Model Context Protocol server that provides capabilities for searching BOLD specimens. This server enables LLMs to retrieve and process content related to specific BOLD Rest API search queries in a simplified manner.

### Available Tools

- `specimen-search` - Fetches specimen data based on given criteria.
- `combined-search` - Fetches specimen and sequence data based on given criteria.

## Installation

### Using PIP

You can install `mcp-server-bold` via pip:

```
git clone https://github.com/Lespernater/mcp-server-bold.git
cd mcp-server-bold
pip install -e .
```

After installation, you can run it as a script using:

```
python -m mcp_server_bold
```

You now can also run a locally hosted MCP interpreter for debugging using:

```
npx @modelcontextprotocol/inspector python -m mcp_server_bold
```

## Configuration

### Configure for Claude Destop App

Add to your `claude_desktop_config.json`, found easiest through the Claude Desktop settings:

<details>
<summary>Add to claude config:</summary>

```json
"mcpServers": {
  "bold": {
    "command": "python",
    "args": ["-m", "mcp_server_bold"]
  }
}
```
</details>

You'll need to restart Claude Desktop, you should see a new plug icon and/or hammer icons in your chat prompt that confirms the BOLD MCP Server is detected.

Each time you create a new chat that queries BOLD through the MCP Server, you will have to agree to permit access to the MCP Server's Tool.

If it isn't working with the above set up, you can try creating a separate conda env and running Claude from there.

```
conda activate <custom_env>
git clone https://github.com/Lespernater/mcp-server-bold.git
cd mcp-server-bold
pip install -e .
open -a "Claude"
```

You may also need to point to absolute path of python in `claude_desktop_config.json`

<details>
<summary>Add to claude config:</summary>

```json
"mcpServers": {
  "bold": {
    "command": "/path/to/bin/python",
    "args": ["-m", "mcp_server_bold"]
  }
}
```
</details>

### Other hosts will be added as they become available (Zed currently doesn't support MCP Tools)

## Debugging

You can use the MCP inspector to debug the server. If you've installed the package in a specific directory or are developing on it:

```
cd path/to/servers/src/mcp_server_bold
npx @modelcontextprotocol/inspector python -m mcp_server_bold
```

## Contributing

We encourage contributions to help expand and improve mcp-server-bold. Whether you want to add new tools, enhance existing functionality, or improve documentation, your input is valuable.

For examples of other MCP servers and implementation patterns, see:
https://github.com/modelcontextprotocol/servers

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-bold even more powerful and useful.

## License

mcp-server-bold is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
