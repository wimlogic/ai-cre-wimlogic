# PATCH INSTRUCTIONS — app/models/design_image_version.py

I do not have a verified copy of this file (it was never modified in any
of my prior deliveries, so it wasn't recoverable after this session's
environment reset). Rather than fabricate a full replacement and risk
silently dropping or altering fields I can't see, apply this small,
targeted patch to your actual current file.

Find the four existing lines for `width`, `height` (or wherever they are
declared - they should sit directly after `height` per the schema and
the migration above), and add these four new nullable columns
immediately after them:

```python
    # AIHOME Image Result Integration - IMAGE_DESIGN provenance.
    # Populated only for versions imported from a DEV-TOOLS IMAGE_DESIGN
    # result (design_result_service.ingest_image_design_results());
    # NULL for every version created through any other existing path.
    source_image_id = Column(String(120), nullable=True)
    source_provider = Column(String(80), nullable=True)
    source_model = Column(String(120), nullable=True)
    source_checksum = Column(String(128), nullable=True)
    source_artifact_url = Column(String(500), nullable=True)
    quality_approved = Column(Boolean, nullable=True)
```

(`Boolean` - if not already imported from `sqlalchemy` in this file, add
it alongside the existing `Column`/`String` import.)

This matches `add_design_image_version_provenance_columns.sql` exactly
(same order, same types, same nullability). No other change to this file
is required - every existing field, relationship, and constraint stays
exactly as it is.

If your actual model already imports `Column` and `String` from
`sqlalchemy` (it certainly does, given the existing `version_uid`/
`file_name` string columns), no new imports are needed either.
