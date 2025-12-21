.PHONY: hf-init hf-deploy

HF_SPACE := lucharo/etymology
HF_REPO := /tmp/hf-etymology

# One-time setup: create HF Space
hf-init:
	uv run hf repo create etymology --repo-type space --space-sdk docker
	@echo "Space created at: https://huggingface.co/spaces/$(HF_SPACE)"

# Deploy to HF Spaces
# We clone the HF repo to /tmp and remove .gitignore files so that:
# 1. Code is pushed via git (small files)
# 2. DuckDB is uploaded via `hf upload` (large file, uses HF's storage backend)
# This keeps DuckDB out of GitHub history while still deploying it to HF Spaces.
hf-deploy:
	@echo "Deploying to HF Space: $(HF_SPACE)"
	@if [ -d $(HF_REPO)/.git ]; then cd $(HF_REPO) && git pull; else rm -rf $(HF_REPO) && git clone https://huggingface.co/spaces/$(HF_SPACE) $(HF_REPO); fi
	rm -f $(HF_REPO)/.gitignore $(HF_REPO)/backend/.gitignore
	cp Dockerfile README.md pyproject.toml uv.lock $(HF_REPO)/
	mkdir -p $(HF_REPO)/backend $(HF_REPO)/frontend $(HF_REPO)/cloudflare-worker
	cp backend/*.py $(HF_REPO)/backend/
	cp frontend/* $(HF_REPO)/frontend/
	cp cloudflare-worker/* $(HF_REPO)/cloudflare-worker/
	cd $(HF_REPO) && git add -A && git diff --cached --quiet || git commit -m "Deploy from local" && git push
	uv run hf upload $(HF_SPACE) backend/data/etymdb.duckdb backend/data/etymdb.duckdb --repo-type space
	@echo "Done! View at: https://huggingface.co/spaces/$(HF_SPACE)"
