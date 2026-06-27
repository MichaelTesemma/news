import asyncio
import logging
import os
import pathlib
import threading

logger = logging.getLogger(__name__)

_INITIALIZED = False
_LOOP = None
_LOOP_THREAD = None


def _ensure_loop():
    global _INITIALIZED, _LOOP, _LOOP_THREAD
    if _INITIALIZED:
        return
    _patch_camoufox_path()
    _LOOP = asyncio.new_event_loop()
    _LOOP_THREAD = threading.Thread(target=_LOOP.run_forever, daemon=True)
    _LOOP_THREAD.start()
    _INITIALIZED = True


def _patch_camoufox_path():
    import camoufox.pkgman as pkgman
    user_dir = pathlib.Path(os.path.expanduser("~")) / "Library" / "Caches" / "camoufox_user"
    pkgman.INSTALL_DIR = user_dir

    def patched_path(download_if_missing=True):
        return user_dir

    def patched_get_path(file):
        return os.path.abspath(os.path.join(str(user_dir), "Camoufox.app", "Contents", "Resources", file))

    pkgman.camoufox_path = patched_path
    pkgman.get_path = patched_get_path


def _run_async(coro):
    _ensure_loop()
    return asyncio.run_coroutine_threadsafe(coro, _LOOP).result()


class SyncPage:
    def __init__(self, page):
        self._page = page

    def goto(self, url, **kwargs):
        return _run_async(self._page.goto(url, **kwargs))

    def wait_for_timeout(self, timeout):
        _run_async(self._page.wait_for_timeout(timeout))

    def content(self):
        return _run_async(self._page.content())

    def close(self):
        try:
            _run_async(self._page.close())
        except Exception:
            pass

    def set_default_timeout(self, timeout):
        self._page.set_default_timeout(timeout)

    def wait_for_selector(self, selector, **kwargs):
        return _run_async(self._page.wait_for_selector(selector, **kwargs))

    def query_selector_all(self, selector):
        return _run_async(self._page.query_selector_all(selector))

    def query_selector(self, selector):
        return _run_async(self._page.query_selector(selector))

    def title(self):
        return _run_async(self._page.title())


class CamoufoxPage:
    def __init__(self, headless=True, viewport=None):
        self.headless = headless
        self.viewport = viewport or {"width": 1280, "height": 720}
        self._page = None

    def __enter__(self):
        from camoufox import AsyncCamoufox
        _ensure_loop()
        self._browser_ctx = AsyncCamoufox(headless=self.headless, humanize=False)
        self._browser = _run_async(self._browser_ctx.__aenter__())
        page = _run_async(self._browser.new_page())
        _run_async(page.set_viewport_size(self.viewport))
        page.set_default_timeout(30000)
        self._page = SyncPage(page)
        return self._page

    def __exit__(self, *args):
        if self._page:
            self._page.close()
        if self._browser:
            try:
                _run_async(self._browser_ctx.__aexit__(*args))
            except Exception:
                pass


def safe_goto(page, url, max_retries=3):
    for attempt in range(max_retries):
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=30000)
            page.wait_for_timeout(3000)
            html = page.content()
            if "security verification" not in html[:500].lower():
                return html
            logger.warning("Cloudflare challenge on %s (attempt %d)", url, attempt + 1)
            page.wait_for_timeout(5000)
        except Exception as e:
            if "EPIPE" in str(e) or "Target closed" in str(e):
                raise
            logger.warning("Page load failed %s (attempt %d): %s", url, attempt + 1, e)
            page.wait_for_timeout(3000)
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_timeout(8000)
    return page.content()
