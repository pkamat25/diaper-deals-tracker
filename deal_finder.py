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
    """Extract a single product deal with detailed description"""
    try:
        # Extract product name and description
        name_selectors = [
            'h3', 'h4', 
            '.product-name', '.product-title', 
            '[data-testid="product-title"]',
            '[data-testid="product-name"]',
            '.product-header',
            'a[title]'  # Sometimes title attribute has full name
        ]
        
        product_name = ""
        product_description = ""
        
        # Try to get the most detailed product name
        for selector in name_selectors:
            name_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if name_elem:
                if selector == 'a[title]':
                    product_name = name_elem.get('title', '').strip()
                else:
                    product_name = name_elem.get_text().strip()
                
                if len(product_name) > 20:  # Prefer longer, more descriptive names
                    break
        
        # If we didn't get a good name, try alternative approaches
        if len(product_name) < 10:
            # Look for any text with nappy keywords
            all_text = product_element.get_text() if hasattr(product_element, 'get_text') else str(product_element)
            lines = all_text.split('\n')
            
            for line in lines:
                line = line.strip()
                nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove', 'rascal', 'tooshies']
                if (any(keyword in line.lower() for keyword in nappy_keywords) and 
                    len(line) > 10 and len(line) < 200 and
                    'size' in line.lower()):  # Prefer lines with size info
                    product_name = line
                    break
        
        # Enhance product name with additional details
        enhanced_name = enhance_product_description(product_element, product_name)
        
        # Validate it's actually a nappy product
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove', 'rascal', 'tooshies']
        if not any(keyword in enhanced_name.lower() for keyword in nappy_keywords):
            return None
        
        # Extract price
        price_selectors = [
            '.price', '[data-testid="price"]', 
            '.current-price', '.sale-price',
            '.price-current', '.dollarValue',
            '[class*="price"]'
        ]
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
        
        # Extract special/discount info with more detail
        special_selectors = [
            '.special', '.discount', '.save', 
            '[data-testid="special"]', '.was-price',
            '.special-badge', '.promotion',
            '[class*="special"]', '[class*="save"]'
        ]
        special = "Special Price"
        
        for selector in special_selectors:
            special_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if special_elem:
                special_text = special_elem.get_text().strip()
                if len(special_text) > 3 and len(special_text) < 100:  # Reasonable length
                    special = special_text
                    break
        
        # Look for additional promotional text
        promo_text = extract_promotional_info(product_element)
        if promo_text and promo_text != special:
            special = f"{special} - {promo_text}"
        
        # Extract product URL
        product_url = base_url  # Default fallback
        
        # Try to find the specific product link
        if hasattr(product_element, 'get') and product_element.get('href'):
            href = product_element.get('href')
            if href.startswith('/'):
                product_url = f"https://www.coles.com.au{href}"
            elif href.startswith('http'):
                product_url = href
        else:
            link_elem = product_element.find('a', href=True) if hasattr(product_element, 'find') else None
            if link_elem:
                href = link_elem.get('href')
                if href.startswith('/'):
                    product_url = f"https://www.coles.com.au{href}"
                elif href.startswith('http'):
                    product_url = href
        
        return {
            'store': 'Coles',
            'product': enhanced_name[:150],  # Allow longer descriptions
            'price': price,
            'special': special[:100],  # Limit special text
            'url': product_url
        }
    
    except Exception as e:
        print(f"      ❌ Error extracting single product: {e}")
    
    return None

