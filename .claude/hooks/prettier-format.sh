#!/bin/bash

# Post-tool-use hook for Claude Code
# Runs prettier on the file that Edit/Write just changed

# Read the JSON input from stdin
INPUT=$(cat)

# Extract the edited file path with node (jq is not guaranteed to be installed)
# printf, not echo: echo can collapse the \\ escapes in Windows paths and break the JSON
FILE=$(printf '%s' "$INPUT" | node -e '
let data = "";
process.stdin.on("data", (chunk) => (data += chunk)).on("end", () => {
  const json = JSON.parse(data);
  process.stdout.write(json.tool_response?.filePath || json.tool_input?.file_path || "");
});
')

[ -z "$FILE" ] && exit 0

# prettier is installed in the project's node_modules; --no-install avoids fetching it on demand
cd "${CLAUDE_PROJECT_DIR:-.}" || exit 0

# --ignore-unknown skips file types prettier has no parser for (e.g. .py)
npx --no-install prettier --write --ignore-unknown "$FILE" > /dev/null 2>&1

# Formatting is best-effort and must never block the tool
exit 0
