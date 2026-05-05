PYTHON ?= /Users/abashraf/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/bin/python3

.PHONY: test package terraform-fmt terraform-validate

test:
	PYTHONPATH=$(PWD) $(PYTHON) -m unittest discover -s tests

package:
	PYTHON=$(PYTHON) ./scripts/package_lambdas.sh

terraform-fmt:
	terraform fmt -recursive -check

terraform-validate:
	terraform init -backend=false
	terraform validate

