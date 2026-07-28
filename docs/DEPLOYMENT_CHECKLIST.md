# AIHOME v1.0 RC2 Deployment Checklist

- Confirm approved commit and `aihome-v1.0-rc2` tag.
- Confirm clean, intentional release scope with no runtime artifacts.
- Back up the database and uploaded assets.
- Run forward migrations and verify their postconditions.
- Install backend production dependencies.
- Deploy backend and verify health and API routes.
- Build and deploy frontend.
- Verify WACP single-intent and multi-intent submission.
- Verify workflow polling, result synchronization, reports, and image imports.
- Verify design version selection and baseline approval.
- Monitor errors and retain the prior application tag for rollback.
