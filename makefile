# makefile for building and publishing multi-arch images + git tags
SHELL := /bin/bash
# Detect dry-run: set to "n" if -n is in MAKEFLAGS, else empty
IS_DRY := $(findstring n,$(MAKEFLAGS))

#  basics (override via env or cli) 
IMAGE      ?= ghcr.io/FaiTheFairy/authentik-helper
PKG_VER  := $(shell python3 -c "import tomllib,sys; d=tomllib.load(open('pyproject.toml','rb')); print(d['project']['version'])" 2>/dev/null || echo 0.0.0)
VER ?= v$(PKG_VER)
PLATFORMS  ?= linux/amd64,linux/arm64
BUILDER    ?= multi
GIT_REMOTE ?= origin
REPO_URL   ?= https://github.com/FaiTheFairy/authentik-helper

# build metadata (used as --build-arg and OCI labels)
BUILD_VERSION ?= $(shell git describe --tags --always --dirty 2>/dev/null || echo 0unknown)
BUILD_COMMIT  ?= $(shell git rev-parse HEAD 2>/dev/null || echo unknown)
BUILD_DATE    ?= $(shell date -u "+%Y-%m-%dT%H:%M:%SZ")
BUILD_ARGS    := --build-arg BUILD_VERSION=$(BUILD_VERSION) \
                 --build-arg BUILD_COMMIT=$(BUILD_COMMIT) \
                 --build-arg BUILD_DATE=$(BUILD_DATE)
LABEL_ARGS    := --label org.opencontainers.image.version=$(BUILD_VERSION) \
                 --label org.opencontainers.image.revision=$(BUILD_COMMIT) \
                 --label org.opencontainers.image.created=$(BUILD_DATE)

# derive registry from image (everything before first slash)
REGISTRY   := $(shell echo $(IMAGE) | cut -d/ -f1)

# host arch helper (handy for single-arch builds on current machine)
UNAME_M    := $(shell uname -m)
ifeq ($(UNAME_M),x86_64)
HOSTARCH := amd64
else ifeq ($(UNAME_M),aarch64)
HOSTARCH := arm64
else
HOSTARCH := unknown
endif

.DEFAULT_GOAL := help

.PHONY: help
help:
	@echo ""
	@echo "targets:"
	@echo "  make buildx-setup         # ensure a named buildx builder exists and is selected"
	@echo "  make bump-patch           # bump patch version, commit, git tag, build & push docker images"
	@echo "  make bump-minor           # bump minor version, commit, git tag, build & push docker images"
	@echo "  make bump-major           # bump major version, commit, git tag, build & push docker images"
	@echo "  make login                # docker login to the registry from image"
	@echo "  make release-amd64        # build+push amd64 image tagged $(VER)-amd64"
	@echo "  make release-arm64        # build+push arm64 image tagged $(VER)-arm64"
	@echo "  make release-local-arch   # build+push image for this host's arch ($(HOSTARCH))"
	@echo "  make verify-arch          # verify both $(VER)-amd64 and $(VER)-arm64 exist"
	@echo "  make manifest             # create+push multi-arch $(VER) (and latest)"
	@echo "  make release              # one-shot multi-arch build+push (recommended)"
	@echo "  make git-tag              # create and push git tag $(VER) (use FORCE_TAG=1 to retag)"
	@echo ""
	@echo "vars you can override: IMAGE, VER, PLATFORMS, BUILDER, GIT_REMOTE, FORCE_TAG=1"

# version bump helpers (patch/minor/major)
.PHONY: bump-patch bump-minor bump-major _bump

bump-patch: ; @$(MAKE) _bump BUMP_KIND=patch
bump-minor: ; @$(MAKE) _bump BUMP_KIND=minor
bump-major: ; @$(MAKE) _bump BUMP_KIND=major

_bump:
	@set -euo pipefail; \
	echo ">>> Bumping version: $(BUMP_KIND)"; \
	if [ -z "$(IS_DRY)" ]; then \
		uv version --bump "$(BUMP_KIND)"; \
	else \
		echo "[DRY-RUN] uv version --bump '$(BUMP_KIND)'"; \
	fi; \
	NEW_VER=$$(python3 -c "import tomllib; print(tomllib.load(open('pyproject.toml','rb'))['project']['version'])"); \
	echo ">>> New version in pyproject.toml: $$NEW_VER"; \
	if [ -z "$(IS_DRY)" ]; then \
		git add pyproject.toml uv.lock 2>/dev/null || true; \
		if git diff --cached --quiet; then \
			echo ">>> No changes to commit (already at $$NEW_VER)"; \
		else \
			git commit -m "release: bump to $$NEW_VER"; \
		fi; \
	else \
		echo "[DRY-RUN] git add/commit pyproject.toml uv.lock"; \
	fi; \
	TAG="v$$NEW_VER"; \
	echo ">>> Creating git tag $$TAG"; \
	$(MAKE) $(if $(IS_DRY),-n,) git-tag VER="$$TAG" FORCE_TAG="$${FORCE_TAG-0}"; \
	echo ">>> Building & pushing Docker images for $$TAG"; \
	$(MAKE) $(if $(IS_DRY),-n,) release-amd64 VER="$$TAG"; \
	$(MAKE) $(if $(IS_DRY),-n,) release-arm64 VER="$$TAG"; \
	$(MAKE) $(if $(IS_DRY),-n,) manifest-imagetools VER="$$TAG"; \
	echo ">>> Done: $$TAG"

	
