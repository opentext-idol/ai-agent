<!--
BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE
-->

# Content MCP server

A local, read-only MCP server for discovering and reading documents from an
OpenText Knowledge Discovery (IDOL) Content engine. MCP clients such as Claude
Code can use it over stdio. The server requires access to a running Content
engine; it does not include one.

## Setup

1. Clone this repository and keep the checkout in a stable location.
2. Install [uv](https://docs.astral.sh/uv/getting-started/installation/).
   The launcher requires Python 3.11 or later; uv can obtain Python and the
   dependencies declared in the launcher. No installation of this project or
   published package is required.
3. Configure your MCP client to run `uv run` with the **absolute path** to
   `mcp/content/run_server.py` and set `CONTENT_BASE` to your Content URL.
   The first launch may need network access to download dependencies.

### Claude Code

For example, in PowerShell, replace the path and URL with your own:

```powershell
claude mcp add --scope user --transport stdio --env CONTENT_BASE=https://content.example.org:9100 content -- uv run C:\path\to\ai-agent\mcp\content\run_server.py
```

Quote the script path if it contains spaces. Use `--scope local` instead of
`--scope user` to configure only the current project. Check the connection
with `claude mcp get content` or `/mcp` in Claude Code. See the
[Claude Code MCP documentation](https://code.claude.com/docs/en/mcp) for
configuration scopes and troubleshooting.

For other MCP clients, use their stdio server configuration; for example:

```json
{
  "mcpServers": {
    "content": {
      "command": "uv",
      "args": ["run", "C:\\path\\to\\ai-agent\\mcp\\content\\run_server.py"],
      "env": {
        "CONTENT_BASE": "https://content.example.org:9100"
      }
    }
  }
}
```

Use the full path to `uv` if the client cannot find it on its PATH. Keep the
checkout in place: the launcher loads the neighboring source files on each run.
To update, update the checkout and restart the MCP client. For reproducible
deployments, use a reviewed Git tag or commit and manage dependency versions.

## Configuration and security

- `CONTENT_BASE`: Content endpoint, including scheme and port. Defaults to
  `http://localhost:9100`.
- `CONTENT_SECURITY_INFO`: optional Content security token, supplied to Content
  on requests. If unset, Content's own access configuration determines which
  documents are accessible.
- `CONTENT_TEXT_FIELDS`: optional comma-separated narrative text field names.
  When unset, the server detects index fields, falling back to `DRECONTENT`.

Only connect trusted users and MCP hosts. The server can expose any documents
accessible with its configured Content identity, and startup instructions can
include field names and example values. Retrieved text can contain untrusted
instructions; use your client's safeguards against prompt injection. Use HTTPS
for remote connections and protect tokens: do not commit them to the repository
or place them in shared project configuration. Claude's `--env` settings are
stored in its configuration, so handle that file as sensitive if it contains a
token. Model providers may receive document contents returned to the client.

If Content is unavailable during startup, the server starts with generic
workflow instructions and reports the schema failure on stderr; queries still
require a reachable Content engine. Restart the server to refresh its schema
summary.

## Tools

The server provides search, exact document counts, aggregations, field
discovery, document reads, and suggestions. Counts are documents, not
necessarily unique entities. Aggregations depend on Content's indexed field
configuration; errors and warnings from Content should not be treated as zero
matches.

## License

See the repository's [MIT license](../../LICENSE).
