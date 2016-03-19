import io
import unittest
import yaml

from backup_tool.pipeline import BackupPipeline

class PipelineTest(unittest.TestCase):

  def setUp(self):
    with open('pipeline.yaml') as f:
      self.pipeline_data = yaml.load(f)

  def test_load(self):
    pipeline = BackupPipeline(self.pipeline_data['pipeline'], {})

  def test_forward(self):
    pipeline = BackupPipeline(self.pipeline_data['pipeline'], {})
    print(pipeline.forward({
      'connection': {
        'host': 'jbnas',
        'remote_user': 'jb',
        'dest_folder': '/data',
      },
      'folders': '/tmp/foo /tmp/bar /tmp/baz',
      'pipeline': pipeline
    }))