def enhance_product_description(product_element, base_name):
    """Enhance product name with size, brand, and pack information"""
    try:
        # Get all text from the product element
        full_text = product_element.get_text() if hasattr(product_element, 'get_text') else str(product_element)
        
        # Look for size information
        size_patterns = [
            r'size \d+',
            r'size [0-6]',
            r'\d+kg',
            r'\d+-\d+kg',
            r'newborn',
            r'infant',
            r'toddler'
        ]
        
        size_info = ""
        for pattern in size_patterns:
            match = re.search(pattern, full_text.lower())
            if match:
                size_info = match.group()
                break
        
        # Look for pack count
        pack_patterns = [
            r'\d+ pack',
            r'\(\d+\)',
            r'\d+ count',
            r'\d+pk'
        ]
        
        pack_info = ""
        for pattern in pack_patterns:
            match = re.search(pattern, full_text.lower())
            if match:
                pack_info = match.group()
                break
        
        # Look for brand (if not already in name)
        brands = ['huggies', 'pampers', 'babylove', 'rascals', 'tooshies', 'mamia']
        brand_info = ""
        
        for brand in brands:
            if brand not in base_name.lower() and brand in full_text.lower():
                brand_info = brand.title()
                break
        
        # Look for product type details
        product_types = [
            'ultra dry', 'ultimate', 'baby dry', 'pure care',
            'cosifit', 'premium', 'classic', 'overnight',
            'sensitive', 'natural', 'eco'
        ]
        
        type_info = ""
        for ptype in product_types:
            if ptype in full_text.lower():
                type_info = ptype.title()
                break
        
        # Combine information intelligently
        enhanced_parts = []
        
        if brand_info and brand_info.lower() not in base_name.lower():
            enhanced_parts.append(brand_info)
        
        if base_name and 'napp' not in base_name.lower():
            enhanced_parts.append(base_name)
        elif not base_name:
            enhanced_parts.append("Nappies")
        
        if type_info and type_info.lower() not in ' '.join(enhanced_parts).lower():
            enhanced_parts.append(type_info)
        
        if size_info:
            enhanced_parts.append(f"Size {size_info}")
        
        if pack_info:
            enhanced_parts.append(f"({pack_info})")
        
        # Join parts intelligently
        if enhanced_parts:
            enhanced_name = ' '.join(enhanced_parts)
            # Clean up the result
            enhanced_name = re.sub(r'\s+', ' ', enhanced_name)  # Remove extra spaces
            enhanced_name = enhanced_name.strip()
            return enhanced_name if len(enhanced_name) > 5 else base_name
        
        return base_name if base_name else "Nappies Special"
        
    except Exception as e:
        return base_name if base_name else "Nappies Deal"

def extract_promotional_info(product_element):
    """Extract additional promotional information"""
    try:
        promo_selectors = [
            '.promotion-text',
            '.offer-text', 
            '.badge-text',
            '[class*="promo"]',
            '[class*="offer"]',
            '.stamp-text'
        ]
        
        for selector in promo_selectors:
            promo_elem = product_element.select_one(selector) if hasattr(product_element, 'select_one') else product_element.find(selector)
            if promo_elem:
                promo_text = promo_elem.get_text().strip()
                if len(promo_text) > 3 and len(promo_text) < 50:
                    return promo_text
        
        # Look for common promotional phrases
        full_text = product_element.get_text() if hasattr(product_element, 'get_text') else str(product_element)
        promo_phrases = [
            r'half price',
            r'\d+% off',
            r'buy \d+ get \d+',
            r'was \$\d+\.\d{2}',
            r'save \$\d+',
            r'down down',
            r'member price'
        ]
        
        for phrase_pattern in promo_phrases:
            match = re.search(phrase_pattern, full_text.lower())
            if match:
                return match.group().title()
        
        return ""
        
    except Exception as e:
        return ""

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
    
    subject = f"🕷️ {len(deals)} Coles Nappy Deals Found! - {datetime.now().strftime('%d/%m/%Y')}"
    body = f"Found {len(deals)} nappy deals from Coles using compliant scraping:\n\n"
    
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
        'method': 'Coles-only robots.txt compliant scraping + official sitemaps'
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} deals to website")

async def main():
    """Main async function - Coles only (most compliant)"""
    print("=" * 80)
    print(f"🕷️ COMPLIANT SCRAPING - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("⚖️ Using only robots.txt compliant methods for Coles")
    print("❌ Woolworths removed due to aggressive anti-scraping measures")
    print("=" * 80)
    
    all_deals = []
    
    # Check only Coles using compliant methods
    print("\n🏪 Checking Coles (robots.txt compliant)...")
    coles_deals = await get_coles_deals()
    all_deals.extend(coles_deals)
    
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
        print("   - No deals currently exist at Coles")
        print("   - Browse pages don't show special pricing")
        print("   - Check official Coles catalogues manually")
    
    print("=" * 80)
    print("✅ Compliant scraping complete!")
    return all_deals

# Run async main if called directly
if __name__ == "__main__":
    if not CRAWL4AI_AVAILABLE:
        print("❌ crawl4ai is required for this script")
        exit(1)
    
    asyncio.run(main())
