import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from urllib.request import Request, urlopen

REPO = Path(__file__).resolve().parent.parent
I18N_DIR = REPO / "app" / "assets" / "i18n"
BROWSER_I18N_DIR = REPO / "browser_extension" / "app" / "public" / "_locales"

API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")
API_URL = "https://api.deepseek.com/chat/completions"
MODEL = "deepseek-v4-pro"

LOCALES = {
    "en_US": "English (United States)",
    "ja_JP": "Japanese",
    "ru_RU": "Русский (Russian)",
    "zh_HK": "Traditional Chinese (Hong Kong)",
    "zh_TW": "Traditional Chinese (Taiwan)",
    "pt_BR": "Português (Brasil)",
}

SYSTEM_PROMPT_DESKTOP = """You are a professional software localization translator. Translate the UI text of the download manager "Ghost Downloader 3" from Simplified Chinese to {locale_name}.

Rules:
1. Placeholders such as {{0}} {{1}} {{2}} must be kept verbatim, with the same position and count
2. Keep HTML tags verbatim
3. Line-break markers must stay at the same position in the translation
4. Reference the terminology and tone of "Existing translations"
5. Strictly keep the === Context === grouping plus the "source = translation" output format
6. Only output the results for the to-translate part
7. Do not output explanations, comments, or markdown markup"""

SYSTEM_PROMPT_BROWSER = """You are a professional software localization translator. Translate the UI text of the "Ghost Downloader" browser extension from Simplified Chinese to {locale_name}.

"Existing translations" format: key = source -> translation (for reference of terminology and tone)
"To translate" format: key = source (a trailing # comment is a context hint, do not translate)

Rules:
1. Placeholders such as $1 $2 $NAME$ must be kept verbatim, with the same position and count
2. Reference the terminology and tone of "Existing translations"
3. Strictly keep the "key = translation" output format, one entry per line
4. Only output the results for the to-translate part
5. Do not output explanations, comments, or markdown markup"""


def escapeNewlines(s: str) -> str:
    return s.replace("\\", "\\\\").replace("\n", "\\n")


def unescapeNewlines(s: str) -> str:
    return re.sub(r"\\([n\\])", lambda m: "\n" if m[1] == "n" else "\\", s)


def parseTs(path: Path):
    tree = ET.parse(path)

    finished = []
    unfinished = []

    for ctx in tree.getroot().findall("context"):
        name = ctx.findtext("name") or ""
        for msg in ctx.findall("message"):
            source = msg.findtext("source") or ""
            t = msg.find("translation")
            text = t.text or ""
            if t.get("type") == "unfinished":
                unfinished.append((name, source, text))
            else:
                finished.append((name, source, text))

    return tree, finished, unfinished


def buildPrompt(finished, unfinished) -> str:
    lines = []

    if finished:
        lines.append("## Existing translations")
        currentContext = None
        for ctx, src, trans in finished:
            if ctx != currentContext:
                lines.append(f"=== {ctx} ===")
                currentContext = ctx
            lines.append(f"{escapeNewlines(src)} = {escapeNewlines(trans)}")
        lines.append("")

    lines.append("## To translate")
    currentContext = None
    for ctx, src, existing in unfinished:
        if ctx != currentContext:
            lines.append(f"=== {ctx} ===")
            currentContext = ctx
        rhs = escapeNewlines(existing) if existing else ""
        lines.append(f"{escapeNewlines(src)} = {rhs}")

    return "\n".join(lines)


def fetchTranslation(system: str, user: str) -> str:
    payload = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "reasoning_effort": "low",
        "max_tokens": 16384,
    }
    req = Request(
        API_URL,
        data=json.dumps(payload).encode(),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {API_KEY}",
        },
    )
    with urlopen(req, timeout=600) as resp:
        body = json.loads(resp.read())
    return body["choices"][0]["message"]["content"]


def parseResponse(text: str) -> dict[tuple[str, str], str]:
    translations = {}
    currentContext = ""
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("=== ") and line.endswith(" ==="):
            currentContext = line[4:-4]
            continue
        if " = " in line:
            srcEsc, transEsc = line.split(" = ", 1)
            transEsc = transEsc.strip()
            if transEsc:
                src = unescapeNewlines(srcEsc.strip())
                trans = unescapeNewlines(transEsc)
                translations[(currentContext, src)] = trans
    return translations


def setTranslations(tree: ET.ElementTree, translations: dict) -> int:
    count = 0
    for ctx in tree.getroot().findall("context"):
        name = ctx.findtext("name") or ""
        for msg in ctx.findall("message"):
            t = msg.find("translation")
            if t.get("type") != "unfinished":
                continue
            source = msg.findtext("source") or ""
            key = (name, source)
            if key in translations:
                t.text = translations[key]
                del t.attrib["type"]
                count += 1
    return count


def saveTs(tree: ET.ElementTree, path: Path) -> None:
    ET.indent(tree.getroot(), space="    ")
    raw = ET.tostring(tree.getroot(), encoding="unicode")
    path.write_text(
        '<?xml version="1.0" encoding="utf-8"?>\n'
        "<!DOCTYPE TS>\n"
        f"{raw}\n",
        encoding="utf-8",
    )


def translateLocale(locale: str, localeName: str) -> None:
    tsPath = I18N_DIR / f"gd3.{locale}.ts"
    if not tsPath.exists():
        print(f"[{locale}] .ts not found — run sync_i18n_res.py first")
        return

    tree, finished, unfinished = parseTs(tsPath)
    if not unfinished:
        print(f"[{locale}] Nothing to translate")
        return

    print(f"[{locale}] {len(unfinished)} unfinished, {len(finished)} reference …")

    system = SYSTEM_PROMPT_DESKTOP.format(locale_name=localeName)
    user = buildPrompt(finished, unfinished)
    print(f"[{locale}] Calling API ({len(user)} chars) …")

    response = fetchTranslation(system, user)
    translations = parseResponse(response)
    count = setTranslations(tree, translations)
    saveTs(tree, tsPath)

    missed = len(unfinished) - count
    status = "done" if missed == 0 else f"done ({missed} missed)"
    print(f"[{locale}] {status}: {count}/{len(unfinished)} filled")


