"""BEGIN COPYRIGHT NOTICE
Copyright 2026 Open Text.

The only warranties for products and services of Open Text and its affiliates and licensors
("Open Text") are as may be set forth in the express warranty statements accompanying such
products and services. Nothing herein should be construed as constituting an additional warranty.
Open Text shall not be liable for technical or editorial errors or omissions contained herein.
The information contained herein is subject to change without notice.

END COPYRIGHT NOTICE"""

# /// script
# requires-python = ">=3.11"
# dependencies = [
#     "httpx>=0.27",
#     "mcp>=1.0,<2.0",
#     "pydantic>=2.0",
#     "sqlglot>=25.0",
# ]
# ///

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from content_mcp.content_discovery import main


if __name__ == "__main__":
    main()
