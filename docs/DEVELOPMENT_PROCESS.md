# Development Process Documentation

## Story File Management

### Gitignore Exclusion Reasoning

**Decision**: Story files in `docs/stories/` are excluded from version control via `.gitignore`

**Rationale**:

1. **Separation of Concerns**
   - Story files are project management artifacts, not source code
   - Code changes should be tracked separately from story/task tracking
   - Keeps git history focused on actual implementation changes

2. **Workflow Independence**
   - Stories may be managed in external tools (JIRA, Linear, etc.)
   - Story files in this repo serve as local development reference only
   - Updates to story status/notes don't require separate commits

3. **Reduced Git Noise**
   - Story updates (status changes, notes, etc.) happen frequently
   - Excluding them prevents cluttering commit history
   - Keeps PRs focused on code changes, not administrative updates

4. **Team Flexibility**
   - Different team members may maintain stories differently
   - Local story files can be customized without conflicts
   - Reduces merge conflicts on non-critical files

### Story Information in Version Control

While story files themselves aren't tracked, story information IS captured in:

1. **Commit Messages**: Reference story numbers and acceptance criteria
2. **PR Descriptions**: Include full story context and AC verification
3. **Code Comments**: Link to story numbers where relevant
4. **Test Descriptions**: Map tests to specific acceptance criteria

### Example Workflow

```bash
# Story file updated locally (not committed)
# Implementation committed with story context
git commit -m "feat: Implement global status bar (Story 1.1)

Implements Story 1.1: Global Status Bar Component

Acceptance Criteria:
- AC-1: Persistent header ✅
- AC-2: Health indicator ✅
...
"

# PR includes full story details in description
gh pr create --title "Story 1.1" --body "$(cat story-template.md)"
```

### Alternative Approaches Considered

1. **Track Story Files in Git**
   - ❌ Creates noise in git history
   - ❌ Potential merge conflicts
   - ❌ Mixes code changes with PM artifacts

2. **External Story Management Only**
   - ❌ Developers lose local reference
   - ❌ Story context not available during development
   - ❌ Harder to work offline

3. **Current Approach: Local Stories + Git Exclusion** ✅
   - ✅ Best of both worlds
   - ✅ Local reference available
   - ✅ Clean git history
   - ✅ Story context preserved in commits/PRs

### Best Practices

1. **Always reference story numbers in commits**
2. **Include AC verification in PR descriptions**
3. **Keep story files updated locally for reference**
4. **Export story summaries to PR descriptions before creating PR**
5. **Use story file templates for consistency**

---

**Last Updated**: 2025-09-30
**Owner**: Development Team
**Related**: `.gitignore`, Story 1.1 implementation