.PHONY: echo-ver
echo-ver:
	@echo "PKG_VER=$(PKG_VER)  VER=$(VER)"

# buildx builder 
.PHONY: buildx-setup
buildx-setup:
	@docker buildx inspect $(BUILDER) >/dev/null 2>&1 || docker buildx create --name $(BUILDER) --use
	@docker buildx use $(BUILDER)
	@docker buildx inspect --bootstrap >/dev/null

# registry login 
.PHONY: login
login:
	@echo "registry: $(REGISTRY)"
	@docker login $(REGISTRY)

# single-arch builds (push with arch suffix) -
.PHONY: release-amd64
release-amd64: buildx-setup
	docker buildx build \
	  --builder $(BUILDER) \
	  --platform linux/amd64 \
	  -t $(IMAGE):$(VER)-amd64 \
	  $(BUILD_ARGS) $(LABEL_ARGS) \
	  --push .

.PHONY: release-arm64
release-arm64: buildx-setup
	docker buildx build \
	  --builder $(BUILDER) \
	  --platform linux/arm64 \
	  -t $(IMAGE):$(VER)-arm64 \
	  $(BUILD_ARGS) $(LABEL_ARGS) \
	  --push .

# build for whatever this host actually is
.PHONY: release-local-arch
release-local-arch: buildx-setup
ifeq ($(HOSTARCH),unknown)
	$(error unsupported host arch "$(UNAME_M)"; set HOSTARCH=amd64 or HOSTARCH=arm64 explicitly)
endif
	docker buildx build \
	  --builder $(BUILDER) \
	  --platform linux/$(HOSTARCH) \
	  -t $(IMAGE):$(VER)-$(HOSTARCH) \
	  $(BUILD_ARGS) $(LABEL_ARGS) \
	  --push .

# verify arch images exist (remote) --
.PHONY: verify-arch
verify-arch:
	@echo "Checking $(IMAGE):$(VER)-amd64..."
	@docker buildx imagetools inspect $(IMAGE):$(VER)-amd64 >/dev/null
	@echo "Checking $(IMAGE):$(VER)-arm64..."
	@docker buildx imagetools inspect $(IMAGE):$(VER)-arm64 >/dev/null
	@echo "OK: both arch images present."

# compose manifest (two ways) 

# classic docker manifest (works fine on many registries)
.PHONY: manifest
manifest: verify-arch
	# versioned manifest
	docker manifest create $(IMAGE):$(VER) \
	  --amend $(IMAGE):$(VER)-amd64 \
	  --amend $(IMAGE):$(VER)-arm64
	docker manifest push $(IMAGE):$(VER)
	# latest pointer (optional)
	docker manifest create $(IMAGE):latest \
	  --amend $(IMAGE):$(VER)-amd64 \
	  --amend $(IMAGE):$(VER)-arm64
	docker manifest push $(IMAGE):latest

# recommended: use imagetools (buildx) to create the multi-arch manifest
.PHONY: manifest-imagetools
manifest-imagetools: verify-arch
	docker buildx imagetools create \
	  -t $(IMAGE):$(VER) \
	  $(IMAGE):$(VER)-amd64 \
	  $(IMAGE):$(VER)-arm64
	docker buildx imagetools create \
	  -t $(IMAGE):latest \
	  $(IMAGE):$(VER)-amd64 \
	  $(IMAGE):$(VER)-arm64

# all-in-one (only if you can build both arch on this host)
.PHONY: release-all
release-all: buildx-setup release-amd64 release-arm64 manifest-imagetools

# git tagging 
.PHONY: git-tag
git-tag:
ifeq ($(FORCE_TAG),1)
	@git tag -fa $(VER) -m "release: $(VER)"
else
	@if git rev-parse -q --verify "refs/tags/$(VER)" >/dev/null; then \
		echo "Tag $(VER) already exists. Use FORCE_TAG=1 to move it."; \
		exit 1; \
	else \
		git tag -a $(VER) -m "release: $(VER)"; \
	fi
endif
	git push $(GIT_REMOTE) $(VER)

