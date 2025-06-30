import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os
import time
import re
import asyncio
import requests
import xml.etree.ElementTree as ET
import urllib.robotparser

# Add BeautifulSoup for HTML parsing
from bs4 import BeautifulSoup

# crawl4ai imports
try:
    from crawl4ai import AsyncWebCrawler
    from crawl4ai.extraction_strategy import CosineStrategy
    CRAWL4AI_AVAILABLE = True
    print("✅ crawl4ai is available")
except ImportError as e:
    print(f"❌ crawl4ai not installed: {e}")
    print("Install with: pip install crawl4ai")
    CRAWL4AI_AVAILABLE = False
    exit(1)
except Exception as e:
    print(f"⚠️ crawl4ai import issue: {e}")
    print("Will attempt to continue...")
    CRAWL4AI_AVAILABLE = True

def check_robots_txt_compliance():
    """Check what URLs are actually allowed by robots.txt"""
    print("🤖 Checking robots.txt compliance...")
    
    try:
        # Parse Coles robots.txt
        rp = urllib.robotparser.RobotFileParser()
        rp.set_url("https://www.coles.com.au/robots.txt")
        rp.read()
        
        # Test URLs we want to use
        test_urls = [
            "https://www.coles.com.au/browse/baby/nappies-nappy-pants/nappies",
            "https://www.coles.com.au/browse/baby/nappies-nappy-pants", 
            "https://www.coles.com.au/browse/baby",
            "https://www.coles.com.au/sitemap/sitemap-specials.xml",
            "https://www.coles.com.au/specials"
        ]
        
        user_agent = "diaper-deals-bot"
        
        print("    Checking URL permissions:")
        allowed_urls = []
        
        for url in test_urls:
            is_allowed = rp.can_fetch(user_agent, url)
            status = "✅ ALLOWED" if is_allowed else "❌ BLOCKED"
            print(f"      {status}: {url}")
            
            if is_allowed:
                allowed_urls.append(url)
        
        print(f"    📋 Total allowed URLs: {len(allowed_urls)}")
        return allowed_urls
        
    except Exception as e:
        print(f"    ❌ Error checking robots.txt: {e}")
        # Fallback to conservative list
        return [
            "https://www.coles.com.au/browse/baby/nappies-nappy-pants/nappies",
            "https://www.coles.com.au/browse/baby/nappies-nappy-pants"
        ]

async def debug_sitemap_thoroughly():
    """Thoroughly debug the sitemap approach"""
    print("\n🗺️ DEBUGGING SITEMAP APPROACH")
    print("=" * 50)
    
    try:
        # First check if we can access sitemaps
        sitemap_urls = [
            "https://www.coles.com.au/sitemap.xml",  # Main sitemap
            "https://www.coles.com.au/sitemap/sitemap-specials.xml",  # Specials
            "https://www.coles.com.au/sitemap/sitemap-products.xml",  # Products
            "https://www.coles.com.au/sitemap/sitemap-browse.xml"     # Browse pages
        ]
        
        working_sitemaps = []
        
        for sitemap_url in sitemap_urls:
            try:
                print(f"  📋 Testing: {sitemap_url}")
                response = requests.get(sitemap_url, timeout=10)
                print(f"    Status: {response.status_code}")
                print(f"    Size: {len(response.text)} chars")
                
                if response.status_code == 200:
                    working_sitemaps.append((sitemap_url, response.text))
                    
                    # Parse and analyze
                    try:
                        root = ET.fromstring(response.text)
                        
                        # Check if it's a sitemap index or regular sitemap
                        if "sitemapindex" in root.tag:
                            print("    📂 This is a sitemap INDEX")
                            sitemaps = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}sitemap')
                            print(f"    Contains {len(sitemaps)} sub-sitemaps:")
                            for i, sm in enumerate(sitemaps[:5]):
                                loc = sm.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                                if loc is not None:
                                    print(f"      {i+1}. {loc.text}")
                        else:
                            print("    📄 This is a regular sitemap")
                            urls = root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url')
                            print(f"    Contains {len(urls)} URLs")
                            
                            # Look for nappy-related URLs
                            nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove']
                            nappy_urls = []
                            
                            for url_elem in urls:
                                loc = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                                if loc is not None:
                                    url_text = loc.text
                                    if any(keyword in url_text.lower() for keyword in nappy_keywords):
                                        nappy_urls.append(url_text)
                            
                            print(f"    🍼 Nappy-related URLs: {len(nappy_urls)}")
                            for url in nappy_urls[:3]:
                                print(f"      - {url}")
                                
                    except ET.ParseError as e:
                        print(f"    ❌ XML parsing error: {e}")
                        print(f"    📝 Content preview: {response.text[:200]}...")
                        
            except Exception as e:
                print(f"    ❌ Error accessing {sitemap_url}: {e}")
        
        print(f"\n  📊 Summary: {len(working_sitemaps)} working sitemaps found")
        return working_sitemaps
        
    except Exception as e:
        print(f"  ❌ Sitemap debugging error: {e}")
        return []

