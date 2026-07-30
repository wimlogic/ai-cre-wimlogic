# Business Intent Routing Hotfix

Base commit: `da1a0e5c993809e337aab9c0dd08f3a40db4d7af`

This narrow backend hotfix makes a nonempty `business_intent` supplied to
`POST /api/v1/ai-orchestration/submit` authoritative. `IMAGE_DESIGN` and
`PROPERTY_ANALYSIS` are the supported explicit values. Missing, null, empty,
or whitespace-only values retain the deployed
`ZONING_ANALYSIS -> PROPERTY_ANALYSIS` mapping.

Unsupported explicit values fail with the API's existing `ValueError` to HTTP
400 convention before a local execution is created or WACP is called.

`additional_business_intents` remains unsupported and ignored, exactly as in
the deployed backend. Multi-intent WACP support is deferred and is not part of
this hotfix.
