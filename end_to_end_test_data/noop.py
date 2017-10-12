import stl.lib


class NoOp(stl.lib.Event):

  def Fire(self, *args):
    return True

  def Wait(self, *args):
    return True
