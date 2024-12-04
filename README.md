
# Bold MCP Server

A Model Context Protocol server that provides capabilities for searching BOLD specimens. This server enables LLMs to retrieve and process content related to specific search queries in a simplified manner.

![Example](/Users/nlespera/PycharmProjects/boldmcp/imgs/example_usage.png)

### Available Tools

- `specimen-search` - Searches for specimens based on given criteria.

## Installation

### Using PIP

You can install `mcp-server-bold` via pip:

```
git clone [LINK NEEDED]
cd mcp-server-bold
pip install -e .
```

After installation, you can run it as a script using:

```
python -m mcp_server_bold
```

You can also run your own MCP interpreter for debugging using:

```
npx @modelcontextprotocol/inspector python -m mcp_server_bold
```

## Configuration

### Configure for Claude.app

Add to your Claude settings:

<details>
<summary>Add to ```claude_desktop_config.json```</summary>

```json
"mcpServers": {
  "bold": {
    "command": "python",
    "args": ["-m", "mcp_server_bold"]
  }
}
```
</details>

When you open Claude Desktop, you should see a new
![PLUG ICON](/Users/nlespera/PycharmProjects/boldmcp/imgs/plugin.png)
icon in your chat prompt to confirm the BOLD MCP Server is detected.

Each time you query BOLD through the MCP Server, you will have to agree to permit access to the MCP Server.

![Agreement](/Users/nlespera/PycharmProjects/boldmcp/imgs/chat_accept_permission.png)

## Debugging

You can use the MCP inspector to debug the server. If you've installed the package in a specific directory or are developing on it:

```
cd path/to/servers/src/bold
npx @modelcontextprotocol/inspector python -m mcp-server-bold
```

## Contributing

We encourage contributions to help expand and improve mcp-server-bold. Whether you want to add new tools, enhance existing functionality, or improve documentation, your input is valuable.

For examples of other MCP servers and implementation patterns, see:
https://github.com/modelcontextprotocol/servers

Pull requests are welcome! Feel free to contribute new ideas, bug fixes, or enhancements to make mcp-server-bold even more powerful and useful.

## License

mcp-server-bold is licensed under the MIT License. This means you are free to use, modify, and distribute the software, subject to the terms and conditions of the MIT License. For more details, please see the LICENSE file in the project repository.
