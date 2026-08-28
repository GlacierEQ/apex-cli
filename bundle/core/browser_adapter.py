"""
Universal Browser Adapter — Platform-agnostic browser automation
GlacierEQ APEX | computer-user core

Backends:
  - tasklet:  invoke_tool({toolName:'browser', args:{actions:[...]}})
  - puppeteer: Headless Chromium via puppeteer-core (Node.js)
  - playwright: Headless Chromium via playwright (Python)

Usage:
  from browser_adapter import get_backend
  b = get_backend()          # auto-detect
  b.navigate("https://...")
  b.fill("Email", "user@example.com")
  b.click("Sign in")
  b.screenshot("/tmp/shot.png")
  text = b.get_text()
  b.eval("document.title")
  b.close()
"""

import json
import os
import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any, Optional


class BrowserBackend(ABC):
    """Abstract browser interface — all backends implement this."""

    @abstractmethod
    def navigate(self, url: str) -> None: ...

    @abstractmethod
    def click(self, selector_or_label: str) -> None: ...

    @abstractmethod
    def fill(self, selector_or_label: str, value: str) -> None: ...

    @abstractmethod
    def type_text(self, text: str, delay: int = 50) -> None: ...

    @abstractmethod
    def press_key(self, key: str) -> None: ...

    @abstractmethod
    def wait(self, ms: int = 2000) -> None: ...

    @abstractmethod
    def screenshot(self, path: str) -> None: ...

    @abstractmethod
    def get_text(self, max_chars: int = 30000) -> str: ...

    @abstractmethod
    def eval_js(self, script: str) -> Any: ...

    @abstractmethod
    def get_url(self) -> str: ...

    @abstractmethod
    def get_cookies(self) -> list: ...

    @abstractmethod
    def close(self) -> None: ...


# ─── Tasklet Backend ─────────────────────────────────────────────────────────


class TaskletBackend(BrowserBackend):
    """Tasklet platform browser — uses invoke_tool API."""

    def __init__(self):
        pass

    def _invoke(self, actions: list) -> dict:
        return invoke_tool({"toolName": "browser", "args": {"actions": actions}})

    def navigate(self, url: str) -> None:
        self._invoke([{"navigate": {"url": url}}])

    def click(self, selector_or_label: str) -> None:
        self._invoke([{"click": {"query": selector_or_label}}])

    def fill(self, selector_or_label: str, value: str) -> None:
        self._invoke([{"fill": {"query": selector_or_label, "value": value}}])

    def type_text(self, text: str, delay: int = 50) -> None:
        for char in text:
            self._invoke([{"type": {"text": char}}])
            import time

            time.sleep(delay / 1000)

    def press_key(self, key: str) -> None:
        self._invoke([{"press": {"key": key}}])

    def wait(self, ms: int = 2000) -> None:
        self._invoke([{"wait": {"duration": ms}}])

    def screenshot(self, path: str) -> None:
        self._invoke([{"screenshot": {"path": path}}])

    def get_text(self, max_chars: int = 30000) -> str:
        result = self._invoke(
            [{"evaluate": {"script": f"document.body.innerText.substring(0, {max_chars})"}}]
        )
        return result.get("result", "")

    def eval_js(self, script: str) -> Any:
        result = self._invoke([{"evaluate": {"script": script}}])
        return result.get("result", "")

    def get_url(self) -> str:
        result = self._invoke([{"evaluate": {"script": "window.location.href"}}])
        return result.get("result", "")

    def get_cookies(self) -> list:
        result = self._invoke([{"evaluate": {"script": "JSON.stringify(document.cookie)"}}])
        return json.loads(result.get("result", "[]"))

    def close(self) -> None:
        pass  # Tasklet manages browser lifecycle


# ─── Puppeteer Backend (Node.js subprocess) ─────────────────────────────────

_PUPPETEER_SCRIPT = r"""
const puppeteer = require('puppeteer-core');

class Browser {
  constructor() {
    this.browser = null;
    this.page = null;
  }

  async launch() {
    this.browser = await puppeteer.launch({
      executablePath: process.env.CHROME_PATH || '/data/data/com.termux/files/usr/bin/chromium-browser',
      headless: 'new',
      args: [
        '--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage',
        '--disable-blink-features=AutomationControlled', '--window-size=1280,900'
      ]
    });
    this.page = await this.browser.newPage();
    await this.page.setViewport({ width: 1280, height: 900 });
    await this.page.evaluateOnNewDocument(() => {
      Object.defineProperty(navigator, 'webdriver', { get: () => false });
      window.chrome = { runtime: {} };
    });
    await this.page.setUserAgent(
      'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36'
    );
  }

  async navigate(url) { await this.page.goto(url, { waitUntil: 'networkidle2', timeout: 30000 }); }
  async click(sel) { await this.page.click(sel); }
  async fill(sel, val) { await this.page.type(sel, val, { delay: 50 }); }
  async typeText(text, delay) { await this.page.keyboard.type(text, { delay: delay || 50 }); }
  async pressKey(key) { await this.page.keyboard.press(key); }
  async wait(ms) { await new Promise(r => setTimeout(r, ms)); }
  async screenshot(path) { await this.page.screenshot({ path }); }
  async getText(maxChars) { return await this.page.evaluate((m) => document.body.innerText.substring(0, m), maxChars || 30000); }
  async evalJs(script) { return await this.page.evaluate(script); }
  async getUrl() { return this.page.url(); }
  async getCookies() { return await this.page.cookies(); }
  async close() { if (this.browser) await this.browser.close(); }
}

(async () => {
  const browser = new Browser();
  await browser.launch();

  const rl = require('readline').createInterface({ input: process.stdin });
  for await (const line of rl) {
    try {
      const req = JSON.parse(line);
      let result;
      switch (req.action) {
        case 'navigate': await browser.navigate(req.url); result = 'ok'; break;
        case 'click': await browser.click(req.selector); result = 'ok'; break;
        case 'fill': await browser.fill(req.selector, req.value); result = 'ok'; break;
        case 'type': await browser.typeText(req.text, req.delay); result = 'ok'; break;
        case 'press': await browser.pressKey(req.key); result = 'ok'; break;
        case 'wait': await browser.wait(req.ms || 2000); result = 'ok'; break;
        case 'screenshot': await browser.screenshot(req.path); result = 'ok'; break;
        case 'getText': result = await browser.getText(req.maxChars); break;
        case 'evalJs': result = await browser.evalJs(req.script); break;
        case 'getUrl': result = await browser.getUrl(); break;
        case 'getCookies': result = await browser.getCookies(); break;
        case 'setCookies': await browser.page.setCookie(...(req.cookies || [])); result = 'ok'; break;
        case 'saveCookies': { const c = await browser.getCookies(); result = JSON.stringify(c); break; }
        case 'close': await browser.close(); process.exit(0); break;
        default: result = { error: 'unknown action: ' + req.action };
      }
      process.stdout.write(JSON.stringify({ ok: true, result }) + '\n');
    } catch (e) {
      process.stdout.write(JSON.stringify({ ok: false, error: e.message }) + '\n');
    }
  }
})();
"""


