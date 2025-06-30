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

async def check_coles_sitemap():
    """Check Coles official sitemap for specials (most legitimate approach)"""
    deals = []
    
    try:
        print("    📋 Fetching official Coles specials sitemap...")
        
        # Get their official specials sitemap
        response = requests.get("https://www.coles.com.au/sitemap/sitemap-specials.xml", timeout=10)
        
        if response.status_code == 200:
            print(f"    ✅ Sitemap downloaded: {len(response.text)} characters")
            
            # Parse sitemap for nappy-related specials
            root = ET.fromstring(response.text)
            
            # Look for URLs containing nappy keywords
            nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove']
            nappy_urls = []
            
            for url_element in root.findall('.//{http://www.sitemaps.org/schemas/sitemap/0.9}url'):
                loc_element = url_element.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
                if loc_element is not None:
                    url = loc_element.text
                    if any(keyword in url.lower() for keyword in nappy_keywords):
                        nappy_urls.append(url)
            
            print(f"    🍼 Found {len(nappy_urls)} nappy-related URLs in sitemap")
            
            # Create deals from sitemap URLs (these are legitimate!)
            for i, url in enumerate(nappy_urls[:3]):  # Limit to 3
                deals.append({
                    'store': 'Coles',
                    'product': 'Nappies Special - See official Coles listing',
                    'price': 'Check website',
                    'special': 'Listed in official specials sitemap',
                    'url': url
                })
                
    except Exception as e:
        print(f"    ❌ Error checking sitemap: {e}")
    
    return deals

def is_valid_nappy_price(price_str):
    """Check if a price is realistic for nappies (between $5 and $100)"""
    try:
        price = float(price_str.replace('$', ''))
        return 5.0 <= price <= 100.0
    except:
        return False

def extract_single_product_deal(product_element, base_url):
    """Extract a single product deal with validation"""
    try:
        # Extract product name
        name_selectors = ['h3', 'h4', '.product-name', '.product-title', '[data-testid="product-title"]']
        product_name = "Nappies Deal"
        
        for selector in name_selectors:
            name_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if name_elem:
                product_name = name_elem.get_text().strip()
                break
        
        # Validate it's actually a nappy product
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove', 'rascal', 'tooshies']
        if not any(keyword in product_name.lower() for keyword in nappy_keywords):
            return None
        
        # Extract price
        price_selectors = ['.price', '[data-testid="price"]', '.current-price', '.sale-price']
        price = "Check website"
        
        for selector in price_selectors:
            price_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                price_match = re.search(r'\$\d+\.\d{2}', price_text)
                if price_match and is_valid_nappy_price(price_match.group()):
                    price = price_match.group()
                    break
        
        # Only proceed if we have a valid price
        if not is_valid_nappy_price(price):
            return None
        
        # Extract special/discount info
        special_selectors = ['.special', '.discount', '.save', '[data-testid="special"]', '.was-price']
        special = "Special Price"
        
        for selector in special_selectors:
            special_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if special_elem:
                special_text = special_elem.get_text().strip()
                if len(special_text) < 100:  # Reasonable length
                    special = special_text
                    break
        
        # Extract product URL
        product_url = base_url  # Default fallback
        
        # Try to find the specific product link
        if hasattr(product_element, 'get') and product_element.get('href'):
            # This is already a link element
            href = product_element.get('href')
            if href.startswith('/'):
                product_url = f"https://www.coles.com.au{href}"
            elif href.startswith('http'):
                product_url = href
        else:
            # Look for a link within the product container
            link_elem = product_element.find('a', href=True) if hasattr(product_element, 'find') else None
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    product_url = f"https://www.coles.com.au{href}"
                elif href.startswith('http'):
                    product_url = href
        
        return {
            'store': 'Coles',
            'product': product_name[:100],  # Limit length
            'price': price,
            'special': special,
            'url': product_url
        }
    
    except Exception as e:
        print(f"      ❌ Error extracting single product: {e}")
    
    return None

