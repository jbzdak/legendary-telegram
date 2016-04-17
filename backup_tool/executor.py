
import abc
import subprocess
import multiprocessing
from tempfile import NamedTemporaryFile

import math

from . import pipeline
from . import operations

class AbstractExecutor(object, metaclass=abc.ABCMeta):

  def __init__(self):
    super().__init__()
    self.pipelines = []
    self.folders = []
    self.hosts = {}
    self.executor_config = {}

  def load_config(self, global_config):
    self.executor_config = global_config['execution']
    self.connections = global_config['connection']
    self.connections[None] = None

    self.pipelines = {
      name: operations.get_operation(config, global_config, 'type')
      for name, config in global_config['pipelines'].items()
    }
    self.folders = [
      FolderExecutor(f, self) for f in global_config['folders']
    ]

  @abc.abstractmethod
  def execute(self):
    pass

class FolderExecutor(object):

  def __init__(self, folder_config: dict, executor: AbstractExecutor):
    self.config = folder_config
    self.executor = executor
    name = folder_config.get('file_name')
    if name is None:
      name = self.sanitize_folder_name(self.config['folders'])
    self.name = name
    self.compress_threads=None

  def sanitize_folder_name(self, folder):
    return folder.replace("/", "SLASH")\
      .replace("\0", 'NULL').replace(' ', "SPACE")

  def create_context(self):
    return {
      'folders': self.config['folders'],
      'connection': self.executor.connections[self.config['connection']],
      'pipeline': self.executor.pipelines[self.config['pipeline']],
      'file_name': self.name,
      'compress_threads': self.compress_threads
    }

  def verify(self):
    pipeline = self.executor.pipelines[self.config['pipeline']]
    pipeline.forward(self.create_context())

  def execute(self):
    pipeline = self.executor.pipelines[self.config['pipeline']]

    with NamedTemporaryFile(mode='w') as file:
      command = pipeline.forward(self.create_context())
      print(command)
      file.write(command)
      file.flush()
      subprocess.check_output(['bash', file.name])


def execute_folder(folder):
  folder.execute()

class DefaultExecutor(AbstractExecutor):

  def execute(self):
    jobs = self.executor_config.get('parralel_jobs', 1)
    for folder in self.folders:
      folder.verify()

    print ("*"*25)
    print ("Verification done")
    print ("*" * 25)

    if jobs == 1:
      for folder in self.folders:
        folder.execute()
    else:
      pool = multiprocessing.Pool(
        processes=jobs
      )

      for folder in self.folders:
        folder.compress_threads = int(math.ceil(multiprocessing.cpu_count()/jobs))
        pool.apply_async(execute_folder, args=(folder, ), error_callback=lambda e: print(e))
      pool.close()
      pool.join()

