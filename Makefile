.PHONY: help build serve

help:
	@echo "Available commands:"
	@echo "  make build  - Build the Vite assets, run JSON parser, and build Hugo"
	@echo "  make serve  - Start Hugo development server"
	@echo "  make update - Parse JSON and build Vite assets"

build: update
	hugo --minify

serve: update
	hugo server -D

update:
	uv run python json2hugo.py
	npm run build