def debug_manual_allowed_pages():
    """Test only robots.txt allowed pages with manual requests"""
    print("\n📖 DEBUGGING ALLOWED BROWSE PAGES")
    print("=" * 50)
    
    # Only test URLs we know are allowed
    allowed_urls = [
        "https://www.coles.com.au/browse/baby/nappies-nappy-pants/nappies",
        "https://www.coles.com.au/browse/baby/nappies-nappy-pants",
        "https://www.coles.com.au/browse/baby"
    ]
    
    results = {}
    
    for url in allowed_urls:
        print(f"  🎯 Testing allowed URL: {url}")
        
        try:
            # Use respectful headers
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; diaper-deals-tracker/1.0; respectful-bot)',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                'Accept-Language': 'en-AU,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'DNT': '1',
                'Connection': 'keep-alive'
            }
            
            response = requests.get(url, headers=headers, timeout=15)
            
            print(f"    Status: {response.status_code}")
            print(f"    Content-Type: {response.headers.get('content-type', 'unknown')}")
            print(f"    Content-Length: {len(response.text)}")
            
            if response.status_code == 200:
                # Analyze content
                content_analysis = analyze_page_content(response.text, url)
                results[url] = {
                    'status': response.status_code,
                    'content': response.text,
                    'analysis': content_analysis
                }
                
                print(f"    ✅ Successfully retrieved content")
                print(f"    🍼 Nappy keywords found: {content_analysis['nappy_keywords_count']}")
                print(f"    💰 Price patterns found: {content_analysis['price_count']}")
                print(f"    🔐 Member-only indicators: {content_analysis['member_only_indicators']}")
                
            else:
                print(f"    ❌ HTTP Error: {response.status_code}")
                
        except Exception as e:
            print(f"    ❌ Request error: {e}")
    
    return results

def analyze_page_content(html_content, url):
    """Analyze page content for debugging"""
    analysis = {
        'nappy_keywords_count': 0,
        'price_count': 0,
        'member_only_indicators': [],
        'potential_product_selectors': [],
        'page_type': 'unknown'
    }
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        page_text = soup.get_text().lower()
        
        # Count nappy keywords
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove', 'rascal', 'tooshies']
        for keyword in nappy_keywords:
            count = page_text.count(keyword.lower())
            analysis['nappy_keywords_count'] += count
        
        # Count price patterns
        prices = re.findall(r'\$\d+(?:\.\d{2})?', html_content)
        analysis['price_count'] = len(prices)
        
        # Check for member-only indicators
        member_indicators = [
            'member price', 'member only', 'sign in to see', 'login to see',
            'flybuys member', 'member special', 'exclusive member'
        ]
        
        for indicator in member_indicators:
            if indicator in page_text:
                analysis['member_only_indicators'].append(indicator)
        
        # Identify potential product selectors
        potential_selectors = [
            '[data-testid*="product"]',
            '[data-cy*="product"]', 
            '.product-tile',
            '.product-card',
            '.product-item',
            'article',
            '[class*="tile"]'
        ]
        
        for selector in potential_selectors:
            elements = soup.select(selector)
            if elements:
                analysis['potential_product_selectors'].append({
                    'selector': selector,
                    'count': len(elements)
                })
        
        # Determine page type
        if 'nappies' in url:
            analysis['page_type'] = 'nappies_category'
        elif 'baby' in url:
            analysis['page_type'] = 'baby_category' 
        elif 'browse' in url:
            analysis['page_type'] = 'browse_page'
        
    except Exception as e:
        analysis['error'] = str(e)
    
    return analysis

