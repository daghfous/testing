#!/usr/bin/env python

# This script will consume 'VITE_TOP_MENU_STATIC_CONFIG' env var and stringify the json payload.
# * load json, will exit in case of decode error.
# * dumps json without space in separator.
# * Add backslash in order to escape `"`, this is usefull as vite add double quote.
# * And finally print it.
# How to test it:
# $ export VITE_TOP_MENU_STATIC_CONFIG="$(cat <<'EOF'
# {
#           "key": "value",
#             "nested": {
#                     "a": 1,
#                         "b": "two   aaa"
#                           }
#             }
# EOF
# 
# )"
# $ ./frontend/json-stringify.py
# {\"key\":\"value\",\"nested\":{\"a\":1,\"b\":\"two   aaa\"}}
import os
import json
import sys
raw = os.getenv('VITE_TOP_MENU_STATIC_CONFIG', '{}')
data: str = ''
try:
    data = json.loads(raw)
except json.JSONDecodeError as e:
    print(f'Invalid JSON: {e}', file=sys.stderr)
    sys.exit(1)
dumps = json.dumps(data, separators=(',', ':'))
print(dumps.replace('"', '\\"'))
