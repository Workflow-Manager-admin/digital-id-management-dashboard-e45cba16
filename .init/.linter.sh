#!/bin/bash
cd /home/kavia/workspace/code-generation/digital-id-management-dashboard-e45cba16/digital_id_backend
source venv/bin/activate
flake8 .
LINT_EXIT_CODE=$?
if [ $LINT_EXIT_CODE -ne 0 ]; then
  exit 1
fi

