
# NOTE: If sentry_sdk is installed, tracing will be enabled. Otherwise, your app will work as normal.

try:
    import sentry_sdk
    def trace(coro_fn):
        return sentry_sdk.trace(coro_fn)
except ImportError:
    def trace(coro_fn):
        # Noop
        return coro_fn
