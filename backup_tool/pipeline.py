
import abc

from . import operations

from . connections import (
  SSHConnection
)

@operations.register_operation('pipeline')
class BackupPipeline(operations.BackupPipelineOperation):

  def __init__(self, *args, **kwargs):
    self.local_operations = []
    self.remote_operations = []
    self.connection = None
    super().__init__(*args, **kwargs)


  def load_config(self, config: dict, global_config:dict):
    if config['connection'] != 'ssh':
      raise ValueError(
        "For now only SSH connection is supported (was: '{}')".format(
          config['connection']))

    for operation_cfg in config['local']:
      self.local_operations.append(
        operations.get_operation(operation_cfg, global_config))

    for operation_cfg in config['remote']:
      self.remote_operations.append(
        operations.get_operation(operation_cfg, global_config))

  def forward(self, context:dict) -> str:
    local = " | ".join(o.forward(context) for o in self.local_operations)
    remote = " && ".join(o.forward(context) for o in self.remote_operations)

    # No need for DI here as we allow only SSH now :)
    connection = SSHConnection()

    return connection.wrap_operations(context, local, remote)


  def backward(self, context:dict) -> str:
    return " | ".join(o.backward(context) for o in self.local_operations)