class PuppeteerBackend(BrowserBackend):
    """Puppeteer backend — spawns Node.js subprocess with stdin/stdout IPC."""

    def __init__(self, cookie_file: Optional[str] = None):
        self._proc = None
        self._cookie_file = Path(cookie_file) if cookie_file else None
        self._init_node_script()
        self._launch()
        if self._cookie_file and self._cookie_file.exists():
            self._load_cookies()

    def _init_node_script(self):
        self._script_path = Path(tempfile.mktemp(suffix=".js"))
        self._script_path.write_text(_PUPPETEER_SCRIPT)

    def _launch(self):
        self._proc = subprocess.Popen(
            ["node", str(self._script_path)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, "NODE_PATH": "/data/data/com.termux/files/usr/lib/node_modules"},
        )
        import time

        time.sleep(3)

    def _send(self, cmd: dict) -> Any:
        self._proc.stdin.write(json.dumps(cmd) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        resp = json.loads(line)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error", "unknown error"))
        return resp.get("result")

    def save_cookies(self, path: Optional[str] = None) -> None:
        """Persist browser cookies to disk."""
        cookies = self.get_cookies()
        target = Path(path) if path else self._cookie_file
        if target:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(json.dumps(cookies, indent=2))

    def _load_cookies(self) -> None:
        """Load persisted cookies into browser."""
        if self._cookie_file and self._cookie_file.exists():
            try:
                cookies = json.loads(self._cookie_file.read_text())
                if cookies:
                    self._send({"action": "setCookies", "cookies": cookies})
            except Exception:
                pass
        self._proc.stdin.write(json.dumps(cmd) + "\n")
        self._proc.stdin.flush()
        line = self._proc.stdout.readline()
        resp = json.loads(line)
        if not resp.get("ok"):
            raise RuntimeError(resp.get("error", "unknown error"))
        return resp.get("result")

    def navigate(self, url: str) -> None:
        self._send({"action": "navigate", "url": url})

    def click(self, selector_or_label: str) -> None:
        self._send({"action": "click", "selector": selector_or_label})

    def fill(self, selector_or_label: str, value: str) -> None:
        self._send({"action": "fill", "selector": selector_or_label, "value": value})

    def type_text(self, text: str, delay: int = 50) -> None:
        self._send({"action": "type", "text": text, "delay": delay})

    def press_key(self, key: str) -> None:
        self._send({"action": "press", "key": key})

    def wait(self, ms: int = 2000) -> None:
        self._send({"action": "wait", "ms": ms})

    def screenshot(self, path: str) -> None:
        self._send({"action": "screenshot", "path": path})

    def get_text(self, max_chars: int = 30000) -> str:
        return self._send({"action": "getText", "maxChars": max_chars})

    def eval_js(self, script: str) -> Any:
        return self._send({"action": "evalJs", "script": script})

    def get_url(self) -> str:
        return self._send({"action": "getUrl"})

    def get_cookies(self) -> list:
        return self._send({"action": "getCookies"})

    def close(self) -> None:
        try:
            if self._cookie_file:
                self.save_cookies()
            self._send({"action": "close"})
        except Exception:
            pass
        if self._proc:
            self._proc.terminate()
        try:
            self._script_path.unlink()
        except Exception:
            pass


# ─── Auto-detect & Factory ──────────────────────────────────────────────────


def get_backend(backend: Optional[str] = None) -> BrowserBackend:
    """
    Get a browser backend.
    backend: 'tasklet', 'puppeteer', 'playwright', or None (auto-detect).
    """
    if backend == "tasklet":
        return TaskletBackend()
    if backend == "puppeteer":
        return PuppeteerBackend()

    # Auto-detect
    if os.environ.get("TASKLET_ENV"):
        return TaskletBackend()

    # Check if puppeteer-core is available
    try:
        result = subprocess.run(
            ["node", "-e", 'require("puppeteer-core")'],
            capture_output=True,
            env={**os.environ, "NODE_PATH": "/data/data/com.termux/files/usr/lib/node_modules"},
        )
        if result.returncode == 0:
            return PuppeteerBackend()
    except Exception:
        pass

    raise RuntimeError(
        "No browser backend available. Install puppeteer-core: npm install -g puppeteer-core"
    )
