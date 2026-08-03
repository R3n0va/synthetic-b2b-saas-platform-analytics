# Landing layer

Landing tables are created dynamically by the Python PostgreSQL loader from the governed schema registry in `data_generator/src/b2b_saas_platform_analytics/schema.py`.

Every source column is initially loaded as text through PostgreSQL `COPY`. Typed core tables are then rebuilt from the same registry. This prevents a second hand-maintained DDL definition from drifting away from the Python generator and YAML contracts.
