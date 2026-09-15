VERSION ?= 0.1.0

.PHONY: bootstrap gen content-sample content web-assets test format

bootstrap: ## Resolve deps and run codegen (the platform folders are committed)
	flutter pub get
	$(MAKE) gen

gen: ## Regenerate drift code
	cd packages/sr_data && dart run build_runner build --delete-conflicting-outputs

content-sample: ## Tiny content DB from committed fixtures (no network)
	cd pipeline && uv run srp build --sample --version 0.0.0-sample \
		--out ../app/assets/content/sevenreadings.sqlite

content: ## Full content DB from pinned upstream sources
	cd pipeline && uv run srp build --version $(VERSION) \
		--out ../app/assets/content/sevenreadings.sqlite

web-assets: ## sqlite3.wasm + drift_worker.js for Flutter web
	tools/web-assets.sh

test:
	cd packages/sr_core && dart test
	cd packages/sr_data && flutter test
	cd pipeline && uv run pytest

format:
	dart format $$(git ls-files '*.dart')
	cd pipeline && uv run ruff format .
