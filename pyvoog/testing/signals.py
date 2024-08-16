from blinker import Namespace

_testing_signals = Namespace()

app_ctx_pushed = _testing_signals.signal('app_ctx_pushed')
