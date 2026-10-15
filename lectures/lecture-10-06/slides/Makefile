.PHONY: all
all: lambda1_vp.pdf

%.pdf: %.tex
	mkdir -p .build
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build $<
	pdflatex -interaction=nonstopmode -halt-on-error -output-directory=.build $<
	cp .build/$*.pdf $@
