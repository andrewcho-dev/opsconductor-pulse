# Task 10: Cross-Reference and Freshness Metadata Pass

## Context

All new docs have been written (Tasks 2-7), old files archived/deleted (Task 8), and README updated (Task 9). This final pass ensures:
1. Every internal link resolves to a real file
2. Every doc has correct YAML frontmatter
3. All "See Also" sections have accurate cross-links

## Actions

### 1. Verify all internal links

Run this check across all new docs:

```bash
# Find all markdown links in docs/
grep -roh '\[.*\](\.\.\/[^)]*\.md\|[^)]*\.md)' docs/ --include="*.md" | \
  grep -v cursor-prompts | sort -u
```

For each link found, verify the target file exists. Fix any broken links.

### 2. Verify all YAML frontmatter

Every doc in the new structure (except cursor-prompts and reference/) MUST have:

```yaml
---
last-verified: 2026-02-17
sources:
  - path/to/source.py
phases: [N, M, ...]
---
```

Check each file:

```bash
for f in docs/architecture/*.md docs/api/*.md docs/services/*.md docs/features/*.md docs/operations/*.md docs/development/*.md docs/index.md; do
  echo "--- $f ---"
  head -6 "$f"
  echo
done
```

Fix any file missing the frontmatter block.

### 3. Verify "See Also" sections

Every doc should end with a "See Also" section containing 2-5 relevant cross-links. Check that:
- Architecture docs link to service docs and API docs
- Service docs link to the architecture overview and relevant feature docs
- Feature docs link to relevant API endpoint docs and service docs
- Operations docs link to relevant service docs
- Development docs link to operations (deployment) and testing

### 4. Verify no stale references

Search for references to deleted concepts:

```bash
# Should return 0 results outside of reference/ and cursor-prompts/
grep -r "delivery_worker\|dispatcher" docs/ --include="*.md" \
  | grep -v cursor-prompts | grep -v reference/
```

```bash
# Should return 0 results for old file names
grep -r "ARCHITECTURE\.md\|REFERENCE_ARCHITECTURE\.md\|PROJECT_MAP\.md\|API_REFERENCE\.md\|RUNBOOK\.md" \
  docs/ --include="*.md" | grep -v cursor-prompts
```

### 5. Build a link map

Create a simple verification that the doc tree is fully connected. Every doc should be reachable from `docs/index.md` via links.

```bash
# List all .md files in the new structure
find docs/architecture docs/api docs/services docs/features docs/operations docs/development -name "*.md" | sort

# Compare against links in index.md
grep -o '([^)]*\.md)' docs/index.md | tr -d '()' | sort
```

Every file in the first list should appear in the second list (as a relative path from docs/).

### 6. Final count

Report the final documentation inventory:

```bash
echo "=== Documentation Inventory ==="
echo "Architecture: $(ls docs/architecture/*.md | wc -l) files"
echo "API: $(ls docs/api/*.md | wc -l) files"
echo "Services: $(ls docs/services/*.md | wc -l) files"
echo "Features: $(ls docs/features/*.md | wc -l) files"
echo "Operations: $(ls docs/operations/*.md | wc -l) files"
echo "Development: $(ls docs/development/*.md | wc -l) files"
echo "Reference: $(ls docs/reference/*.md | wc -l) files"
echo "Index: 1 file"
echo "Total: $(find docs/ -maxdepth 2 -name '*.md' ! -path '*/cursor-prompts/*' | wc -l) files"
```

Expected totals:
- Architecture: 3
- API: 6
- Services: 7
- Features: 6
- Operations: 5
- Development: 4
- Reference: 4
- Index: 1
- **Total: 36 files**
