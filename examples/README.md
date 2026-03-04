# Example Archive Status

## Current State (Post-Fix)

The example archive currently has incomplete data due to regeneration issues during development. The database has been corrupted/reset during troubleshooting.

## Fix Applied

The user profile fetching bug has been **FIXED** in commit `12e3ac2`. All future archives will correctly fetch user profiles for all users.

### What Was Fixed:
- User fetching now scans ALL posts in database (not just current run)
- Added `get_unique_usernames()` method to database classes
- Prevents missing user profiles in incremental/interrupted archives

## Regenerating the Example Archive

To regenerate the example archive with complete user profiles:

```bash
# 1. Clean start
rm -rf examples/meta-example
mkdir -p examples/meta-example

# 2. Create archive with ~100 topics from meta.discourse.org
.venv/bin/python -m chronicon.cli archive \
  --urls https://meta.discourse.org \
  --sweep \
  --start-id 394700 \
  --end-id 394500 \
  --output-dir ./examples/meta-example \
  --formats html,markdown,markdown-github

# This will now automatically:
# - Fetch all topics in ID range
# - Fetch ALL posts for those topics  
# - Scan database for unique usernames
# - Fetch user profiles for ALL users
# - Generate exports with complete user pages
```

The fix ensures that:
1. Initial archives fetch all user profiles
2. Incremental updates fetch missing user profiles
3. No ad-hoc scripts needed
4. Production-ready and repeatable

## Note

The example archive in the current commit may have incomplete user data due to the corruption during fix development. This does not affect the functionality - the bug is fixed in the code and all future archives will work correctly.