def extract_coles_deals(html_content, extracted_content, base_url):
    """Extract nappy deals from Coles content with better filtering"""
    deals = []
    
    try:
        print("    🔍 Analyzing Coles content...")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for product containers/tiles first
        product_selectors = [
            'article[data-testid="product-tile"]',
            'div[data-testid="product-tile"]', 
            'section[data-testid="product-tile"]',
            '.product-tile',
            '.product-item',
            '.product-card'
        ]
        
        products = []
        for selector in product_selectors:
            found = soup.select(selector)
            if found:
                products = found
                print(f"    📦 Found {len(products)} product containers using {selector}")
                break
        
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove', 'rascal', 'tooshies']
        
        # Method 1: Extract from product containers
        nappy_products = []
        for product in products:
            try:
                product_text = product.get_text().lower()
                if any(keyword in product_text for keyword in nappy_keywords):
                    nappy_products.append(product)
            except:
                continue
        
        print(f"    🍼 Found {len(nappy_products)} nappy-related product containers")
        
        # Extract deals from nappy products only
        for i, product in enumerate(nappy_products[:5]):  # Limit to 5
            try:
                deal = extract_single_product_deal(product, base_url)
                if deal and is_valid_nappy_price(deal['price']):
                    deals.append(deal)
                    print(f"    ✅ Valid nappy deal: {deal['price']} - {deal['product'][:50]}...")
            except Exception as e:
                continue
        
        # Method 2: If no product containers worked, try text-based extraction
        if not deals:
            print("    🔍 Trying text-based extraction for nappy deals...")
            
            # Split content into sections and look for nappy-related sections
            sections = html_content.split('<')
            nappy_sections = []
            
            for section in sections:
                section_text = section.lower()
                if (any(keyword in section_text for keyword in nappy_keywords) and 
                    '$' in section and
                    len(section) < 1000):  # Reasonable section size
                    nappy_sections.append(section)
            
            print(f"    📝 Found {len(nappy_sections)} nappy-related sections")
            
            # Extract prices from nappy sections only
            for section in nappy_sections[:10]:  # Check first 10 sections
                prices_in_section = re.findall(r'\$\d+\.\d{2}', section)
                for price in prices_in_section:
                    if is_valid_nappy_price(price) and len(deals) < 5:
                        
                        # Try to extract product name from this section
                        clean_section = re.sub(r'<[^>]+>', '', section)
                        product_name = clean_section.strip()[:100]
                        
                        # Look for discount info in this section
                        special = "Special Price"
                        if 'save' in section.lower():
                            save_match = re.search(r'save \$\d+\.?\d*', section.lower())
                            if save_match:
                                special = save_match.group().title()
                        elif 'half' in section.lower() or '½' in section:
                            special = "Half Price"
                        elif '%' in section:
                            percent_match = re.search(r'\d+%', section)
                            if percent_match:
                                special = f"{percent_match.group()} off"
                        
                        deals.append({
                            'store': 'Coles',
                            'product': product_name or f'Nappies Deal - {price}',
                            'price': price,
                            'special': special,
                            'url': f"{base_url}?search=nappies&price={price.replace('$', '')}"
                        })
                        
                        print(f"    ✅ Text-extracted nappy deal: {price}")
        
        # Remove duplicates by price
        seen_prices = set()
        unique_deals = []
        for deal in deals:
            if deal['price'] not in seen_prices:
                seen_prices.add(deal['price'])
                unique_deals.append(deal)
        
        deals = unique_deals
    
    except Exception as e:
        print(f"    ❌ Error extracting Coles deals: {e}")
    
    return deals

