from concurrent.futures import ThreadPoolExecutor


class StreamPool:
    """Shared thread pool for RTSP stream workers.

    A single pool sized to MAX_STREAMS keeps thread lifecycles bounded and
    centralised, replacing the previous per-stream QThread design.
    """

    def __init__(self, max_workers=16):
        self._executor = ThreadPoolExecutor(
            max_workers=max_workers, thread_name_prefix="rtsp"
        )

    def submit(self, fn, *args, **kwargs):
        return self._executor.submit(fn, *args, **kwargs)

    def shutdown(self, wait=True):
        self._executor.shutdown(wait=wait, cancel_futures=True)
