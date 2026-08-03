# Data contracts

The YAML contracts define the grain, primary key, foreign keys, logical column types and nullability expectations for every generated source table. They are generated from the same schema registry used by the Python validator and PostgreSQL loader, which prevents drift between generation, validation and loading.

`catalog.yaml` is the contract index.
