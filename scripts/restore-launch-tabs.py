#!/usr/bin/env python3
"""Restore the Aletheia launch tabs and refill everything via Kimi WebBridge.

Prereqs:
  - Browser open with the Kimi WebBridge extension connected (daemon on 127.0.0.1:10086)
  - You are logged in to dev.to, LinkedIn and Product Hunt in that browser

Usage:
  python3 scripts/restore-launch-tabs.py            # full restore
  python3 scripts/restore-launch-tabs.py --check    # only verify daemon + extension

What it does:
  1. Opens a tab group "Lancamento Aletheia" with dev.to / LinkedIn / Product Hunt
  2. Re-inserts the LinkedIn post into the composer (does NOT click Publish)
  3. Refills the Product Hunt launch form (does NOT submit)
  4. Uploads gallery assets on the "Images and media" step (best effort)

Nothing is published or submitted by this script. Final buttons are yours.
"""

import json
import sys
import time
import urllib.request
from pathlib import Path

DAEMON = "http://127.0.0.1:10086/command"
SESSION = "polygraph-launch"
ROOT = Path(__file__).resolve().parent.parent
LAUNCH = ROOT / "docs" / "launch"

DEVTO_DRAFT_EDIT = "https://dev.to/dashboard"  # open dashboard; draft is listed there
LINKEDIN_FEED = "https://www.linkedin.com/feed/"
PH_NEW_POST = "https://www.producthunt.com/posts/new"

GALLERY = [
    LAUNCH / "assets" / "gallery-terminal-verdicts.png",
    LAUNCH / "assets" / "gallery-per-task-table.png",
    LAUNCH / "assets" / "gallery-false-success-per-cli.png",
]
LOGO = LAUNCH / "assets" / "logo-240.png"


