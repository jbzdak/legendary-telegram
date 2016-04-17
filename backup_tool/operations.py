
import abc

import datetime
import os
import typing
from tempfile import NamedTemporaryFile

import subprocess
import multiprocessing

OPERATIONS = {}

def register_operation(name):
  def wrapper(type):
    OPERATIONS[name] = type
    return type
  return wrapper

def get_operation(operation_cfg:dict, global_config:dict, type_key='operation'):
  operation_name = operation_cfg[type_key]
  OperationClass = OPERATIONS[operation_name]
  operation = OperationClass(operation_cfg, global_config)
  return operation

class ConfigurationError(Exception):
  pass

class BackupPipelineOperation(object, metaclass=abc.ABCMeta):
  """
  A fancy name for at thing that produce shell snippets
  """

  def __init__(self, config: dict, global_config:dict):
    # self.cp = cp
    self.config = config
    self.global_config = global_config
    self.load_config(self.config, global_config)

  @classmethod
  def _assert_command_exits(cls, command):
    try:
      subprocess.check_output(['which', command])
    except subprocess.CalledProcessError:
      raise ConfigurationError("Command does not exits {}".format(command))

  def verify(self, context:dict):
    pass

  @property
  def extension(self):
    return None

  def load_config(self, config: dict, global_config:dict):
    pass

  @abc.abstractmethod
  def forward(self, context:dict) -> str:
    pass

  # @abc.abstractmethod
  def backward(self, context:dict) -> str:
    pass


def run_command(script, error):
  with NamedTemporaryFile(encoding="utf8", mode="w+") as file:
    try:
      file.write(script)
      file.flush()
      subprocess.check_output(['bash', file.name])
    except subprocess.CalledProcessError as e:
      raise ConfigurationError(error.format(
        e.output
      ))


def verify_folders_exist(folder_list: str):
  VERIFICATION_SCRIPT = """
    for glob in {folders};
    do
      if ! stat -t ${{glob}} >/dev/null 2>&1
      then
        echo ${{glob}}
        exit 1
      fi
    done
    """

  script = VERIFICATION_SCRIPT.format(folders=folder_list)
  error = "One of the backed-up folders didn't exist: '{}'"
  run_command(script, error)


@register_operation("tarsnap")
class TarsnapOperation(BackupPipelineOperation):

  FSCK_TARSNAP = """
    {exec} --fsck --keyfile {keyfile} --cachedir {cachedir}
  """.strip()

  RUN_TARSNAP = """
    {exec} -c --keyfile {keyfile} --cachedir {cachedir} -f {archive} {folders}
  """

  def __init__(self, config: dict, global_config: dict):
    super().__init__(config, global_config)

  def load_config(self, config: dict, global_config:dict):
    self.keyfile = config['keyfile']
    self.cachedir = config['cachedir']
    self.tarsnap_exec = config.get('executable', 'tarsnap')

  def verify(self, context: dict):
    folders = context['folders']
    verify_folders_exist(folders)
    if not os.path.exists(self.keyfile):
      raise ConfigurationError("Tarsnap keyfile  {} does not exist".format(self.keyfile))

    if not os.path.exists(self.keyfile):
      raise ConfigurationError("Tarsnap cachedir {} does not exist".format(self.cachedir))
    print("Running tarsnap fsck")
    self._assert_command_exits(self.tarsnap_exec)
    script = self.FSCK_TARSNAP.format(
      keyfile=self.keyfile,
      cachedir=self.cachedir,
      exec=self.tarsnap_exec
    )
    run_command(script, "Tarsnap fsck failed: {}")

  def backward(self, context: dict) -> str:
    return "tarsnap has no backward command"

  def forward(self, context: dict) -> str:
    return self.RUN_TARSNAP.format(
      keyfile=self.keyfile,
      cachedir=self.cachedir,
      exec=self.tarsnap_exec,
      folders=context['folders'],
      archive=context['file_name']
    )


@register_operation("tar")
class TarOperation(BackupPipelineOperation):

  def forward(self, context: dict) -> str:
    folders = context['folders']
    return "tar -c --to-stdout {}".format(folders)

  def backward(self, context: dict) -> str:
    raise NotImplementedError()

  @property
  def extension(self):
    return "tar"

  def verify(self, context:dict):
    verify_folders_exist(context['folders'])
    self._assert_command_exits("tar")