async def debug_compliant_crawl():
    """Debug crawl4ai with only compliant URLs"""
    print("\n🕷️ DEBUGGING COMPLIANT CRAWLING")
    print("=" * 50)
    
    # Only use confirmed allowed URLs
    allowed_urls = check_robots_txt_compliance()
    
    if not allowed_urls:
        print("  ❌ No allowed URLs found!")
        return
    
    try:
        async with AsyncWebCrawler(verbose=True) as crawler:
            
            for url in allowed_urls[:2]:  # Test first 2 allowed URLs
                print(f"\n  🎯 Testing compliant crawl: {url}")
                
                try:
                    result = await crawler.arun(
                        url=url,
                        word_count_threshold=10,
                        bypass_cache=True,
                        # Conservative crawling - respect the site
                        js_code=[
                            "await new Promise(resolve => setTimeout(resolve, 2000));",
                            "window.scrollTo(0, document.body.scrollHeight/3);",
                            "await new Promise(resolve => setTimeout(resolve, 2000));",
                            "window.scrollTo(0, document.body.scrollHeight/2);",
                            "await new Promise(resolve => setTimeout(resolve, 2000));"
                        ],
                        wait_for="body",
                        delay_before_return_html=4,
                        # Respectful headers
                        headers={
                            'User-Agent': 'Mozilla/5.0 (compatible; diaper-deals-tracker/1.0; +https://github.com/pkamat25/diaper-deals-tracker)',
                            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
                            'Accept-Language': 'en-AU,en;q=0.5',
                            'DNT': '1'
                        }
                    )
                    
                    print(f"    📄 Content length: {len(result.html)}")
                    print(f"    🔗 Links found: {len(result.links) if hasattr(result, 'links') and result.links else 0}")
                    
                    # Check for blocking
                    blocking_indicators = ['incapsula', 'blocked', 'access denied', 'captcha', 'cloudflare']
                    html_lower = result.html.lower()
                    
                    blocked = False
                    for indicator in blocking_indicators:
                        if indicator in html_lower:
                            print(f"    🚫 BLOCKING DETECTED: {indicator}")
                            blocked = True
                    
                    if not blocked:
                        print("    ✅ No blocking detected")
                        
                        # Analyze what we got
                        analysis = analyze_crawled_content(result.html, url)
                        
                        print(f"    🍼 Nappy content found: {analysis['has_nappy_content']}")
                        print(f"    💰 Prices found: {analysis['price_count']}")
                        print(f"    📦 Potential products: {analysis['product_elements']}")
                        
                        # Save sample for manual inspection
                        debug_filename = f"debug_compliant_{url.split('/')[-1]}_{datetime.now().strftime('%H%M%S')}.html"
                        with open(debug_filename, 'w', encoding='utf-8') as f:
                            f.write(result.html)
                        print(f"    💾 Saved to {debug_filename}")
                    
                except Exception as e:
                    print(f"    ❌ Crawl error: {e}")
        
    except Exception as e:
        print(f"  ❌ Crawler setup error: {e}")

def analyze_crawled_content(html_content, url):
    """Analyze crawled content specifically for debugging"""
    analysis = {
        'has_nappy_content': False,
        'price_count': 0,
        'product_elements': 0,
        'member_only_detected': False,
        'recommendations': []
    }
    
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Check for nappy content
        nappy_keywords = ['napp', 'huggies', 'pampers', 'babylove']
        page_text = soup.get_text().lower()
        
        if any(keyword in page_text for keyword in nappy_keywords):
            analysis['has_nappy_content'] = True
        
        # Count prices
        prices = re.findall(r'\$\d+(?:\.\d{2})?', html_content)
        analysis['price_count'] = len(prices)
        
        # Count potential product elements
        product_selectors = [
            '[data-testid*="product"]', '.product-tile', '.product-card', 
            'article', '[class*="tile"]', '[class*="card"]'
        ]
        
        for selector in product_selectors:
            elements = soup.select(selector)
            if elements:
                analysis['product_elements'] += len(elements)
                break
        
        # Check for member-only pricing
        member_indicators = ['member price', 'sign in', 'login', 'flybuys']
        if any(indicator in page_text for indicator in member_indicators):
            analysis['member_only_detected'] = True
            analysis['recommendations'].append("Prices may only be visible to logged-in members")
        
        # Generate recommendations
        if analysis['has_nappy_content'] and analysis['price_count'] == 0:
            analysis['recommendations'].append("Nappy content found but no prices - check if prices load dynamically")
        
        if analysis['product_elements'] == 0:
            analysis['recommendations'].append("No product elements found - selectors may need updating")
        
        if not analysis['has_nappy_content']:
            analysis['recommendations'].append("No nappy content found - URL may not show nappies section")
    
    except Exception as e:
        analysis['error'] = str(e)
    
    return analysis

