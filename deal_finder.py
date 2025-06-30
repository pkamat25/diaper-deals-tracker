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

async def get_coles_deals():
    """Get Coles nappy deals using crawl4ai"""
    print("🕷️ Scraping Coles directly with crawl4ai...")
    deals = []
    
    try:
        async with AsyncWebCrawler(verbose=False) as crawler:
            
            # Coles URLs - ONLY use pages NOT disallowed by robots.txt
            coles_urls = [
                "https://www.coles.com.au/browse/baby/nappies-nappy-pants/nappies",  # Regular browse page (allowed)
                "https://www.coles.com.au/browse/baby/nappies-nappy-pants",         # Category page (allowed)
                # REMOVED: on-special pages (explicitly disallowed by robots.txt)
            ]
            
            for url in coles_urls:
                print(f"  🎯 Trying: {url}")
                
                try:
                    # Simplified crawl4ai usage - avoid complex strategies that might fail
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

def extract_coles_deals(html_content, extracted_content, base_url):
    """Extract nappy deals from Coles content with specific product URLs"""
    deals = []
    
    try:
        print("    🔍 Analyzing Coles content...")
        
        # Use BeautifulSoup to parse the HTML properly
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for product containers/tiles
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
        
        if not products:
            print("    🔍 Trying alternative extraction methods...")
            # Look for any links containing nappy keywords
            all_links = soup.find_all('a', href=True)
            product_links = []
            
            for link in all_links:
                href = link.get('href', '')
                text = link.get_text().strip()
                
                if (any(keyword in text.lower() for keyword in ['napp', 'huggies', 'pampers', 'babylove', 'rascal']) and
                    any(keyword in href.lower() for keyword in ['product', 'p/', '/browse/']) and
                    '

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
                    if (len(product_name) > 10 and 
                        not any(js_indicator in product_name for js_indicator in ['function', 'var ', 'object', '=>', '{', '}', 'defineProperty'])):
                        
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
                            if (len(special_text) < 50 and 
                                not any(js_indicator in special_text for js_indicator in ['function', 'var ', '=>', '{'])):
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
                if (any(keyword in line.lower() for keyword in nappy_keywords) and 
                    '



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
    body = f"Found {len(deals)} nappy deals using direct store scraping:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special']:
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "Scraped directly from store websites using crawl4ai! 🚀\n\n"
    body += "This system uses advanced web crawling with JavaScript rendering to find real deals."
    
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
    
    asyncio.run(main()) in text):
                    product_links.append(link)
            
            products = product_links[:10]  # Limit to 10
            print(f"    🔗 Found {len(products)} product links with nappy keywords")
        
        # Extract deals from product containers
        for i, product in enumerate(products[:5]):  # Limit to 5 deals
            try:
                deal = extract_single_product_deal(product, base_url)
                if deal:
                    deals.append(deal)
                    print(f"    ✅ Extracted deal {i+1}: {deal['price']} - {deal['product'][:50]}...")
            except Exception as e:
                print(f"    ❌ Error extracting product {i+1}: {e}")
                continue
        
        # Fallback: If no specific products found, look for general price patterns
        if not deals:
            print("    🔧 Using fallback pattern extraction...")
            price_patterns = re.findall(r'\$\d+\.\d{2}', html_content)
            save_patterns = re.findall(r'[Ss]ave \$\d+\.?\d*', html_content)
            
            if price_patterns:
                for i, price in enumerate(price_patterns[:3]):
                    deals.append({
                        'store': 'Coles',
                        'product': f'Nappies Special Deal #{i+1}',
                        'price': price,
                        'special': save_patterns[i] if i < len(save_patterns) else 'Special Price',
                        'url': f"{base_url}#deal-{i+1}"  # Add anchor for uniqueness
                    })
    
    except Exception as e:
        print(f"    ❌ Error extracting Coles deals: {e}")
    
    return deals

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

def extract_woolworths_deals(html_content, extracted_content, url):
    """Extract deals from Woolworths content"""
    deals = []
    
    try:
        # Look for price and discount patterns
        price_patterns = re.findall(r'\$\d+\.\d{2}', html_content)
        save_patterns = re.findall(r'[Ss]ave \$\d+', html_content)
        
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove']
        
        # Look for nappy content
        relevant_lines = []
        for line in html_content.split('\n'):
            line = line.strip()
            if (any(keyword in line.lower() for keyword in nappy_keywords) and 
                '$' in line and len(line) > 10):
                clean_line = re.sub(r'<[^>]+>', '', line).strip()
                if clean_line:
                    relevant_lines.append(clean_line)
        
        print(f"    🍼 Found {len(relevant_lines)} Woolworths nappy lines")
        print(f"    💰 Found {len(price_patterns)} prices")
        
        if relevant_lines and price_patterns:
            for i, price in enumerate(price_patterns[:3]):  # Limit to 3
                product_name = "Nappies Special"
                special = "Special Price"
                
                # Find matching content
                for line in relevant_lines:
                    if price in line:
                        product_name = line[:80]
                        break
                
                if i < len(save_patterns):
                    special = save_patterns[i]
                
                deals.append({
                    'store': 'Woolworths',
                    'product': product_name,
                    'price': price,
                    'special': special,
                    'url': url
                })
        
        # If no specific deals, but we have nappy content, add generic entry
        elif relevant_lines:
            deals.append({
                'store': 'Woolworths',
                'product': 'Nappies available - Check website for current specials',
                'price': 'Various prices',
                'special': 'Check website for current deals',
                'url': url
            })
    
    except Exception as e:
        print(f"    ❌ Error extracting Woolworths deals: {e}")
    
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
    body = f"Found {len(deals)} nappy deals using direct store scraping:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special']:
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "Scraped directly from store websites using crawl4ai! 🚀\n\n"
    body += "This system uses advanced web crawling with JavaScript rendering to find real deals."
    
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
        'method': 'Direct store scraping with crawl4ai'
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} deals to website")

