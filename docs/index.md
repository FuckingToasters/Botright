# Welcome to Botright!

For full documentation of changes visit [BotrightDocumentation](botright.md).
Except of these changes, you can use Botright after the [PlaywrightDocs](https://playwright.dev/python/docs/api/class-playwright)

## Installation

### Pip

[![PyPI version](https://badge.fury.io/py/botright.svg)](https://pypi.python.org/pypi/botright/)

```bash
pip install --upgrade pip
pip install botright
playwright install
```

## Usage

Once installed, you can `import` Botright in a Python script, and launch a firefox browser.

```py
import asyncio
import botright


async def main():
    botright_client = await botright.Botright()
    browser = await botright_client.new_browser()
    page = await browser.new_page()

    await page.goto("http://playwright.dev")
    print(await page.title())

    await botright_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

## First script

In our first script, we will navigate to `whatsmyuseragent.org` and take a screenshot in WebKit.

```py
import asyncio
import botright


async def main():
    botright_client = await botright.Botright()
    browser = await botright_client.new_browser()
    page = await browser.new_page()

    page.goto("http://whatsmyuseragent.org/")
    page.screenshot(path="example.png")

    await botright_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

By default, Botright runs the browsers in headless mode. To see the browser UI, pass the `headless=False` flag while launching botright/the browser.

```py
await botright.Botright(headless=False)
```

## Interactive mode (REPL)

You can launch the interactive python REPL:

```bash
python -m asyncio
```

and then launch Botright within it for quick experimentation:

```py
>>> import botright
>>> botright_client = await botright.Botright()
# Pass headless=False to botright.Botright() to see the browser UI
>>> browser = await botright_client.new_browser()
>>> page = await browser.new_page()
>>> await page.goto("http://whatsmyuseragent.org/")
>>> await page.screenshot(path="example.png")
>>> await botright_client.stop()
```

## Pyinstaller

You can use Botright with [Pyinstaller](https://www.pyinstaller.org/) to create standalone executables.

```py
# main.py
import asyncio
import botright


async def main():
    botright_client = await botright.Botright()
    browser = await botright_client.new_browser()
    page = await browser.new_page()

    page.goto("http://whatsmyuseragent.org/")
    page.screenshot(path="example.png")

    await botright_client.close()

if __name__ == "__main__":
    asyncio.run(main())
```

If you want to bundle browsers with the executables:

```bash
PLAYWRIGHT_BROWSERS_PATH=0 playwright install firefox
pyinstaller -F main.py
```

```batch
set PLAYWRIGHT_BROWSERS_PATH=0
playwright install firefox
pyinstaller -F main.py
```

```powershell
$env:PLAYWRIGHT_BROWSERS_PATH="0"
playwright install firefox
pyinstaller -F main.py
```

## Known issues

### Threading

Botright's API is not thread-safe. If you are using Botright in a multi-threaded environment, you should create a botright instance per thread. See [threading issue](https://github.com/microsoft/playwright-python/issues/623) for more details.