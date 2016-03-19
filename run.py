import sys

import yaml
from backup_tool import executor

if __name__ == "__main__":

  e = executor.DefaultExecutor()
  with open(sys.argv[1]) as f:
    e.load_config(yaml.load(f))

  e.execute()