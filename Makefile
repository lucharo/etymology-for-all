.PHONY: hf-create hf-delete hf-squash hf-stage hf-push hf-deploy cf-deploy

HF_SPACE := lucharo/etymology
HF_REPO := /tmp/hf-etymology
DB_SRC := backend/data/etymdb.duckdb
DB_COMPRESSED := backend/data/etymdb.duckdb.zst

# ============================================================================
# HF Space deployment
# ============================================================================

# Full deploy: compress DB, stage files, push, squash history
hf-deploy: hf-compress hf-stage hf-push hf-squash
	@echo "Done! View at: https://huggingface.co/spaces/$(HF_SPACE)"

# Compress DB for faster upload (~300MB -> ~90MB)
hf-compress:
	@echo "Compressing database..."
	@zstd -19 -f $(DB_SRC) -o $(DB_COMPRESSED) 2>/dev/null || (echo "zstd not found, using uncompressed DB" && false) || true

# Stage files to temp repo
hf-stage:
	@echo "Staging files..."
	rm -rf $(HF_REPO)
	mkdir -p $(HF_REPO)/backend/data $(HF_REPO)/frontend $(HF_REPO)/cloudflare-worker
	cp Dockerfile README.md pyproject.toml uv.lock $(HF_REPO)/
	cp backend/*.py $(HF_REPO)/backend/
	@if [ -f $(DB_COMPRESSED) ]; then cp $(DB_COMPRESSED) $(HF_REPO)/backend/data/; else cp $(DB_SRC) $(HF_REPO)/backend/data/; fi
	cp -r frontend/* $(HF_REPO)/frontend/
	cp cloudflare-worker/* $(HF_REPO)/cloudflare-worker/
	cd $(HF_REPO) && git init && git lfs install
	cd $(HF_REPO) && echo "*.duckdb filter=lfs diff=lfs merge=lfs -text" > .gitattributes
	cd $(HF_REPO) && echo "*.zst filter=lfs diff=lfs merge=lfs -text" >> .gitattributes
	cd $(HF_REPO) && git add -A && git commit -m "Deploy"

# Push to HF Space
hf-push:
	cd $(HF_REPO) && git remote add origin https://huggingface.co/spaces/$(HF_SPACE) 2>/dev/null || true
	cd $(HF_REPO) && git push --force origin main

# Squash history to single commit (frees LFS storage from old versions)
hf-squash:
	@echo "Squashing history to free LFS storage..."
	uv run python -c "from huggingface_hub import HfApi; HfApi().super_squash_history('$(HF_SPACE)', repo_type='space')"

# ============================================================================
# HF Space management (rarely needed)
# ============================================================================

hf-create:
	uv run hf repo create etymology --repo-type space --space-sdk docker

hf-delete:
	@read -p "Delete HF Space? Type 'yes': " c && [ "$$c" = "yes" ] && uv run hf repo delete $(HF_SPACE) --repo-type space

# ============================================================================
# Cloudflare Worker
# ============================================================================
cf-deploy:
	cd cloudflare-worker && npx wrangler deploy

# ============================================================================
# Utilities
# ============================================================================

# Check all URLs in the project are valid
check-links:
	@echo "Checking URLs in project files..."
	@grep -rhoE 'https?://[^)"'"'"' <>]+' README.md CHANGELOG.md frontend/ .github/ 2>/dev/null | \
		sort -u | \
		grep -vE 'localhost|127\.0\.0\.1|fonts\.googleapis\.com$$|fonts\.gstatic\.com$$' | \
		while read url; do \
			status=$$(curl -sL -o /dev/null -w '%{http_code}' --max-time 10 "$$url" 2>/dev/null); \
			if [ "$$status" -ge 400 ] || [ "$$status" = "000" ]; then \
				echo "❌ $$status $$url"; \
			else \
				echo "✓ $$status $$url"; \
			fi; \
		done
