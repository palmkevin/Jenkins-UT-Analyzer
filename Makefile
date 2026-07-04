# Developer convenience targets. The substance lives in scripts/ — these are thin, discoverable
# entry points. See CLAUDE.md "worktrees" for the parallel-dev model.

.PHONY: help worktree worktree-rm worktree-ls

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | sort \
	  | awk 'BEGIN {FS = ":.*?## "} {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

# Parallel in-container git worktrees: one devcontainer, an isolated venv + throwaway `uta_<name>`
# database per worktree, so concurrent `pytest -m "not live"` runs never contend.
worktree: ## Create a worktree: make worktree name=<x>  (branch <x>, db uta_<x>)
	@scripts/worktree.sh add "$(name)"

worktree-rm: ## Tear down a worktree: make worktree-rm name=<x>  (removes worktree, branch, db)
	@scripts/worktree.sh remove "$(name)"

worktree-ls: ## List worktrees
	@scripts/worktree.sh list
