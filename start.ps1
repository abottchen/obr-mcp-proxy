$root = Split-Path -Parent $MyInvocation.MyCommand.Path
wt -w 0 -d "$root\extension" --title "OBR Extension" cmd /c "npx vite" `; sp -H -s 0.75 -d "$root\server" --title "MCP Server" cmd /c "python -m server.main"