def is_valid_nappy_price(price_str):
    """Check if a price is realistic for nappies (between $5 and $100)"""
    try:
        price = float(price_str.replace('$', ''))
        return 5.0 <= price <= 100.0
    except:
        return False

async def debug_main():
    """Main debug function - fully compliant approach"""
    print("=" * 80)
    print("🔍 COMPLIANT DEBUG MODE - Respectful Website Analysis")
    print("⚖️ Only using robots.txt allowed methods")
    print("=" * 80)
    
    # Step 1: Check what's actually allowed
    print("\n1️⃣ CHECKING ROBOTS.TXT COMPLIANCE")
    allowed_urls = check_robots_txt_compliance()
    
    # Step 2: Debug sitemap approach (most legitimate)
    print("\n2️⃣ DEBUGGING SITEMAP APPROACH") 
    working_sitemaps = await debug_sitemap_thoroughly()
    
    # Step 3: Test allowed browse pages manually
    print("\n3️⃣ TESTING ALLOWED BROWSE PAGES")
    manual_results = debug_manual_allowed_pages()
    
    # Step 4: Test with crawl4ai on allowed URLs only
    print("\n4️⃣ TESTING COMPLIANT CRAWLING")
    await debug_compliant_crawl()
    
    # Step 5: Generate recommendations
    print("\n" + "=" * 80)
    print("🎯 COMPLIANT DEBUG RECOMMENDATIONS:")
    print("=" * 80)
    
    if working_sitemaps:
        print("✅ Sitemap approach is working - focus on this method")
        print("   → Parse sitemap URLs for nappy-related product pages")
        print("   → These are the most legitimate URLs to crawl")
    else:
        print("❌ No working sitemaps found")
    
    if allowed_urls:
        print(f"✅ {len(allowed_urls)} URLs are robots.txt compliant")
        print("   → Focus scraping efforts on these URLs only")
    else:
        print("❌ No compliant URLs found - check robots.txt")
    
    # Check manual results
    successful_manual = [url for url, data in manual_results.items() if data.get('status') == 200]
    if successful_manual:
        print(f"✅ {len(successful_manual)} URLs accessible via HTTP")
        
        # Check for member-only pricing
        member_only_detected = any(
            data['analysis'].get('member_only_indicators', []) 
            for data in manual_results.values()
        )
        
        if member_only_detected:
            print("🔐 MEMBER-ONLY PRICING DETECTED!")
            print("   → This is likely why no deals are found")
            print("   → Consider: Coles may require login to see special prices")
            print("   → Alternative: Focus on catalogue/PDF scraping instead")
        
        # Check for dynamic content
        no_prices_but_content = any(
            data['analysis'].get('nappy_keywords_count', 0) > 0 and 
            data['analysis'].get('price_count', 0) == 0
            for data in manual_results.values()
        )
        
        if no_prices_but_content:
            print("⚡ DYNAMIC CONTENT DETECTED!")
            print("   → Nappy content found but no prices in HTML")
            print("   → Prices likely load via JavaScript/AJAX")
            print("   → Need longer wait times or different approach")
    
    print("\n💡 NEXT STEPS:")
    print("1. Check if Coles requires member login for deal prices")
    print("2. Try increasing JavaScript wait times to 8-10 seconds")
    print("3. Focus on sitemap approach if working")
    print("4. Consider alternative: Coles catalogue PDF scraping")
    print("5. Test during different times (deals may be time-limited)")
    
    print("=" * 80)

# Run the compliant debug version
if __name__ == "__main__":
    if not CRAWL4AI_AVAILABLE:
        print("❌ crawl4ai is required for this script")
        exit(1)
    
    # Run compliant debug mode
    asyncio.run(debug_main())