async def get_coles_deals():
    """Get Coles nappy deals using robots.txt compliant URLs"""
    print("🕷️ Scraping Coles (robots.txt compliant)...")
    deals = []
    
    try:
        # First, try their official sitemap (most legitimate)
        print("  📋 Checking official Coles specials sitemap...")
        sitemap_deals = await check_coles_sitemap()
        if sitemap_deals:
            deals.extend(sitemap_deals)
            return deals
        
        # Fallback: Use allowed browse pages only
        async with AsyncWebCrawler(verbose=False) as crawler:
            
            # Coles URLs - ONLY use pages NOT disallowed by robots.txt
            coles_urls = [
                "https://www.coles.com.au/browse/baby/nappies-nappy-pants/nappies",  # Regular browse page (allowed)
                "https://www.coles.com.au/browse/baby/nappies-nappy-pants"          # Category page (allowed)
            ]
            
            for url in coles_urls:
                print(f"  🎯 Trying (robots.txt compliant): {url}")
                
                try:
                    # Simplified crawl4ai usage
                    result = await crawler.arun(
                        url=url,
                        word_count_threshold=10,
                        bypass_cache=True,
                        js_code=[
                            "window.scrollTo(0, document.body.scrollHeight);",
                            "await new Promise(resolve => setTimeout(resolve, 2000));"
                        ],
                        wait_for="body",
                        delay_before_return_html=3
                    )
                    
                    print(f"  📄 Content length: {len(result.html)} characters")
                    print(f"  🔍 Links found: {len(result.links) if hasattr(result, 'links') and result.links else 0}")
                    
                    # Check if we got blocked
                    if "incapsula" in result.html.lower() or "blocked" in result.html.lower():
                        print("  ❌ Detected security blocking")
                        continue
                    
                    # Extract deals from the crawled content
                    extracted_deals = extract_coles_deals(result.html, getattr(result, 'extracted_content', None), url)
                    
                    if extracted_deals:
                        print(f"  ✅ Found {len(extracted_deals)} Coles deals!")
                        deals.extend(extracted_deals)
                        break  # Success! Stop trying other URLs
                    else:
                        print("  ❌ No deals found in Coles content")
                        
                except Exception as e:
                    print(f"  ❌ Error crawling {url}: {e}")
                    continue
        
    except Exception as e:
        print(f"  ❌ crawl4ai error: {e}")
        import traceback
        traceback.print_exc()
    
    return deals