def cmd(action, **args):
    body = json.dumps({"action": action, "args": args, "session": SESSION}).encode()
    req = urllib.request.Request(DAEMON, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as r:
        out = json.loads(r.read())
    if not out.get("ok"):
        raise RuntimeError(f"{action} failed: {out.get('error')}")
    return out.get("data")


def evaluate(code):
    return cmd("evaluate", code=code).get("value")


def check():
    try:
        cmd("list_tabs")
        print("[ok] WebBridge daemon + extension connected")
        return True
    except Exception as e:
        print(f"[fail] WebBridge not reachable: {e}")
        print("Open the browser and click the Kimi WebBridge extension icon, then re-run.")
        return False


def linkedin_post_text():
    lines = (LAUNCH / "linkedin-post.md").read_text().splitlines()
    return "\n".join(lines[2:]).strip().strip("-").strip()


def restore_linkedin():
    print("[..] LinkedIn: opening composer and inserting post text")
    text = linkedin_post_text()
    js = """
(async()=>{
const b=[...document.querySelectorAll("button, [role=button]")].find(x=>/Começar publicação|Start a post/i.test(x.textContent));
if(!b) return "composer button not found — open the feed manually";
b.click();
let ed=null;
const findEd=(root,depth)=>{if(ed||depth>8)return;const c=root.querySelector("[contenteditable=true], .ql-editor");if(c){ed=c;return;}root.querySelectorAll("*").forEach(el=>{if(el.shadowRoot)findEd(el.shadowRoot,depth+1);});};
for(let i=0;i<16;i++){await new Promise(r=>setTimeout(r,500));findEd(document,0);if(ed)break;}
if(!ed) return "editor not found";
ed.focus();
document.execCommand("insertText", false, %s);
return "inserted "+ed.innerText.length+" chars";
})()
""" % json.dumps(text)
    print("   ", evaluate(js))


def fill_ph_text():
    print("[..] Product Hunt: filling main info")
    # start from URL field
    cmd("navigate", url=PH_NEW_POST)
    time.sleep(3)
    evaluate("""(()=>{const i=document.querySelector('input[name=url]');const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;i.focus();s.call(i,'https://github.com/JoaoPauloNA/Aletheia');i.dispatchEvent(new Event('input',{bubbles:true}));return 1;})()""")
    time.sleep(1)
    evaluate("""(()=>{const b=[...document.querySelectorAll('button')].find(x=>/Get started/i.test(x.textContent));b.click();return 1;})()""")
    time.sleep(4)

    def set_input(name, value, textarea=False):
        proto = "HTMLTextAreaElement" if textarea else "HTMLInputElement"
        js = """(()=>{const d=document.querySelector('%s[name=%s]');if(!d)return 'missing %s';
const s=Object.getOwnPropertyDescriptor(window.%s.prototype,'value').set;
d.focus();s.call(d,%s);d.dispatchEvent(new Event('input',{bubbles:true}));return 'ok';})()""" % (
            "textarea" if textarea else "input", name, name, proto, json.dumps(value))
        r = evaluate(js)
        if r != "ok":
            print(f"    [warn] field {name}: {r}")

    set_input("name", "Aletheia")
    set_input("tagline", 'Aletheia for coding agents: is "done" actually true?')
    set_input("description",
              'When a coding agent says "done, tests passing" — is it true? Aletheia runs your agent '
              'in a sandbox, injects hidden tests after the claim, and reports SOLVED vs FALSE_SUCCESS '
              'vs honest failure. Open source, works with any CLI.', textarea=True)
    comment = (LAUNCH / "producthunt-kit.md").read_text()
    marker = "## First comment (maker comment)"
    comment = comment.split(marker, 1)[1].split("## ", 1)[0].strip()
    set_input("commentBody", comment, textarea=True)

    # topics via autocomplete
    for tag in ["Developer Tools", "Artificial Intelligence", "Open Source"]:
        evaluate("""(()=>{const i=document.querySelector('input[name=topics]');const s=Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype,'value').set;i.focus();s.call(i,'');i.dispatchEvent(new Event('input',{bubbles:true}));return 1;})()""")
        time.sleep(0.6)
        cmd("key_type", text=tag)
        time.sleep(2.5)
        r = evaluate("""(()=>{const opt=[...document.querySelectorAll('[data-test^=add-topic]')].find(e=>e.textContent.trim().startsWith(%s));
if(!opt) return 'option not found';
['mousedown','mouseup','click'].forEach(t=>opt.dispatchEvent(new MouseEvent(t,{bubbles:true,cancelable:true})));
return 'ok';})()""" % json.dumps(tag))
        if r != "ok":
            print(f"    [warn] topic {tag}: {r}")
    cmd("send_keys", keys="escape")
    print("    main info filled (name, tagline, description, comment, 3 tags)")


def upload_ph_gallery():
    print("[..] Product Hunt: advancing to Images and media, uploading assets")
    r = evaluate("""(()=>{const b=[...document.querySelectorAll('button, a')].find(x=>/Next step/i.test(x.textContent));if(!b)return 'no next button';b.click();return 'ok';})()""")
    if r != "ok":
        print(f"    [warn] {r} — upload skipped; advance manually and re-run")
        return
    time.sleep(3)
    # NOTE: Chrome blocks programmatic file upload here (CDP "Not allowed",
    # because the PH inputs are display:none and the dialog requires a real
    # user gesture). We try anyway; if it fails, drag the files manually —
    # they are all in docs/launch/assets/.
    uploaded = 0
    for img in [LOGO, *GALLERY]:
        try:
            cmd("upload", selector="input[type=file]", files=[str(img)])
            print(f"    uploaded {img.name}")
            uploaded += 1
            time.sleep(2)
        except Exception as e:
            print(f"    [warn] upload {img.name}: blocked by browser")
            break
    if uploaded == 0:
        print(f"    → manual step: drag the 4 files from {LOGO.parent} into the PH gallery")


def main():
    if "--check" in sys.argv:
        sys.exit(0 if check() else 1)
    if not check():
        sys.exit(1)

    print("[..] Opening tab group")
    cmd("navigate", url=DEVTO_DRAFT_EDIT)
    cmd("navigate", url=LINKEDIN_FEED, new_tab=True)
    time.sleep(3)

    restore_linkedin()
    fill_ph_text()
    upload_ph_gallery()

    print()
    print("Done. Nothing was published or submitted.")
    print("Your moves: dev.to dashboard → Publish · LinkedIn composer → Publicar · Product Hunt → review + launch.")


if __name__ == "__main__":
    main()
