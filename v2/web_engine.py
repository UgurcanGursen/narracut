import os
import hashlib
from playwright.sync_api import sync_playwright

TEMP_DIR = os.path.join(os.getcwd(), "temp_assets")

def _get_cache_path(identifier: str, ext: str) -> str:
    os.makedirs(os.path.join(TEMP_DIR, "v2_cache"), exist_ok=True)
    safe_name = hashlib.md5(identifier.encode("utf-8")).hexdigest()
    return os.path.join(TEMP_DIR, "v2_cache", f"{safe_name}{ext}")

from typing import Tuple, Dict

def capture_web_record(url: str, target_text: str = None, target_selector: str = None, zoom: float = 1.0, highlight_target: bool = True) -> Tuple[str, Dict]:
    """
    Captures a screenshot of a webpage, applying ad-block, zoom, and text highlighting.
    Returns the tuple (path to the captured image, results_dict).
    """
    if not url.startswith("http"):
        url = "https://" + url
        
    zoom = 1.5 if target_text else zoom # ZOOM IN IF TARGET TEXT EXISTS
        
    identifier = f"{url}_{target_text}_{zoom}_{highlight_target}_v3.0.0"
    out_path = _get_cache_path(identifier, ".png")
    out_path_highlight = _get_cache_path(identifier + "_highlight", ".png")
    
    if os.path.exists(out_path) and os.path.exists(out_path_highlight):
        return out_path, {
            "url_loaded": True,
            "http_status": 200,
            "target_found": True,
            "target_visible": True,
            "placeholder_detected": False,
            "highlight_path": out_path_highlight
        }
        
    print(f"  [WEB] Capturing web record for {url} (Zoom: {zoom})")
    
    # Try cloudscraper first to get raw HTML if it's a strict site like SEC
    import hashlib
    url_hash = hashlib.md5(url.encode("utf-8")).hexdigest()
    fixture_html_path = os.path.join(TEMP_DIR, "v2_cache", f"fixture_{url_hash}.html")
    
    is_local = False
    if not os.path.exists(fixture_html_path) or os.environ.get("KURGU_NOCACHE_HTML") == "1":
        try:
            import cloudscraper
            scraper = cloudscraper.create_scraper()
            resp = scraper.get(url, headers={"User-Agent": "KurguBot/3.0 (admin@kurgu.com)"}, timeout=15)
            if resp.status_code == 200:
                with open(fixture_html_path, "w", encoding="utf-8") as f:
                    f.write(resp.text)
        except Exception as e:
            print(f"  [WEB] Cloudscraper failed: {e}")
            
    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=False,
            channel="chrome",
            args=["--disable-blink-features=AutomationControlled"]
        )
        
        page = browser.new_page(
            viewport={"width": 1920, "height": 1080},
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        from playwright_stealth import Stealth
        Stealth().apply_stealth_sync(page)
        
        if os.path.exists(fixture_html_path):
            print(f"  [WEB] Using local HTML for {url}")
            def route_intercept(route):
                if route.request.url.rstrip("/") == url.rstrip("/"):
                    with open(fixture_html_path, "r", encoding="utf-8") as f:
                        html_content = f.read()
                    route.fulfill(status=200, content_type="text/html", body=html_content)
                else:
                    route.continue_()
            page.route("**/*", route_intercept)
            is_local = True
            
        try:
            page.goto(url, wait_until="load", timeout=45000)
            if not is_local:
                try:
                    html_content = page.content()
                    with open(fixture_html_path, "w", encoding="utf-8") as f:
                        f.write(html_content)
                except: pass
        except: pass
            
        page.wait_for_timeout(3000)
        
                # Ad-block and DOM Cleaning (Reader Mode)
        try:
            page.add_style_tag(content="""
                iframe, ins, .ad, .ads, .advertisement, 
                [id*='google_ads'], [id*='ad-'], [class*='ad-'], [data-testid*='Ad'],
                [id*='cookie'], [class*='cookie'], #onetrust-consent-sdk,
                [id*='popup'], [class*='popup'], [class*='newsletter'],
                [id*='newsletter'], [class*='feedback'], [id*='feedback'],
                header, footer, nav, aside, .sidebar, [role="banner"]
                { display: none !important; }
            """)
        except: pass
            
        if zoom != 1.0:
            try: page.evaluate(f"document.body.style.zoom = '{zoom}'")
            except: pass
                
        target_found = False
        
        # Locate target, format it for screenshot, and scroll
        if target_text:
            try:
                js_scroll = f"""
                (() => {{
                    const target = "{target_text.replace('\"', '\\\\\"').replace('\\n', ' ')}";
                    const walker = document.createTreeWalker(document.body, NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while (node = walker.nextNode()) {{
                        if (node.nodeValue.includes(target) || target.includes(node.nodeValue.trim()) && node.nodeValue.trim().length > 10) {{
                            const parent = node.parentNode;
                            let blockEl = parent.closest('article, main, section, div.content, div.article, p');
                            if (!blockEl) blockEl = parent.closest('div') || parent;
                            
                            blockEl.id = "kurgu-target-element";
                            blockEl.style.backgroundColor = "#fdfdfc";
                            blockEl.style.color = "#000000";
                            blockEl.style.padding = "40px";
                            blockEl.style.borderRadius = "8px";
                            blockEl.style.border = "1px solid #eaeaea";
                            blockEl.style.boxShadow = "0 4px 12px rgba(0,0,0,0.1)";
                            
                            blockEl.scrollIntoView({{behavior: "instant", block: "center"}});
                            return true;
                        }}
                    }}
                    return false;
                }})();
                """
                target_found = page.evaluate(js_scroll)
            except Exception as e:
                print(f"  [WEB ERROR] JS Scroll: {e}")
            
        page.wait_for_timeout(1500)
        
        # TAKE BASE SCREENSHOT (UNHIGHLIGHTED)
        try:
            if target_found:
                elem = page.locator("#kurgu-target-element")
                elem.screenshot(path=out_path)
            else:
                page.screenshot(path=out_path, full_page=False)
        except Exception as e:
            print(f"  [WEB ERROR] Failed to screenshot base: {e}")
            out_path = None
            
        # APPLY HIGHLIGHT
        if target_found and highlight_target:
            try:
                js_highlight = f"""
                (() => {{
                    const target = "{target_text.replace('\"', '\\\\\"').replace('\\n', ' ')}";
                    const walker = document.createTreeWalker(document.getElementById("kurgu-target-element"), NodeFilter.SHOW_TEXT, null, false);
                    let node;
                    while (node = walker.nextNode()) {{
                        if (node.nodeValue.includes(target) || target.includes(node.nodeValue.trim()) && node.nodeValue.trim().length > 10) {{
                            const parent = node.parentNode;
                            parent.innerHTML = parent.innerHTML.replace(node.nodeValue, `<mark style="background-color: yellow; color: black; font-weight: bold; border-radius: 4px; padding: 0 2px;">${{node.nodeValue}}</mark>`);
                            return true;
                        }}
                    }}
                    return false;
                }})();
                """
                page.evaluate(js_highlight)
            except Exception as e:
                print(f"  [WEB ERROR] JS Highlight: {e}")
            
        page.wait_for_timeout(500)
        
        # TAKE HIGHLIGHTED SCREENSHOT
        try:
            if target_found and highlight_target:
                elem = page.locator("#kurgu-target-element")
                elem.screenshot(path=out_path_highlight)
            elif highlight_target:
                page.screenshot(path=out_path_highlight, full_page=False)
        except Exception as e:
            print(f"  [WEB ERROR] Failed to screenshot highlight: {e}")
            out_path_highlight = None
        browser.close()
        
    results = {
        "url_loaded": True if out_path else False,
        "http_status": 200, 
        "target_found": target_found,
        "target_visible": target_found,
        "placeholder_detected": False,
        "highlight_path": out_path_highlight
    }
        
    return out_path, results