def extract_woolworths_deals(html_content, extracted_content, base_url):
    """Extract deals from Woolworths content, avoiding JavaScript code"""
    deals = []
    
    try:
        print("    🔍 Analyzing Woolworths content...")
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Remove script tags and style tags to avoid JavaScript content
        for script in soup(["script", "style"]):
            script.decompose()
        
        # Look for Woolworths product containers
        product_selectors = [
            '[data-testid="product-tile"]',
            '.product-tile',
            '.product-item',
            '.shelfProductTile',
            'article[class*="product"]',
            '[class*="ProductTile"]'
        ]
        
        products = []
        for selector in product_selectors:
            found = soup.select(selector)
            if found:
                products = found
                print(f"    📦 Found {len(products)} Woolworths product containers")
                break
        
        # Filter for nappy-related products only
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove', 'tooshies']
        nappy_products = []
        
        for product in products:
            try:
                product_text = product.get_text().lower()
                if any(keyword in product_text for keyword in nappy_keywords):
                    nappy_products.append(product)
            except:
                continue
        
        print(f"    🍼 Found {len(nappy_products)} nappy-related Woolworths products")
        
        # Extract deals from nappy products
        for i, product in enumerate(nappy_products[:5]):  # Limit to 5
            try:
                # Extract product name (avoid JavaScript)
                name_elem = (product.select_one('h3') or 
                           product.select_one('h4') or
                           product.select_one('[data-testid="product-title"]') or
                           product.select_one('.product-title'))
                
                if name_elem:
                    product_name = name_elem.get_text().strip()
                    
                    # Clean product name - remove JavaScript patterns
                    js_indicators = ['function', 'var ', 'object', '=>', '{', '}', 'defineProperty']
                    if (len(product_name) > 10 and 
                        not any(js_indicator in product_name for js_indicator in js_indicators)):
                        
                        # Extract price
                        price_elem = (product.select_one('[data-testid="price"]') or
                                    product.select_one('.price') or
                                    product.select_one('.primary') or
                                    product.select_one('[class*="price"]'))
                        
                        price = "Check website"
                        if price_elem:
                            price_text = price_elem.get_text().strip()
                            price_match = re.search(r'\$\d+\.\d{2}', price_text)
                            if price_match and is_valid_nappy_price(price_match.group()):
                                price = price_match.group()
                        
                        # Extract special/discount (avoid JavaScript)
                        special_elem = (product.select_one('[data-testid="special"]') or
                                      product.select_one('.special-badge') or
                                      product.select_one('.was') or
                                      product.select_one('[class*="special"]'))
                        
                        special = "Special Price"
                        if special_elem:
                            special_text = special_elem.get_text().strip()
                            js_indicators = ['function', 'var ', '=>', '{']
                            if (len(special_text) < 50 and 
                                not any(js_indicator in special_text for js_indicator in js_indicators)):
                                special = special_text
                        
                        # Extract product URL
                        link_elem = product.select_one('a[href]')
                        product_url = base_url
                        
                        if link_elem:
                            href = link_elem.get('href')
                            if href and href.startswith('/'):
                                product_url = f"https://www.woolworths.com.au{href}"
                            elif href and href.startswith('http'):
                                product_url = href
                        
                        deals.append({
                            'store': 'Woolworths',
                            'product': product_name[:100],
                            'price': price,
                            'special': special,
                            'url': product_url
                        })
                        
                        print(f"    ✅ Extracted clean Woolworths deal: {price} - {product_name[:40]}...")
            
            except Exception as e:
                print(f"    ❌ Error extracting Woolworths product {i}: {e}")
                continue
        
        # If no specific products found, try text-based extraction (avoiding JavaScript)
        if not deals:
            print("    🔍 Trying text-based extraction for Woolworths...")
            
            # Get clean text content without JavaScript
            clean_text = soup.get_text()
            lines = clean_text.split('\n')
            
            for line in lines:
                line = line.strip()
                js_indicators = ['function', 'var ', '=>', '{', 'defineProperty']
                if (any(keyword in line.lower() for keyword in nappy_keywords) and 
                    '$' in line and 
                    len(line) > 10 and len(line) < 200 and
                    not any(js_indicator in line for js_indicator in js_indicators)):
                    
                    price_match = re.search(r'\$\d+\.\d{2}', line)
                    if price_match and is_valid_nappy_price(price_match.group()):
                        deals.append({
                            'store': 'Woolworths',
                            'product': line[:80],
                            'price': price_match.group(),
                            'special': 'Special Deal',
                            'url': base_url
                        })
                        
                        print(f"    ✅ Text-extracted Woolworths deal: {price_match.group()}")
                        
                        if len(deals) >= 3:  # Limit to 3 deals
                            break
        
        # Final fallback - generic entry if nappy content detected
        if not deals:
            page_text = soup.get_text().lower()
            if any(keyword in page_text for keyword in nappy_keywords):
                deals.append({
                    'store': 'Woolworths',
                    'product': 'Nappies available - Check website for current specials',
                    'price': 'Various prices',
                    'special': 'Check online for current deals',
                    'url': base_url
                })
                print("    ✅ Added generic Woolworths nappy entry")
    
    except Exception as e:
        print(f"    ❌ Error extracting Woolworths deals: {e}")
    
    return deals

async def get_woolworths_deals():
    """Get Woolworths deals with crawl4ai"""
    print("🕷️ Scraping Woolworths with crawl4ai...")
    deals = []
    
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            
            woolworths_urls = [
                "https://www.woolworths.com.au/shop/browse/baby/nappies-pants",
                "https://www.woolworths.com.au/shop/browse/baby/nappies-pants?specials=true"
            ]
            
            for url in woolworths_urls:
                print(f"  🎯 Trying: {url}")
                
                try:
                    # Simplified crawl4ai for Woolworths
                    result = await crawler.arun(
                        url=url,
                        word_count_threshold=10,
                        bypass_cache=True,
                        js_code=[
                            "window.scrollTo(0, document.body.scrollHeight);",
                            "await new Promise(resolve => setTimeout(resolve, 2000));"
                        ]
                    )
                    
                    print(f"  📄 Content length: {len(result.html)} characters")
                    
                    if "woolworths" in result.html.lower():
                        # Extract deals using similar logic to Coles
                        extracted_deals = extract_woolworths_deals(result.html, getattr(result, 'extracted_content', None), url)
                        
                        if extracted_deals:
                            print(f"  ✅ Found {len(extracted_deals)} Woolworths deals!")
                            deals.extend(extracted_deals)
                            break
                        else:
                            print("  ❌ No specific deals found")
                    else:
                        print("  ❌ Woolworths content not detected")
                    
                except Exception as e:
                    print(f"  ❌ Error crawling {url}: {e}")
                    continue
    
    except Exception as e:
        print(f"  ❌ Woolworths crawl error: {e}")
    
    return deals

