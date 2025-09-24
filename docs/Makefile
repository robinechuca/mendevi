# Makefile for Sphinx documentation

SPHINXOPTS    =
SPHINXBUILD   = sphinx-build
SPHINXPROJ    = laueimproc
SOURCEDIR     = .
BUILDDIR     ?= build
TEMPLATEDIR   = config

clean:
	@echo "****************************************"
	@echo "************* Remove Build *************"
	@echo "****************************************"
	@rm -rf "$(BUILDDIR)"
	@rm -rf "$(SOURCEDIR)/_static"

html:
	@echo "****************************************"
	@echo "************ Invoke Graphviz ***********"
	@echo "****************************************"
	@mkdir -p "$(SOURCEDIR)/_static/media"
	@for dotfile in $(SOURCEDIR)/media/*.dot; do \
	    basefile=$$(basename "$$dotfile" .dot); \
	    echo "Generating SVG for $$basefile.dot..."; \
	    dot -Tsvg "$$dotfile" > "$(SOURCEDIR)/_static/media/$$basefile.svg"; \
	done
	@cp $(SOURCEDIR)/media/*.avif $(SOURCEDIR)/_static/media/
	@echo "****************************************"
	@echo "************* Invoke Sphinx ************"
	@echo "****************************************"
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
