PYTHON ?= python3

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
