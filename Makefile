.PHONY: demo demo-ops demo-audit test

demo:
	python3 -m assaystone demo

demo-ops:
	python3 -m assaystone demo ops

demo-audit:
	python3 -m assaystone demo audit

test:
	python3 -m unittest discover -s tests -t . -v
