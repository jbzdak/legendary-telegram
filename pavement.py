import configparser
import os
import abc
from optparse import make_option

# from paver.easy import *
# import paver.doctools


# TODO:
# 1. Create a oneliner that loads a backup
# 2. Add dates to backup files
# 3. Test faster compression algorithm (see if it makes sense / pgzip?)
# 4. Get rid of paver stuff
# 5. Write up assumptions (key ids, keys locall on both machines, singing key unencrypted)
# 6. Delete old backups
# 7. Add syncing to gcloud

OPERATIONS = {}
CONNECTIONS = {}




class ConfigFileParser(object):
  def __init__(self, cp):
    super(ConfigFileParser, self).__init__()
    self.cp = cp

  @property
  def folders(self):
    cp = self.cp
    assert isinstance(cp, ConfigParser.ConfigParser)
    return cp.get("backup", "folders").split(";")

  @property
  def destination_host(self):
    cp = self.cp
    assert isinstance(cp, ConfigParser.ConfigParser)
    return cp.get("backup", "host")

  @property
  def destination_user(self):
    cp = self.cp
    assert isinstance(cp, ConfigParser.ConfigParser)
    return cp.get("backup", "remote_user")

  @property
  def destination_root_folder(self):
    cp = self.cp
    assert isinstance(cp, ConfigParser.ConfigParser)
    return cp.get("backup", "remote_folder")

  @property
  def gpg_encrypt_key_id(self):
    cp = self.cp
    assert isinstance(cp, ConfigParser.ConfigParser)
    return cp.get("backup", "encrypt_id")

  @property
  def gpg_sign_key_id(self):
    cp = self.cp
    assert isinstance(cp, ConfigParser.ConfigParser)
    return cp.get("backup", "sign_id")


# old: tar -c --to-stdout {folder} | pbzip2 -c | gpg --encrypt --recipient {encrypt_id} | gpg --sign --local-user {sign_id} | ssh {user}@{host} "cat >> {remote_folder}/{filename}.back.enc &&  gpg --verify {remote_folder}/{filename}.back.enc"

BACKUP_COMMAND_PATTERN = """
tar -c --to-stdout {folder} | pigz -c | gpg --encrypt --recipient {encrypt_id} --compress-algo none | ssh {user}@{host} "cat > {remote_folder}/{filename}.back.enc && sync"
"""


def sanitize_folder_name(folder):
  assert isinstance(folder, str)
  return folder.replace("/", "SLASH").replace("\0", 'NULL')


def do_backups(config):
  if not os.path.exists(config):
    raise ValueError("Config file must exits")
  cp = ConfigParser.ConfigParser()
  cp.read(config)

  cp = ConfigFileParser(cp)

  for f in cp.folders:
    command = BACKUP_COMMAND_PATTERN.format(
      folder=f,
      encrypt_id=cp.gpg_encrypt_key_id,
      sign_id=cp.gpg_sign_key_id,
      user=cp.destination_user,
      host=cp.destination_host,
      remote_folder=cp.destination_root_folder,
      filename=sanitize_folder_name(f)
    )
    print(command)
    sh(command)


if __name__ == "__main__":
  print(sys.argv)
  do_backups(sys.argv[1])
