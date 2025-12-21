.PHONY: hf-init hf-deploy

HF_SPACE := lucharo/etymology
HF_REPO := /tmp/hf-etymology

# One-time setup: create HF Space (only run once)
hf-init:
	uv run hf repo create etymology --repo-type space --space-sdk docker
	@echo "Space created! Configure custom domain at: https://huggingface.co/spaces/$(HF_SPACE)/settings"

# Deploy updates to HF Spaces
hf-deploy:
	@echo "Deploying to HF Space: $(HF_SPACE)"
	@if [ -d $(HF_REPO)/.git ]; then cd $(HF_REPO) && git pull; else rm -rf $(HF_REPO) && git clone https://huggingface.co/spaces/$(HF_SPACE) $(HF_REPO); fi
	cp Dockerfile README.md pyproject.toml uv.lock $(HF_REPO)/
	mkdir -p $(HF_REPO)/backend $(HF_REPO)/frontend
	cp backend/*.py $(HF_REPO)/backend/
	cp frontend/* $(HF_REPO)/frontend/
	cd $(HF_REPO) && git add -A && git diff --cached --quiet || git commit -m "Deploy from local" && git push
	uv run hf upload $(HF_SPACE) backend/data/etymdb.duckdb backend/data/etymdb.duckdb --repo-type space
	@echo "Done! View at: https://huggingface.co/spaces/$(HF_SPACE)"