@register_operation('compress')
class CompressOperation(BackupPipelineOperation):

  ALGORITHM_COMMAND_MAP = {
    "bzip": "pbzip2 --to-stdout -{level}",
    "gzip": "pigz -i -b 1024 -p {threads} --to-stdout -{level}"
  }

  EXTENSIONS = {
    "bzip": "bz",
    "gzip": "gz"
  }

  def load_config(self, config: dict, global_config: dict):
    super().load_config(config, global_config)
    self.algorithm = config['algorithm']
    if self.algorithm not in self.ALGORITHM_COMMAND_MAP.keys():
      raise ValueError(
        "Unknown compression algorithm '{}'".format(self.algorithm)
      )
    self.level = config.get('level', '6')
    self.threads = config.get('threads', None)

  def forward(self, context: dict) -> str:
    threads = self.threads
    if self.threads is None:
      threads = context.get('compress_threads', multiprocessing.cpu_count())

    return self.ALGORITHM_COMMAND_MAP[self.algorithm].format(
      level=self.level, threads=threads
    )

  @property
  def extension(self):
    return self.EXTENSIONS[self.algorithm]

class _BaseGPGOperation(BackupPipelineOperation):

  def load_config(self, config: dict, global_config: dict):
    self.key_id = config['key']

  def verify(self, context: dict):
    self._assert_command_exits("gpg")
    try:
      with NamedTemporaryFile(mode='w') as file:
        file.write("echo foo bar | " + self.forward(context))
        file.flush()
        subprocess.check_output(['bash', file.name])
    except subprocess.CalledProcessError as e:
      raise ConfigurationError("Coudn't find key {}".format(
        self.key_id
      )) from e


@register_operation('gpg encrypt')
class GPGEncrypt(_BaseGPGOperation):

  def forward(self, context: dict) -> str:
    return """
      gpg --encrypt --recipient {key_id} --compress-algo none
    """.strip().format(key_id=self.key_id)

  @property
  def extension(self):
    return "enc"


@register_operation('gpg sign')
class GPGSign(_BaseGPGOperation):
  def forward(self, context: dict) -> str:
    return """
       gpg --sign --local-user {key_id} --compress-algo none
    """.strip().format(key_id=self.key_id)

  @property
  def extension(self):
    return "sign"


@register_operation('sync')
class Sync(BackupPipelineOperation):
  def forward(self, context: dict) -> str:
    return "sync"


@register_operation('save backup')
class SaveBackup(BackupPipelineOperation):

  def load_config(self, config: dict, global_config: dict):
    self.dest_file = self.config['dest_file']

  def generate_extensions(self, pipeline:'pipeline.BackupPipeline'):
    exts = (op.extension for op in pipeline.local_operations)
    return "." + ".".join(e for e in exts if e)

  def forward(self, context: dict) -> str:

    dest_folder = context['connection']['dest_folder']
    dest_file = context['file_name']
    date = datetime.datetime.now().isoformat("T")
    pipeline = context['pipeline']
    extensions = self.generate_extensions(pipeline)
    dest_file_final = self.dest_file.format(
      dest_folder=dest_folder,
      dest_filename=dest_file,
      date=date,
      extensions=extensions
    )
    context['remote_dest_file_path'] = dest_file_final
    return "cat > {}".format(dest_file_final)


@register_operation('push to cloud')
class PushToCloud(BackupPipelineOperation):
  def load_config(self, config: dict, global_config: dict):
    super().load_config(config, global_config)
    self.sync=config['sync']
    self.target=config['target']
    self.type=config['type']
    if self.type != "gcloud":
      raise ValueError("For now only gcloud is supported")

  def sync_operation(self, context):
    return "gsutil cp {file_name} {target}".format(
      file_name=context['remote_dest_file_path'],
      target=self.target
    )

  def async(self, command, context):
    return 'bash -c "nohup {command} > {file_name}.upload.log 2>&1 &"'.format(
      command=command,
      file_name=context['remote_dest_file_path'],
    )

  def forward(self, context: dict) -> str:
    command = self.sync_operation(context)
    if not self.sync:
      command = self.async(command, context)

    return command