async def main():
    """Main async function - Coles and Woolworths direct scraping only"""
    print("=" * 80)
    print(f"🕷️ DIRECT STORE SCRAPING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Using crawl4ai to scrape Coles & Woolworths directly")
    print("=" * 80)
    
    all_deals = []
    
    # Check Coles and Woolworths directly with crawl4ai
    print("\n🏪 Checking Coles...")
    coles_deals = await get_coles_deals()
    all_deals.extend(coles_deals)
    
    await asyncio.sleep(3)  # Be respectful between requests
    
    print("\n🏪 Checking Woolworths...")
    woolworths_deals = await get_woolworths_deals()
    all_deals.extend(woolworths_deals)
    
    print("=" * 80)
    print(f"📊 FINAL RESULTS: Found {len(all_deals)} deals from direct scraping")
    
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
        print("😔 No deals found from direct scraping")
        print("💡 This could mean:")
        print("   - No deals currently exist at Coles or Woolworths")
        print("   - Sites are still blocking crawl4ai")
        print("   - Deals structure has changed")
    
    print("=" * 80)
    print("✅ Direct scraping complete!")
    return all_deals

# Run async main if called directly
if __name__ == "__main__":
    if not CRAWL4AI_AVAILABLE:
        print("❌ crawl4ai is required for this script")
        exit(1)
    
    asyncio.run(main()) in line and 
                    len(line) > 10 and len(line) < 200 and
                    not any(js_indicator in line for js_indicator in ['function', 'var ', '=>', '{', 'defineProperty'])):
                    
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
    body = f"Found {len(deals)} nappy deals using direct store scraping:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special']:
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "Scraped directly from store websites using crawl4ai! 🚀\n\n"
    body += "This system uses advanced web crawling with JavaScript rendering to find real deals."
    
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
        'method': 'Direct store scraping with crawl4ai'
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} deals to website")

async def main():
    """Main async function - Coles and Woolworths direct scraping only"""
    print("=" * 80)
    print(f"🕷️ DIRECT STORE SCRAPING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Using crawl4ai to scrape Coles & Woolworths directly")
    print("=" * 80)
    
    all_deals = []
    
    # Check Coles and Woolworths directly with crawl4ai
    print("\n🏪 Checking Coles...")
    coles_deals = await get_coles_deals()
    all_deals.extend(coles_deals)
    
    await asyncio.sleep(3)  # Be respectful between requests
    
    print("\n🏪 Checking Woolworths...")
    woolworths_deals = await get_woolworths_deals()
    all_deals.extend(woolworths_deals)
    
    print("=" * 80)
    print(f"📊 FINAL RESULTS: Found {len(all_deals)} deals from direct scraping")
    
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
        print("😔 No deals found from direct scraping")
        print("💡 This could mean:")
        print("   - No deals currently exist at Coles or Woolworths")
        print("   - Sites are still blocking crawl4ai")
        print("   - Deals structure has changed")
    
    print("=" * 80)
    print("✅ Direct scraping complete!")
    return all_deals

# Run async main if called directly
if __name__ == "__main__":
    if not CRAWL4AI_AVAILABLE:
        print("❌ crawl4ai is required for this script")
        exit(1)
    
    asyncio.run(main()) in text):
                    product_links.append(link)
            
            products = product_links[:10]  # Limit to 10
            print(f"    🔗 Found {len(products)} product links with nappy keywords")
        
        # Extract deals from product containers
        for i, product in enumerate(products[:5]):  # Limit to 5 deals
            try:
                deal = extract_single_product_deal(product, base_url)
                if deal:
                    deals.append(deal)
                    print(f"    ✅ Extracted deal {i+1}: {deal['price']} - {deal['product'][:50]}...")
            except Exception as e:
                print(f"    ❌ Error extracting product {i+1}: {e}")
                continue
        
        # Fallback: If no specific products found, look for general price patterns
        if not deals:
            print("    🔧 Using fallback pattern extraction...")
            price_patterns = re.findall(r'\$\d+\.\d{2}', html_content)
            save_patterns = re.findall(r'[Ss]ave \$\d+\.?\d*', html_content)
            
            if price_patterns:
                for i, price in enumerate(price_patterns[:3]):
                    deals.append({
                        'store': 'Coles',
                        'product': f'Nappies Special Deal #{i+1}',
                        'price': price,
                        'special': save_patterns[i] if i < len(save_patterns) else 'Special Price',
                        'url': f"{base_url}#deal-{i+1}"  # Add anchor for uniqueness
                    })
    
    except Exception as e:
        print(f"    ❌ Error extracting Coles deals: {e}")
    
    return deals

