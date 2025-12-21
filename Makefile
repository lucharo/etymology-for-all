.PHONY: hf-init hf-deploy

HF_SPACE := lucharo/etymology
HF_REMOTE := https://huggingface.co/spaces/$(HF_SPACE)

# One-time setup: create HF Space and add remote
hf-init:
	uv run hf repo create etymology --repo-type space --space-sdk docker
	git remote add hf $(HF_REMOTE) 2>/dev/null || git remote set-url hf $(HF_REMOTE)
	@echo "Space created! Remote 'hf' configured."
	@echo "Configure custom domain at: https://huggingface.co/spaces/$(HF_SPACE)/settings"

# Deploy updates to HF Spaces
hf-deploy:
	@echo "Deploying to HF Space: $(HF_SPACE)"
	git push hf main:main --force
	uv run hf upload $(HF_SPACE) backend/data/etymdb.duckdb backend/data/etymdb.duckdb --repo-type space
	@echo "Done! View at: https://huggingface.co/spaces/$(HF_SPACE)"
