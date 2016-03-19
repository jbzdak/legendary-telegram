import os
import unittest
import uuid
from tempfile import gettempdir, NamedTemporaryFile

from backup_tool import operations


class TestTarOperation(unittest.TestCase):
  def setUp(self):
    super().setUp()
    # Config not neeed
    self.tar_operation = operations.TarOperation({}, {})

  def test_verify_false(self):
    name = os.path.join(gettempdir(), str(uuid.uuid4()))
    self.assertFalse(os.path.exists(name), "Random file did exits")
    with self.assertRaises(operations.ConfigurationError):
      self.tar_operation.verify({"folders": name})

  def test_verify_true(self):
    with NamedTemporaryFile() as file:
      self.tar_operation.verify({"folders": file.name})

  def test_verify_true_2(self):
    with NamedTemporaryFile() as file, NamedTemporaryFile() as file2:
      self.tar_operation.verify({"folders": file.name + " " + file2.name})

  def test_verify_false_2(self):
    name = os.path.join(gettempdir(), str(uuid.uuid4()))
    self.assertFalse(os.path.exists(name), "Random file did exits")
    with NamedTemporaryFile() as file, NamedTemporaryFile() as file2:
      with self.assertRaises(operations.ConfigurationError):
        self.tar_operation.verify({
          "folders": file.name + " " + file2.name + " " + name
        })

  def test_forward(self):
    self.assertEqual(
      self.tar_operation.forward({"folders": "/home/foo*"}).strip(),
      "tar -c --to-stdout /home/foo*"
    )


class TestGPGOperation(unittest.TestCase):
  @classmethod
  def setUpClass(cls):
    super().setUpClass()
    cls.old_gpg_home = os.environ.get('GNUPGHOME')
    cls.known_key_id = '55B16974'
    os.environ['GNUPGHOME'] = os.path.join(os.path.split(__file__)[0], 'gpg')

  @classmethod
  def tearDownClass(cls):
    super().tearDownClass()
    if cls.old_gpg_home is None:
      del os.environ['GNUPGHOME']
    else:
      os.environ['GNUPGHOME'] = cls.old_gpg_home


class TestEncrypt(TestGPGOperation):
  def setUp(self):
    super().setUp()

  def test_verify_positive(self):
    self.operation = operations.GPGEncrypt({
      "key": self.known_key_id}, {})
    self.operation.verify({})

  def test_verify_negative(self):
    self.operation = operations.GPGEncrypt({
      "key": 'foobar'}, {})
    with self.assertRaises(operations.ConfigurationError):
      self.operation.verify({})


class TestSign(TestGPGOperation):
  def setUp(self):
    super().setUp()

  def test_verify_positive(self):
    self.operation = operations.GPGSign({
      "key": self.known_key_id}, {})
    self.operation.verify({})

  def test_verify_negative(self):
    self.operation = operations.GPGSign({
      "key": 'foobar'}, {})
    with self.assertRaises(operations.ConfigurationError):
      self.operation.verify({})