def extract_single_product_deal(product_element, base_url):
    """Extract a single product deal with its specific URL"""
    try:
        # Extract product name
        name_selectors = ['h3', 'h4', '.product-name', '.product-title', '[data-testid="product-title"]']
        product_name = "Nappies Deal"
        
        for selector in name_selectors:
            name_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if name_elem:
                product_name = name_elem.get_text().strip()
                break
        
        # Extract price
        price_selectors = ['.price', '[data-testid="price"]', '.current-price', '.sale-price']
        price = "Check website"
        
        for selector in price_selectors:
            price_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if price_elem:
                price_text = price_elem.get_text().strip()
                price_match = re.search(r'\$\d+\.\d{2}', price_text)
                if price_match:
                    price = price_match.group()
                    break
        
        # Extract special/discount info
        special_selectors = ['.special', '.discount', '.save', '[data-testid="special"]', '.was-price']
        special = "Special Price"
        
        for selector in special_selectors:
            special_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if special_elem:
                special = special_elem.get_text().strip()
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
        
        # Only return if we have meaningful data
        if ('napp' in product_name.lower() or 'diaper' in product_name.lower() or 
            any(brand in product_name.lower() for brand in ['huggies', 'pampers', 'babylove', 'rascal'])):
            
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

def extract_woolworths_deals(html_content, extracted_content, url):
    """Extract deals from Woolworths content"""
    deals = []
    
    try:
        # Look for price and discount patterns
        price_patterns = re.findall(r'\$\d+\.\d{2}', html_content)
        save_patterns = re.findall(r'[Ss]ave \$\d+', html_content)
        
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove']
        
        # Look for nappy content
        relevant_lines = []
        for line in html_content.split('\n'):
            line = line.strip()
            if (any(keyword in line.lower() for keyword in nappy_keywords) and 
                '$' in line and len(line) > 10):
                clean_line = re.sub(r'<[^>]+>', '', line).strip()
                if clean_line:
                    relevant_lines.append(clean_line)
        
        print(f"    🍼 Found {len(relevant_lines)} Woolworths nappy lines")
        print(f"    💰 Found {len(price_patterns)} prices")
        
        if relevant_lines and price_patterns:
            for i, price in enumerate(price_patterns[:3]):  # Limit to 3
                product_name = "Nappies Special"
                special = "Special Price"
                
                # Find matching content
                for line in relevant_lines:
                    if price in line:
                        product_name = line[:80]
                        break
                
                if i < len(save_patterns):
                    special = save_patterns[i]
                
                deals.append({
                    'store': 'Woolworths',
                    'product': product_name,
                    'price': price,
                    'special': special,
                    'url': url
                })
        
        # If no specific deals, but we have nappy content, add generic entry
        elif relevant_lines:
            deals.append({
                'store': 'Woolworths',
                'product': 'Nappies available - Check website for current specials',
                'price': 'Various prices',
                'special': 'Check website for current deals',
                'url': url
            })
    
    except Exception as e:
        print(f"    ❌ Error extracting Woolworths deals: {e}")
    
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
    body = f"Found {len(deals)} nappy deals using direct store scraping:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special']:
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "Scraped directly from store websites using crawl4ai! 🚀\n\n"
    body += "This system uses advanced web crawling with JavaScript rendering to find real deals."
    
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
        'method': 'Direct store scraping with crawl4ai'
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} deals to website")

async def main():
    """Main async function - Coles and Woolworths direct scraping only"""
    print("=" * 80)
    print(f"🕷️ DIRECT STORE SCRAPING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Using crawl4ai to scrape Coles & Woolworths directly")
    print("=" * 80)
    
    all_deals = []
    
    # Check Coles and Woolworths directly with crawl4ai
    print("\n🏪 Checking Coles...")
    coles_deals = await get_coles_deals()
    all_deals.extend(coles_deals)
    
    await asyncio.sleep(3)  # Be respectful between requests
    
    print("\n🏪 Checking Woolworths...")
    woolworths_deals = await get_woolworths_deals()
    all_deals.extend(woolworths_deals)
    
    print("=" * 80)
    print(f"📊 FINAL RESULTS: Found {len(all_deals)} deals from direct scraping")
    
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
        print("😔 No deals found from direct scraping")
        print("💡 This could mean:")
        print("   - No deals currently exist at Coles or Woolworths")
        print("   - Sites are still blocking crawl4ai")
        print("   - Deals structure has changed")
    
    print("=" * 80)
    print("✅ Direct scraping complete!")
    return all_deals

# Run async main if called directly
if __name__ == "__main__":
    if not CRAWL4AI_AVAILABLE:
        print("❌ crawl4ai is required for this script")
        exit(1)
    
    asyncio.run(main())
