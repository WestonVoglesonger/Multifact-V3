---
name: Test Failure - Foreign Key Violations in Token Compiler Tests
about: Token compiler tests failing due to foreign key violations
title: '[TEST] Fix Foreign Key Violations in Token Compiler Tests'
labels: bug, test
assignees: ''

---

**Describe the bug**
Token compiler tests are failing due to foreign key violations, indicating issues with test database setup and relationship management.

**Affected Tests**
- `test_token_compiler_compile_success`
- `test_token_compiler_compile_fail`
- `test_token_compiler_cache_hit`

**Error Message**
```
sqlalchemy.exc.IntegrityError: (psycopg2.errors.ForeignKeyViolation)
```

**Root Cause**
Test fixtures are not properly setting up related database records before running tests. Specifically:
1. Token relationships are not being established correctly
2. Required parent records may be missing
3. Database state is not consistent between tests

**To Fix**
1. Review and update test fixtures to ensure proper record creation order
2. Implement proper cascading cleanup in teardown
3. Add relationship validation before test execution
4. Consider implementing a test database state manager
5. Add better error handling for relationship setup failures

**Environment**
- Python Version: 3.11.11
- SQLAlchemy Version: Latest
- Test Framework: pytest

**Additional Context**
These failures indicate a need for better test database state management and possibly a more robust fixture system.
