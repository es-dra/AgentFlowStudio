# API

FastAPI is still not part of this branch.

The Web UI supervised production slice uses `apps/web_bridge`, a small stdlib
local HTTP bridge for `127.0.0.1` only. It exists so the static browser UI can
launch existing CLI/workflow operations without introducing a server framework,
database, SaaS account model, upload path, or provider configuration surface.
