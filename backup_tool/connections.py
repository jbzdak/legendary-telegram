
import abc

class Connection(object, metaclass=abc.ABCMeta):

  @abc.abstractmethod
  def wrap_operations(self, local, remote):
    pass

class SSHConnection(Connection):

  def wrap_operations(self, context: dict, local: str, remote: str):
    connection = context['connection']
    destination = "{}@{}".format(
      connection['remote_user'],
      connection['host']
    )

    return """
      {local} | ssh {destination} '{remote}'
    """.format(local=local, destination=destination, remote=remote).strip()

