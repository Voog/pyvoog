from blinker import Namespace

_signals = Namespace()

jwt_decoded = _signals.signal('jwt_decoded')