def checkLocales(locales: dict[str, str]) -> int:
    total = 0
    for locale in locales:
        tsPath = I18N_DIR / f"gd3.{locale}.ts"
        if not tsPath.exists():
            print(f"  {locale}: .ts not found")
            continue
        _, _, unfinished = parseTs(tsPath)
        total += len(unfinished)
        if unfinished:
            print(f"  {locale}: {len(unfinished)} unfinished")
        else:
            print(f"  {locale}: up to date")
    return total


def parseBrowserMessages(path: Path) -> dict[str, dict]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def buildBrowserPrompt(
    source: dict[str, dict],
    existing: dict[str, dict],
    untranslated: dict[str, dict],
) -> str:
    lines = []

    if existing:
        lines.append("## Existing translations")
        for key, entry in existing.items():
            src = source.get(key, {}).get("message", "")
            lines.append(f"{key} = {src} → {entry['message']}")
        lines.append("")

    lines.append("## To translate")
    for key, entry in untranslated.items():
        desc = entry.get("description")
        hint = f"  # {desc}" if desc else ""
        lines.append(f"{key} = {entry['message']}{hint}")

    return "\n".join(lines)


def parseBrowserResponse(text: str) -> dict[str, str]:
    translations = {}
    for raw in text.split("\n"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        if " = " in line:
            key, trans = line.split(" = ", 1)
            trans = trans.strip()
            if trans:
                translations[key.strip()] = trans
    return translations


BROWSER_LOCALE_MAP = {
    "en_US": "en_US",
    "ja_JP": "ja",
    "ru_RU": "ru",
    "zh_HK": "zh_HK",
    "zh_TW": "zh_TW",
    "pt_BR": "pt_BR",
}


def translateBrowserLocale(locale: str, localeName: str) -> None:
    chromeLocale = BROWSER_LOCALE_MAP.get(locale, locale)
    sourceDir = BROWSER_I18N_DIR / "zh_CN"
    targetDir = BROWSER_I18N_DIR / chromeLocale

    source = parseBrowserMessages(sourceDir / "messages.json")
    if not source:
        print(f"[browser:{locale}] source messages.json not found")
        return

    existing = parseBrowserMessages(targetDir / "messages.json")
    untranslated = {k: v for k, v in source.items() if k not in existing}
    if not untranslated:
        print(f"[browser:{locale}] Nothing to translate")
        return

    print(f"[browser:{locale}] {len(untranslated)} untranslated, {len(existing)} reference …")

    system = SYSTEM_PROMPT_BROWSER.format(locale_name=localeName)
    user = buildBrowserPrompt(source, existing, untranslated)
    print(f"[browser:{locale}] Calling API ({len(user)} chars) …")

    response = fetchTranslation(system, user)
    translations = parseBrowserResponse(response)

    merged = {**existing}
    filled = 0
    for key, trans in translations.items():
        if key in source:
            merged[key] = {"message": trans}
            if desc := source[key].get("description"):
                merged[key]["description"] = desc
            filled += 1

    targetDir.mkdir(parents=True, exist_ok=True)
    (targetDir / "messages.json").write_text(
        json.dumps(merged, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    missed = len(untranslated) - filled
    status = "done" if missed == 0 else f"done ({missed} missed)"
    print(f"[browser:{locale}] {status}: {filled}/{len(untranslated)} filled")


def checkBrowserLocales(locales: dict[str, str]) -> int:
    total = 0
    source = parseBrowserMessages(BROWSER_I18N_DIR / "zh_CN" / "messages.json")
    if not source:
        print("  browser: source messages.json not found")
        return 0
    for locale in locales:
        chromeLocale = BROWSER_LOCALE_MAP.get(locale, locale)
        existing = parseBrowserMessages(BROWSER_I18N_DIR / chromeLocale / "messages.json")
        missing = len(source) - len(existing)
        total += max(missing, 0)
        if missing > 0:
            print(f"  browser:{locale}: {missing} untranslated")
        else:
            print(f"  browser:{locale}: up to date")
    return total


def main() -> int:
    args = sys.argv[1:]
    check = "--check" in args
    browser = "--browser" in args
    targets = [a for a in args if not a.startswith("-")]

    if targets:
        invalid = [t for t in targets if t not in LOCALES]
        if invalid:
            print(f"Unknown locales: {', '.join(invalid)}", file=sys.stderr)
            print(f"Available: {', '.join(LOCALES)}", file=sys.stderr)
            return 1
        locales = {k: LOCALES[k] for k in targets}
    else:
        locales = LOCALES

    if check:
        total = checkBrowserLocales(locales) if browser else checkLocales(locales)
        return 0 if total == 0 else 2

    if not API_KEY:
        print("Set DEEPSEEK_API_KEY environment variable", file=sys.stderr)
        return 1

    translateFn = translateBrowserLocale if browser else translateLocale

    failed = False
    with ThreadPoolExecutor(max_workers=len(locales)) as pool:
        futures = {
            pool.submit(translateFn, loc, name): loc
            for loc, name in locales.items()
        }
        for fut in as_completed(futures):
            loc = futures[fut]
            try:
                fut.result()
            except Exception as exc:
                failed = True
                print(f"[{loc}] ERROR: {exc}", file=sys.stderr)

    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
