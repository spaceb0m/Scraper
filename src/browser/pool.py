# src/browser/pool.py
from __future__ import annotations

import asyncio
from dataclasses import dataclass
from playwright.async_api import Browser, BrowserContext, Page


@dataclass
class PooledContext:
    context: BrowserContext
    page: Page


class ContextPool:
    """Semáforo de contextos Playwright: limita N contextos simultáneos."""

    def __init__(self, browser: Browser, n: int, timeout_ms: int) -> None:
        self._browser = browser
        self._semaphore = asyncio.Semaphore(n)
        self._timeout_ms = timeout_ms

    async def acquire(self) -> PooledContext:
        """Espera un slot libre, crea un nuevo contexto+página y lo devuelve."""
        await self._semaphore.acquire()
        try:
            context = await self._browser.new_context(
                locale="es-ES",
                user_agent=(
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/122.0.0.0 Safari/537.36"
                ),
            )
            page = await context.new_page()
            page.set_default_timeout(self._timeout_ms)
            return PooledContext(context=context, page=page)
        except Exception:
            self._semaphore.release()
            raise

    async def release(self, pooled: PooledContext) -> None:
        """Cierra el contexto y libera el slot."""
        try:
            await pooled.context.close()
        finally:
            self._semaphore.release()
