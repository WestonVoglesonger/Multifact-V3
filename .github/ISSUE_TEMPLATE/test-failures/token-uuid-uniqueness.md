---
name: Test Failure - Token UUID Uniqueness Violations
about: Integration tests failing due to token UUID conflicts
title: '[TEST] Fix Token UUID Uniqueness Violations in Integration Tests'
labels: bug, test
assignees: ''

---

**Describe the bug**
Multiple integration tests are failing due to unique constraint violations on token UUIDs. This indicates that tokens are not being properly isolated between test runs.

**Affected Tests**
- `test_create_ni_document`
- `test_user_intervention_service_update_and_recompile_success`
- `test_code_evaluation_flow`
- `test_multi_token_dependency`
- `test_ni_to_code_compilation_e2e`

**Error Message**
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.UniqueViolation) duplicate key value violates unique constraint "ni_tokens_token_uuid_key"
```

**Root Cause**
Token UUIDs are being reused across test runs, violating the unique constraint in the database. This suggests that:
1. Test isolation is insufficient
2. UUID generation strategy needs improvement
3. Database cleanup between tests may be incomplete

**To Fix**
1. Implement proper test isolation mechanisms
2. Review and improve UUID generation strategy for test environments
3. Ensure proper database cleanup between test runs
4. Consider using temporary schemas for each test
5. Add transaction rollback after each test

**Environment**
- Python Version: 3.11.11
- SQLAlchemy Version: Latest
- Test Framework: pytest

**Additional Context**
This issue is blocking several integration tests and needs to be addressed for reliable test execution.
