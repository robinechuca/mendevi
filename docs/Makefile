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

html:
	@echo "****************************************"
	@echo "************ Invoke Graphviz ***********"
	@echo "****************************************"
	@mkdir -p "$(SOURCEDIR)/_static/media"
	@dot -Tsvg "$(SOURCEDIR)/media/sql_database.dot" > "$(SOURCEDIR)/_static/media/sql_database.svg"

	# 	@mkdir -p "$(BUILDDIR)"/media
	# 	@dot -Tsvg "$(SOURCEDIR)"/media/sql_database.dot > "$(BUILDDIR)"/media/sql_database.svg

	@echo "****************************************"
	@echo "************* Invoke Sphinx ************"
	@echo "****************************************"
	@$(SPHINXBUILD) -M $@ "$(SOURCEDIR)" "$(BUILDDIR)" $(SPHINXOPTS) $(O)