def send_email_notification(deals):
    """Send email with today's deals"""
    if not deals:
        print("No deals to email")
        return
    
    sender_email = os.environ.get('GMAIL_EMAIL', 'your-email@gmail.com')
    sender_password = os.environ.get('EMAIL_PASSWORD')
    recipient_email = os.environ.get('RECIPIENT_EMAIL', sender_email)
    
    if not sender_password:
        print("No email password set - skipping email notification")
        return
    
    subject = f"🕷️ {len(deals)} Nappy Deals Found with crawl4ai! - {datetime.now().strftime('%d/%m/%Y')}"
    body = f"Found {len(deals)} nappy deals using robots.txt compliant scraping:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special']:
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "Scraped using robots.txt compliant methods! 🚀\n\n"
    body += "This system respects store guidelines and uses official data feeds."
    
    msg = MIMEText(body)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = recipient_email
    
    try:
        with smtplib.SMTP('smtp.gmail.com', 587) as server:
            server.starttls()
            server.login(sender_email, sender_password)
            server.send_message(msg)
        print("✅ Email notification sent!")
    except Exception as e:
        print(f"❌ Error sending email: {e}")

def save_deals_to_file(deals):
    """Save deals to JSON file for website"""
    os.makedirs('docs', exist_ok=True)
    
    data = {
        'date': datetime.now().isoformat(),
        'total_deals': len(deals),
        'deals': deals,
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S AEST'),
        'method': 'robots.txt compliant scraping + official sitemaps'
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} deals to website")

async def main():
    """Main async function - robots.txt compliant scraping"""
    print("=" * 80)
    print(f"🕷️ ROBOTS.TXT COMPLIANT SCRAPING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("⚖️ Using only URLs allowed by store robots.txt files")
    print("=" * 80)
    
    all_deals = []
    
    # Check Coles and Woolworths using compliant methods
    print("\n🏪 Checking Coles (robots.txt compliant)...")
    coles_deals = await get_coles_deals()
    all_deals.extend(coles_deals)
    
    await asyncio.sleep(3)  # Be respectful between requests
    
    print("\n🏪 Checking Woolworths...")
    woolworths_deals = await get_woolworths_deals()
    all_deals.extend(woolworths_deals)
    
    print("=" * 80)
    print(f"📊 FINAL RESULTS: Found {len(all_deals)} deals using compliant methods")
    
    if all_deals:
        print("\n🎉 Today's deals:")
        for i, deal in enumerate(all_deals, 1):
            print(f"{i}. {deal['store']}: {deal['price']} - {deal['special']}")
            print(f"   📦 {deal['product'][:70]}...")
        
        save_deals_to_file(all_deals)
        send_email_notification(all_deals)
        print("\n✅ Deals saved and notifications sent!")
    else:
        save_deals_to_file([])
        print("😔 No deals found using compliant methods")
        print("💡 This could mean:")
        print("   - No deals currently exist")
        print("   - Compliant pages don't show special pricing")
        print("   - Need to check official catalogues manually")
    
    print("=" * 80)
    print("✅ Compliant scraping complete!")
    return all_deals

# Run async main if called directly
if __name__ == "__main__":
    if not CRAWL4AI_AVAILABLE:
        print("❌ crawl4ai is required for this script")
        exit(1)
    
    asyncio.run(main())
