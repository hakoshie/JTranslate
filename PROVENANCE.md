# Source and license

JTranslate is a separate Windows translation application derived from
[hakoshie/jhenkan](https://github.com/hakoshie/jhenkan), upstream commit
`ea2465751d0f2d664cc199ffe967b007d2bdbd25` (MIT, copyright 2026 hakoshie).
The original LICENSE and copyright notice are retained.

The converter transport, ChatGPT OAuth/DPAPI implementation, RegisterHotKey
listener, tray backend and selection utilities originated in that project.
JTranslate adds a separate package, configuration and login storage,
translation prompts, conservative line-break cleanup, selection-only UI,
resizable floating popup, clipboard copy and translation tests.

The original JHenkan repository, installation and credentials are not migrated
or deleted. Optional compatibility mode reads JHenkan's existing connection.
Dedicated JTranslate sign-in uses a new app registration named JTranslate.
No existing issued OAuth client ID is repurposed for that registration.

Official authentication reference checked 2026-10-17:
https://developers.openai.com/siwc/token-sharing-open-source/sign-in

This repository was initialized locally without a remote. No GitHub repository,
push or pull request has been created. Real credentials, personal settings,
logs and machine-specific shortcuts are excluded from version control.
