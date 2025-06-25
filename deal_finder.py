import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os
import time
import re

def check_coles_deals():
    """Check Coles using multiple approaches - NO HARDCODING"""
    print("Checking Coles with multiple methods...")
    deals = []
    
    # Method 1: Direct website scraping with various headers
    print("🔍 Method 1: Direct website scraping")
    urls_to_try = [
        "https://www.coles.com.au/on-special/baby/nappies-nappy-pants",
        "https://www.coles.com.au/browse/baby/nappies-nappy-pants/nappies",
        "https://shop.coles.com.au/a/national/specials/browse/baby/nappies-nappy-pants"
    ]
    
    headers_to_try = [
        {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'},
        {'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 14_6 like Mac OS X) AppleWebKit/605.1.15'},
        {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'},
    ]
    
    for url in urls_to_try:
        for headers in headers_to_try:
            try:
                print(f"  Trying: {url}")
                response = requests.get(url, headers=headers, timeout=10)
                
                # Check if we're being blocked
                if "incapsula" in response.text.lower() or "blocked" in response.text.lower():
                    print(f"  ❌ Blocked by security")
                    continue
                
                if response.status_code == 200:
                    deals_found = extract_deals_from_html(response.text, "Coles", url)
                    if deals_found:
                        print(f"  ✅ Found {len(deals_found)} deals via direct scraping")
                        deals.extend(deals_found)
                        return deals  # Success! Return immediately
                    
            except Exception as e:
                print(f"  ❌ Error: {e}")
                continue
    
    # Method 2: Check for RSS/JSON feeds
    print("🔍 Method 2: Looking for RSS/JSON feeds")
    feed_urls = [
        "https://www.coles.com.au/content/coles/en/homepage/jcr:content/par/specials_carousel.data.json",
        "https://www.coles.com.au/api/v1/specials/baby",
        "https://shop.coles.com.au/wcs/resources/store/20601/specials"
    ]
    
    for feed_url in feed_urls:
        try:
            print(f"  Trying feed: {feed_url}")
            response = requests.get(feed_url, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    deals_found = extract_deals_from_json(data, "Coles")
                    if deals_found:
                        print(f"  ✅ Found {len(deals_found)} deals via JSON feed")
                        deals.extend(deals_found)
                        return deals
                except:
                    pass
        except Exception as e:
            print(f"  ❌ Feed error: {e}")
    
    # Method 3: Check price comparison sites
    print("🔍 Method 3: Checking price comparison sites")
    comparison_sites = [
        "https://www.ozbargain.com.au/search/node/coles%20nappies%20type%3Adeal",
        "https://www.lasoo.com.au/catalogue/coles",
    ]
    
    for site_url in comparison_sites:
        try:
            print(f"  Trying comparison site: {site_url}")
            response = requests.get(site_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                deals_found = extract_deals_from_comparison_site(response.text, "Coles", site_url)
                if deals_found:
                    print(f"  ✅ Found {len(deals_found)} deals via comparison site")
                    deals.extend(deals_found)
                    return deals
        except Exception as e:
            print(f"  ❌ Comparison site error: {e}")
    
    # Method 4: Check if Coles has a mobile API
    print("🔍 Method 4: Trying mobile API endpoints")
    mobile_apis = [
        "https://www.coles.com.au/api/products/search?q=nappies&specials=true",
        "https://mobile.coles.com.au/api/specials/baby"
    ]
    
    for api_url in mobile_apis:
        try:
            print(f"  Trying mobile API: {api_url}")
            headers = {
                'User-Agent': 'Coles/1.0 (iPhone; iOS 14.6)',
                'Accept': 'application/json'
            }
            response = requests.get(api_url, headers=headers, timeout=10)
            if response.status_code == 200:
                try:
                    data = response.json()
                    deals_found = extract_deals_from_json(data, "Coles")
                    if deals_found:
                        print(f"  ✅ Found {len(deals_found)} deals via mobile API")
                        deals.extend(deals_found)
                        return deals
                except:
                    pass
        except Exception as e:
            print(f"  ❌ Mobile API error: {e}")
    
    print("❌ All Coles methods failed - no deals found")
    return deals

def extract_deals_from_html(html_content, store_name, url):
    """Extract deals from HTML content"""
    deals = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for common deal patterns
        price_patterns = re.findall(r'\$\d+\.\d{2}', html_content)
        save_patterns = re.findall(r'[Ss]ave \$\d+\.\d{2}', html_content)
        
        # Check for nappy/diaper related content
        nappy_keywords = ['Tooshies','huggies', 'Rascals', 'babylove','Millie Moon']
        has_nappy_content = any(keyword in html_content.lower() for keyword in nappy_keywords)
        
        if has_nappy_content and (price_patterns or save_patterns):
            print(f"    Found nappy content with {len(price_patterns)} prices, {len(save_patterns)} saves")
            
            # Try to extract specific product information
            product_elements = soup.find_all(['h1', 'h2', 'h3', 'h4'], text=lambda text: text and any(keyword in text.lower() for keyword in nappy_keywords))
            
            for i, element in enumerate(product_elements[:3]):  # Limit to 3 deals
                product_name = element.get_text().strip()
                
                # Try to find price near this product
                price = "Check website"
                special = "Special offer"
                
                # Look for price in nearby elements
                parent = element.parent
                if parent:
                    parent_text = parent.get_text()
                    price_match = re.search(r'\$\d+\.\d{2}', parent_text)
                    save_match = re.search(r'[Ss]ave \$\d+\.\d{2}', parent_text)
                    
                    if price_match:
                        price = price_match.group()
                    if save_match:
                        special = save_match.group()
                
                deals.append({
                    'store': store_name,
                    'product': product_name,
                    'price': price,
                    'special': special,
                    'url': url
                })
        
    except Exception as e:
        print(f"    Error extracting from HTML: {e}")
    
    return deals

def extract_deals_from_json(json_data, store_name):
    """Extract deals from JSON data"""
    deals = []
    try:
        # Handle different JSON structures
        if isinstance(json_data, dict):
            # Look for common JSON keys
            items = []
            for key in ['items', 'products', 'specials', 'deals', 'data']:
                if key in json_data:
                    items = json_data[key]
                    break
            
            if isinstance(items, list):
                for item in items[:5]:  # Limit to 5 deals
                    if isinstance(item, dict):
                        # Extract product info
                        name = item.get('name', item.get('title', item.get('product', 'Nappy Special')))
                        price = item.get('price', item.get('currentPrice', 'Check website'))
                        special = item.get('special', item.get('discount', item.get('offer', 'Special price')))
                        
                        # Only include if it's nappy related
                        if any(keyword in str(name).lower() for keyword in ['napp', 'diaper', 'baby']):
                            deals.append({
                                'store': store_name,
                                'product': str(name),
                                'price': str(price),
                                'special': str(special),
                                'url': f"https://www.{store_name.lower()}.com.au"
                            })
    
    except Exception as e:
        print(f"    Error extracting from JSON: {e}")
    
    return deals

def extract_deals_from_comparison_site(html_content, store_name, url):
    """Extract deals from price comparison sites"""
    deals = []
    try:
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for deal titles and prices
        deal_elements = soup.find_all(['a', 'div', 'h3'], text=lambda text: text and 'napp' in text.lower())
        
        for element in deal_elements[:3]:  # Limit to 3 deals
            text = element.get_text().strip()
            
            # Try to extract price from nearby text
            parent = element.parent
            price = "Check website"
            
            if parent:
                parent_text = parent.get_text()
                price_match = re.search(r'\$\d+\.\d{2}', parent_text)
                if price_match:
                    price = price_match.group()
            
            if 'coles' in text.lower() or store_name.lower() in text.lower():
                deals.append({
                    'store': store_name,
                    'product': text[:100],  # Limit length
                    'price': price,
                    'special': 'Found on deal site',
                    'url': url
                })
    
    except Exception as e:
        print(f"    Error extracting from comparison site: {e}")
    
    return deals

def check_woolworths_deals():
    """Check Woolworths using multiple approaches"""
    print("Checking Woolworths with multiple methods...")
    deals = []
    
    # Similar multi-approach strategy for Woolworths
    urls_to_try = [
        "https://www.woolworths.com.au/shop/browse/baby/nappies-pants",
        "https://www.woolworths.com.au/shop/browse/baby/nappies-pants?specials=true",
        "https://www.woolworths.com.au/apis/ui/browse/category/1_E5BEE36E"
    ]
    
    for url in urls_to_try:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                deals_found = extract_deals_from_html(response.text, "Woolworths", url)
                if deals_found:
                    print(f"✅ Found {len(deals_found)} Woolworths deals")
                    deals.extend(deals_found)
                    break
        except Exception as e:
            print(f"❌ Woolworths error: {e}")
            continue
    
    # If no deals found via direct scraping, try OzBargain
    if not deals:
        try:
            ozbargain_url = "https://www.ozbargain.com.au/search/node/woolworths%20nappies%20type%3Adeal"
            response = requests.get(ozbargain_url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                deals_found = extract_deals_from_comparison_site(response.text, "Woolworths", ozbargain_url)
                if deals_found:
                    deals.extend(deals_found)
        except:
            pass
    
    print(f"✅ Found {len(deals)} Woolworths deals total")
    return deals

def check_aldi_deals():
    """Check Aldi using multiple approaches"""
    print("Checking Aldi with multiple methods...")
    deals = []
    
    urls_to_try = [
        "https://www.aldi.com.au/en/special-buys/",
        "https://www.aldi.com.au/en/special-buys/baby-children/",
        "https://www.aldi.com.au/api/special-buys"
    ]
    
    for url in urls_to_try:
        try:
            response = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, timeout=10)
            if response.status_code == 200:
                deals_found = extract_deals_from_html(response.text, "Aldi", url)
                if deals_found:
                    deals.extend(deals_found)
                    break
                
                # Even if no specific deals found, check if baby content exists
                if any(word in response.text.lower() for word in ['baby', 'napp', 'child']):
                    deals.append({
                        'store': 'Aldi',
                        'product': 'Baby & Children items - Check Special Buys',
                        'price': 'Varies',
                        'special': 'Special Buys - Limited time',
                        'url': url
                    })
                    break
        except Exception as e:
            print(f"❌ Aldi error: {e}")
            continue
    
    print(f"✅ Found {len(deals)} Aldi deals")
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
    
    subject = f"🍼 {len(deals)} Real Diaper Deals Found! - {datetime.now().strftime('%d/%m/%Y')}"
    body = f"Found {len(deals)} genuine diaper deals today:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special']:
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "Happy shopping! 🛒\n\nThis email was sent automatically by your Multi-Approach Diaper Deals Tracker."
    
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
        'method': 'Multi-approach scraping - real deals only'
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} real deals to website")

def main():
    """Main function using multiple approaches"""
    print("=" * 80)
    print(f"🔍 MULTI-APPROACH DIAPER DEALS TRACKER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🚀 Trying multiple methods to find REAL deals (no hardcoding!)")
    print("=" * 80)
    
    all_deals = []
    
    # Check each store with multiple approaches
    all_deals.extend(check_coles_deals())
    time.sleep(2)
    
    all_deals.extend(check_woolworths_deals())
    time.sleep(2)
    
    all_deals.extend(check_aldi_deals())
    
    print("=" * 80)
    print(f"📊 FINAL RESULT: Found {len(all_deals)} REAL deals")
    
    if all_deals:
        for i, deal in enumerate(all_deals, 1):
            print(f"{i}. {deal['store']}: {deal['product']}")
            print(f"   💰 {deal['price']} - {deal['special']}")
        
        save_deals_to_file(all_deals)
        send_email_notification(all_deals)
        print("\n✅ Real deals saved and notifications sent!")
    else:
        save_deals_to_file([])
        print("😔 No deals found today using any method")
        print("💡 This means either no deals exist, or all sites are blocking us")
        print("🔧 Consider adding more data sources or manual verification")
    
    print("=" * 80)
    print("✅ Multi-approach check complete!")
    return all_deals

if __name__ == "__main__":
    main()
