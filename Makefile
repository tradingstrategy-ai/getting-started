# Manually generate table of contents for Github README
# TODO: Does not work anymore?
toc:
	cat README.md | scripts/gh-md-doc.sh - 

trade-executor-clone:
	git clone --depth=1 --recursive git@github.com:tradingstrategy-ai/trade-executor.git deps/trade-executor
	

