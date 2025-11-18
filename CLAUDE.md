# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This repository contains the **CCPM (Claude Code Project Management)** system - a project management framework designed to work within Claude Code environments. It manages the complete workflow from product requirements to GitHub issues through a file-based system.

## Architecture

The system is built around three core data structures:

1. **PRDs** (Product Requirement Documents) - Stored in `.claude/prds/` as markdown files with YAML frontmatter
2. **Epics** - Stored in `.claude/epics/{name}/epic.md` - group related work
3. **Tasks** - Stored in `.claude/epics/{name}/{number}-{slug}.md` - individual work items

All files use YAML frontmatter for metadata (name, status, timestamps, etc.). The system synchronizes this data bi-directionally with GitHub issues.

### Directory Structure
```
.claude/
├── prds/              # Product Requirement Documents
├── epics/             # Epics and their tasks
│   └── {epic-name}/
│       ├── epic.md    # Epic definition
│       ├── 001.md     # Task files (numbered)
│       └── 002.md
├── rules/             # Operational rules and standards
├── scripts/pm/        # Bash scripts for PM commands
└── commands/pm/       # Slash command definitions
```

## Core Workflow

The standard project lifecycle:

1. **Create PRD**: `/pm:prd-new <feature-name>` - Brainstorm requirements
2. **Parse to Epic**: `/pm:prd-parse <feature-name>` - Convert PRD to implementation plan
3. **Decompose**: `/pm:epic-decompose <epic-name>` - Break into specific tasks
4. **Sync**: `/pm:epic-sync <epic-name>` - Push to GitHub as issues
5. **Execute**: `/pm:epic-start <epic-name>` - Run tasks in parallel
6. **Track**: `/pm:status`, `/pm:standup`, `/pm:next` - Monitor progress

## Essential Commands

### Project Status & Navigation
- `/pm:status` - Overall project dashboard
- `/pm:standup` - Daily standup report
- `/pm:next` - Show next priority tasks
- `/pm:blocked` - Show blocked items

### Epic & Task Management
- `/pm:epic-show <name>` - Display epic and tasks
- `/pm:epic-status [name]` - Show progress
- `/pm:issue-start <num>` - Begin work on specific task
- `/pm:issue-status <num>` - Check task status

### Synchronization
- `/pm:sync [epic-name]` - Bi-directional sync with GitHub
- `/pm:import <issue-num>` - Import existing GitHub issues
- `/pm:validate` - Check system integrity

### Maintenance
- `/pm:search <query>` - Search across all content
- `/pm:clean` - Archive completed work
- `/pm:validate` - Check for issues

## Critical Rules to Follow

### Path Standards (`.claude/rules/path-standards.md`)
**NEVER use absolute paths** - Always use relative paths:
- ✅ Correct: `internal/auth/server.go`
- ❌ Wrong: `/Users/username/project/internal/auth/server.go`

This prevents leaking system information and ensures portability.

### GitHub Operations (`.claude/rules/github-operations.md`)
**ALWAYS verify repository** before GitHub operations:
```bash
remote_url=$(git remote get-url origin 2>/dev/null || echo "")
if [[ "$remote_url" == *"automazeio/ccpm"* ]]; then
  echo "❌ Cannot sync with template repository"
  exit 1
fi
```

**ALWAYS** check this before: `gh issue create`, `gh issue edit`, `gh issue comment`, `gh pr create`

### DateTime Handling (`.claude/rules/datetime.md`)
**Use REAL system time** for all timestamps:
```bash
CURRENT_DATE=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
```

- Format: `YYYY-MM-DDTHH:MM:SSZ` (ISO 8601 UTC)
- Never use placeholder dates
- Update `updated` field when modifying files
- Preserve `created` field in updates

### Language Requirements
**Always respond in Simplified Chinese** - All responses, documentation, comments, and messages must be in Simplified Chinese. This ensures consistency for the development team.

### Standard Patterns (`.claude/rules/standard-patterns.md`)

**Keep it simple:**
- Fail fast - check essentials only, don't over-validate
- Trust the system - gh CLI is usually authenticated
- Clear errors - say exactly what failed and how to fix
- Minimal output - show results, skip decoration

**Error messages format:**
```
❌ {What failed}: {Exact solution}
```

## File Formats

### Frontmatter Standard
All PRDs, Epics, and Tasks use YAML frontmatter:
```yaml
---
name: feature-name
status: backlog|in-progress|completed
created: 2024-01-15T14:30:45Z
updated: 2024-01-15T14:30:45Z
---
```

### Epic Files
- Location: `.claude/epics/{name}/epic.md`
- Contains: Epic definition, task breakdown preview
- Status: `backlog` → `in-progress` → `completed`

### Task Files
- Location: `.claude/epics/{name}/{number}-{slug}.md`
- Numbering: 001, 002, 003... (padded)
- Status: `todo` → `in-progress` → `blocked` → `completed`
- Dependencies: Use `depends_on: [001, 002]` field

## Configuration

### GitHub Integration
- Repository detection via `.claude/ccpm.config`
- Uses `gh` CLI for all GitHub operations
- Requires: `gh auth login` (already authenticated)
- Labels: `epic` (green), `task` (blue) created automatically

### Permissions (`.claude/settings.local.json`)
The system has extensive permissions including:
- Bash: Full access to shell operations
- Git/GitHub: Via gh CLI
- File operations: Read, Write, List
- Web access: github.com, web search

## Special Capabilities

### Parallel Execution
The system includes specialized agents:
- `code-analyzer` - For code review and bug investigation
- `test-runner` - For test execution and analysis
- `file-analyzer` - For log file and data analysis
- `parallel-worker` - For coordinated multi-task execution

Use `/pm:epic-start <epic-name>` to launch parallel task execution.

### Path Tools (`.claude/scripts/path-tools-README.md`)
Built-in utilities for:
- Path normalization (absolute → relative)
- Cross-project file references
- Path validation and cleanup

## Important Implementation Notes

### For Commands
1. Read relevant rule files before execution (especially `/rules/datetime.md`)
2. Follow minimal preflight checks from `/rules/standard-patterns.md`
3. Use relative paths per `/rules/path-standards.md`
4. Verify GitHub repo per `/rules/github-operations.md`
5. Create bash scripts in `.claude/scripts/pm/` for new commands
6. Create markdown definitions in `.claude/commands/pm/` for slash commands

### For File Operations
1. Always use `Read` tool before `Edit` or `Write`
2. Preserve frontmatter when editing files
3. Use UTC timestamps (Z suffix)
4. Never include absolute paths in content

### For GitHub Sync
1. Run `/pm:sync` regularly to keep local ↔ GitHub in sync
2. Check for conflicts and resolve explicitly
3. Update `last_sync` timestamp after successful sync

## Validation & Health Checks

Run `/pm:validate` to check:
- Directory structure integrity
- Orphaned files
- Broken references (task dependencies)
- Missing frontmatter

This should be run before major operations to catch issues early.

## Tips

- Start with `/pm:help` for command reference
- Use `/pm:next` to find available work
- Run `/pm:status` for quick project overview
- Check `.claude/rules/` directory for specific operational guidance
- The system is designed to be simple - trust the workflows and follow the rules

## Integration Notes

This system integrates with:
- **GitHub CLI** - For issue management
- **Git** - For version control
- **Claude Code Agents** - For parallel execution
- **File System** - For local data persistence

All synchronization happens through the gh CLI, ensuring GitHub is always the single source of truth for project state.
