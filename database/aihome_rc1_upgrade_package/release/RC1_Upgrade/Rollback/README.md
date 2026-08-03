# Rollback: Nothing To Roll Back

This upgrade executes zero migrations, so there are no rollback scripts —
placeholder rollback files for migrations that don't exist would be
misleading, so none are provided.

Rollback for this release is code-only:

1. Restore the prior backend/frontend files (revert the code overlay).
2. Rebuild the frontend.
3. Restart the backend.

The database is untouched by this upgrade and remains simultaneously valid
for both the pre-RC1 and RC1 code at every point — a direct consequence of
the zero-schema-delta audit result.
