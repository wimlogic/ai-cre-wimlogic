# AIHOME v1.0 RC2 Rollback Plan

1. Stop new workflow submissions and record in-flight execution IDs.
2. Capture application logs and deployment metadata.
3. Restore the previously approved application tag.
4. If schema rollback is required, confirm no design jobs depend on RC2 source
   image versions and run `database/migrations/rollback_aihome_v1_0_rc2.sql`.
5. If rollback SQL cannot safely run, restore the pre-deployment database backup.
6. Restore uploaded assets if storage contents changed.
7. Redeploy the prior backend and frontend.
8. Smoke-test database access, APIs, WACP submission, result synchronization,
   reports, image delivery, and baseline approval.
