import importlib
import sys

module, port = sys.argv[1], int(sys.argv[2])
importlib.import_module(f"crashpay.{module}").app.run(port=port)