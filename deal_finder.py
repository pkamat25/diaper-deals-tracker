import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os
import time
import re
import asyncio

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
            
            # Coles URLs to try
            coles_urls = [
                "https://www.coles.com.au/on-special/baby/nappies-nappy-pants",
                "https://www.coles.com.au/browse/baby/nappies-nappy-pants/nappies",
                "https://shop.coles.com.au/a/national/specials/browse/baby/nappies-nappy-pants"
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

def extract_coles_deals(html_content, extracted_content, url):
    """Extract nappy deals from Coles content"""
    deals = []
    
    try:
        print("    🔍 Analyzing Coles content...")
        
        # Look for price patterns
        price_patterns = re.findall(r'\$\d+\.\d{2}', html_content)
        save_patterns = re.findall(r'[Ss]ave \$\d+\.?\d*', html_content)
        discount_patterns = re.findall(r'\d+% [Oo]ff', html_content)
        half_price_patterns = re.findall(r'[Hh]alf [Pp]rice|½ [Pp]rice', html_content)
        
        print(f"    💰 Found {len(price_patterns)} price patterns")
        print(f"    💸 Found {len(save_patterns)} save patterns")
        print(f"    🏷️ Found {len(discount_patterns)} percentage discounts")
        print(f"    ⚡ Found {len(half_price_patterns)} half price indicators")
        
        # Look for nappy-related content with prices
        nappy_keywords = ['napp', 'diaper', 'huggies', 'pampers', 'babylove', 'rascal', 'tooshies']
        relevant_content = []
        
        # Extract from HTML lines
        for line in html_content.split('\n'):
            line = line.strip()
            if (any(keyword in line.lower() for keyword in nappy_keywords) and 
                '$' in line and 
                len(line) > 15 and len(line) < 400):
                # Clean HTML tags
                clean_line = re.sub(r'<[^>]+>', '', line)
                clean_line = clean_line.strip()
                if clean_line and clean_line not in relevant_content:
                    relevant_content.append(clean_line)
        
        print(f"    🍼 Found {len(relevant_content)} relevant content pieces")
        
        # Show some examples of what we found
        if relevant_content:
            print("    📝 Sample content:")
            for i, content in enumerate(relevant_content[:3]):
                print(f"      {i+1}. {content[:80]}...")
        
        # Method 1: Create deals from price + content combinations
        unique_prices = list(set(price_patterns))[:5]  # Get up to 5 unique prices
        
        for i, price in enumerate(unique_prices):
            product_name = "Nappies Special Deal"
            special_offer = "Special Price"
            
            # Find the best matching content for this price
            for content in relevant_content:
                if price in content:
                    # Clean and format product name
                    product_name = content.replace(price, '').strip()
                    # Remove common HTML artifacts
                    product_name = re.sub(r'&[a-zA-Z]+;', '', product_name)
                    product_name = re.sub(r'\s+', ' ', product_name).strip()
                    if len(product_name) > 100:
                        product_name = product_name[:100] + "..."
                    break
            
            # Find the best discount info for this deal
            if i < len(save_patterns):
                special_offer = save_patterns[i]
            elif i < len(half_price_patterns):
                special_offer = half_price_patterns[i]
            elif i < len(discount_patterns):
                special_offer = discount_patterns[i]
            
            deals.append({
                'store': 'Coles',
                'product': product_name,
                'price': price,
                'special': special_offer,
                'url': url
            })
        
        # Method 2: Check semantic extraction from crawl4ai
        if not deals and extracted_content:
            print("    🧠 Checking semantic extraction...")
            for i, item in enumerate(extracted_content[:5]):
                content_str = str(item)
                if (any(keyword in content_str.lower() for keyword in nappy_keywords) and 
                    '$' in content_str):
                    
                    price_match = re.search(r'\$\d+\.\d{2}', content_str)
                    price = price_match.group() if price_match else "Check website"
                    
                    # Clean the content for product name
                    clean_content = re.sub(r'<[^>]+>', '', content_str)
                    clean_content = clean_content.strip()[:100]
                    
                    deals.append({
                        'store': 'Coles',
                        'product': f'Nappies Deal #{i+1} - {clean_content}',
                        'price': price,
                        'special': 'Found via semantic extraction',
                        'url': url
                    })
        
        # Method 3: If we found evidence of deals but couldn't extract specifics
        if not deals and (price_patterns or save_patterns or half_price_patterns):
            print("    🔧 Creating generic deal from detected patterns...")
            deals.append({
                'store': 'Coles',
                'product': 'Nappies Specials Available - Check website for details',
                'price': price_patterns[0] if price_patterns else 'Check website',
                'special': save_patterns[0] if save_patterns else 'Special pricing detected',
                'url': url
            })
    
    except Exception as e:
        print(f"    ❌ Error extracting Coles deals: {e}")
        import traceback
        traceback.print_exc()
    
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
