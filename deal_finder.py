import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os
import time

def check_coles_deals():
    """Check Coles for diaper deals - UPDATED VERSION"""
    print("Checking Coles specials page...")
    deals = []
    
    try:
        # Use the correct Coles specials page URL
        url = "https://www.coles.com.au/on-special/baby/nappies-nappy-pants"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        
        print(f"Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"Response status: {response.status_code}")
        
        if response.status_code != 200:
            print(f"Bad response code: {response.status_code}")
            return deals
            
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for any element containing "SPECIAL" and price information
        special_indicators = soup.find_all(text=lambda text: text and 'SPECIAL' in text.upper())
        save_indicators = soup.find_all(text=lambda text: text and 'Save $' in text)
        
        print(f"Found {len(special_indicators)} SPECIAL indicators")
        print(f"Found {len(save_indicators)} Save indicators")
        
        # Method 1: Look for price patterns in the text
        page_text = soup.get_text()
        lines = page_text.split('\n')
        
        current_deal = {}
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Look for price patterns like "$29.00"
            if line.startswith('$') and '.' in line and len(line) < 10:
                try:
                    price = float(line.replace('$', ''))
                    if price > 5 and price < 100:  # Reasonable diaper price range
                        
                        # Look for "Save" information nearby
                        context_lines = lines[max(0, i-3):i+4]
                        save_info = ""
                        was_price = ""
                        
                        for context_line in context_lines:
                            if 'Save $' in context_line:
                                save_info = context_line.strip()
                            if context_line.startswith('Was $'):
                                was_price = context_line.strip()
                        
                        if save_info or was_price:  # Only include if there's a discount
                            special_text = f"{save_info} {was_price}".strip()
                            if not special_text:
                                special_text = "Special Price"
                                
                            deals.append({
                                'store': 'Coles',
                                'product': f'Nappies Special Deal',  # Generic since we can't extract specific product names reliably
                                'price': line,
                                'special': special_text,
                                'url': url
                            })
                            
                            print(f"Found deal: {line} - {special_text}")
                            
                except ValueError:
                    continue
        
        # Method 2: Look for common diaper brands in discount context
        brand_keywords = ['huggies', 'Rascals', 'babylove', 'tooshies', 'Millie Moon','Little One']
        discount_keywords = ['special', 'save', 'was $', 'down down', '%', 'half price','online only','LOWER SHELF PRICE']
        
        for brand in brand_keywords:
            brand_mentions = soup.find_all(text=lambda text: text and brand.lower() in text.lower())
            for mention in brand_mentions:
                # Check if there's discount language nearby
                parent = mention.parent if mention.parent else None
                if parent:
                    parent_text = parent.get_text().lower()
                    if any(keyword in parent_text for keyword in discount_keywords):
                        # Try to find price in the same area
                        price_match = None
                        for sibling in parent.find_all(text=True):
                            if sibling.strip().startswith('$') and '.' in sibling:
                                price_match = sibling.strip()
                                break
                        
                        if price_match:
                            deals.append({
                                'store': 'Coles',
                                'product': f'{brand.title()} Nappies (Special)',
                                'price': price_match,
                                'special': 'Special Offer',
                                'url': url
                            })
                            print(f"Found brand deal: {brand} - {price_match}")
        
        # Remove duplicates based on price
        seen_prices = set()
        unique_deals = []
        for deal in deals:
            if deal['price'] not in seen_prices:
                seen_prices.add(deal['price'])
                unique_deals.append(deal)
        
        deals = unique_deals[:5]  # Limit to 5 deals
        
    except Exception as e:
        print(f"Error checking Coles: {e}")
        import traceback
        traceback.print_exc()
    
    print(f"✅ Found {len(deals)} Coles deals")
    return deals

def check_woolworths_deals():
    """Check Woolworths for diaper deals - IMPROVED VERSION"""
    print("Checking Woolworths...")
    deals = []
    
    try:
        # Use Woolworths specials page
        url = "https://www.woolworths.com.au/shop/browse/baby/nappies"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for special/discount indicators
        special_elements = soup.find_all(text=lambda text: text and any(word in text.lower() for word in ['special', 'save', 'was $', '%']))
        
        # Simple extraction - look for price patterns near special indicators
        if special_elements:
            page_text = soup.get_text()
            lines = page_text.split('\n')
            
            for line in lines:
                line = line.strip()
                if ('$' in line and 'save' in line.lower()) or ('$' in line and 'was $' in line.lower()):
                    if any(brand in line.lower() for brand in ['huggies', 'pampers', 'babylove', 'napp']):
                        deals.append({
                            'store': 'Woolworths',
                            'product': 'Nappies Special Deal',
                            'price': 'Check website',
                            'special': line,
                            'url': url
                        })
                        if len(deals) >= 3:  # Limit to 3 deals
                            break
        
    except Exception as e:
        print(f"Error checking Woolworths: {e}")
    
    print(f"✅ Found {len(deals)} Woolworths deals")
    return deals

def check_aldi_deals():
    """Check Aldi Special Buys for diapers - IMPROVED"""
    print("Checking Aldi...")
    deals = []
    
    try:
        url = "https://www.aldi.com.au/en/special-buys/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for baby/diaper related items
        page_text = soup.get_text().lower()
        if any(word in page_text for word in ['napp', 'diaper', 'baby care', 'toddler']):
            # If we find baby-related content, add a generic Aldi entry
            deals.append({
                'store': 'Aldi',
                'product': 'Baby Care Items - Check Special Buys',
                'price': 'Varies',
                'special': 'Special Buy - Limited Time',
                'url': url
            })
                
    except Exception as e:
        print(f"Error checking Aldi: {e}")
    
    print(f"✅ Found {len(deals)} Aldi deals")
    return deals

def send_email_notification(deals):
    """Send email with today's deals"""
    if not deals:
        print("No deals to email")
        return
    
    # Get email settings from environment variables
    sender_email = os.environ.get('GMAIL_EMAIL', 'your-email@gmail.com')
    sender_password = os.environ.get('EMAIL_PASSWORD')
    recipient_email = os.environ.get('RECIPIENT_EMAIL', sender_email)
    
    if not sender_password:
        print("No email password set - skipping email notification")
        return
    
    # Create email content
    subject = f"🍼 {len(deals)} Diaper Deals Found Today! - {datetime.now().strftime('%d/%m/%Y')}"
    body = f"Great news! Found {len(deals)} diaper deals today:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special'] != 'Regular Price':
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "Happy shopping! 🛒\n\n"
    body += "This email was sent automatically by your Diaper Deals Tracker.\n"
    body += f"Check your website for the latest deals: https://yourusername.github.io/diaper-deals-tracker"
    
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
    # Create docs directory if it doesn't exist
    os.makedirs('docs', exist_ok=True)
    
    data = {
        'date': datetime.now().isoformat(),
        'total_deals': len(deals),
        'deals': deals,
        'last_check': datetime.now().strftime('%Y-%m-%d %H:%M:%S AEST')
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} deals to website")

def main():
    """Main function to run daily"""
    print(f"🔍 Starting IMPROVED diaper deal check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 50)
    
    all_deals = []
    
    # Check each store with delays to be respectful
    all_deals.extend(check_coles_deals())
    time.sleep(3)  # Wait 3 seconds between requests
    
    all_deals.extend(check_woolworths_deals())
    time.sleep(3)
    
    all_deals.extend(check_aldi_deals())
    
    print("=" * 50)
    print(f"📊 SUMMARY: Found {len(all_deals)} total deals")
    
    if all_deals:
        save_deals_to_file(all_deals)
        send_email_notification(all_deals)
        
        print("\n🎉 All deals found today:")
        for i, deal in enumerate(all_deals, 1):
            print(f"{i}. {deal['store']}: {deal['product']} - {deal['price']}")
            if deal['special']:
                print(f"   Special: {deal['special']}")
    else:
        # Still save empty file so website shows "no deals"
        save_deals_to_file([])
        print("😔 No deals found today - the scraper might need updating")
    
    print("\n✅ Daily check complete!")
    return all_deals

if __name__ == "__main__":
    main()
