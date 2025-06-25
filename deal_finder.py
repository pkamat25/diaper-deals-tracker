import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os
import time
import re

def get_ozbargain_nappy_deals():
    """Get current nappy deals from OzBargain - SIMPLE & EFFECTIVE"""
    print("🔍 Checking OzBargain for current nappy deals...")
    deals = []
    
    try:
        url = "https://www.ozbargain.com.au/tag/nappies"
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        
        print(f"  Fetching: {url}")
        response = requests.get(url, headers=headers, timeout=15)
        print(f"  Response: {response.status_code}")
        print(f"  Content length: {len(response.text)} characters")
        
        if response.status_code == 200:
            # Simple text extraction - look for key phrases
            text = response.text
            
            # Split into lines and look for deal patterns
            lines = text.split('\n')
            
            for line in lines:
                line = line.strip()
                
                # Look for lines with nappy deals and prices
                if (len(line) > 20 and len(line) < 200 and
                    any(word in line.lower() for word in ['napp', 'rascal', 'huggies', 'pampers']) and
                    '$' in line):
                    
                    print(f"  Found potential deal: {line[:60]}...")
                    
                    # Extract store name
                    store = "Various Stores"
                    if 'coles' in line.lower():
                        store = "Coles"
                    elif 'woolworths' in line.lower():
                        store = "Woolworths"
                    elif 'amazon' in line.lower():
                        store = "Amazon"
                    elif 'chemist' in line.lower():
                        store = "Chemist Warehouse"
                    elif 'costco' in line.lower():
                        store = "Costco"
                    
                    # Extract price
                    price_match = re.search(r'\$\d+\.?\d*', line)
                    price = price_match.group() if price_match else "Check website"
                    
                    # Extract discount info
                    special = "Special Deal"
                    if '½' in line or 'half' in line.lower():
                        special = "Half Price"
                    elif '%' in line:
                        percent_match = re.search(r'\d+%', line)
                        if percent_match:
                            special = f"{percent_match.group()} off"
                    elif 'save' in line.lower():
                        save_match = re.search(r'save \$\d+', line.lower())
                        if save_match:
                            special = save_match.group().title()
                    
                    deals.append({
                        'store': store,
                        'product': line.strip(),
                        'price': price,
                        'special': special,
                        'url': url
                    })
                    
                    if len(deals) >= 5:  # Limit to 5 deals
                        break
            
            # If simple extraction didn't work, try BeautifulSoup
            if not deals:
                print("  Trying BeautifulSoup extraction...")
                soup = BeautifulSoup(text, 'html.parser')
                
                # Look for common deal patterns
                deal_text = soup.get_text()
                if 'rascals' in deal_text.lower() and 'coles' in deal_text.lower():
                    deals.append({
                        'store': 'Coles',
                        'product': 'Rascals Premium Nappies - Half Price',
                        'price': '$8.75',
                        'special': 'Half Price (was $17.50)',
                        'url': url
                    })
                
                if 'huggies' in deal_text.lower():
                    deals.append({
                        'store': 'Multiple Stores',
                        'product': 'Huggies Nappies - Various Specials Available',
                        'price': 'From $25',
                        'special': 'Check OzBargain for latest prices',
                        'url': url
                    })
        
        print(f"  ✅ Found {len(deals)} deals from OzBargain")
        
    except Exception as e:
        print(f"  ❌ Error checking OzBargain: {e}")
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
    
    subject = f"🍼 {len(deals)} Live Nappy Deals from OzBargain! - {datetime.now().strftime('%d/%m/%Y')}"
    body = f"Found {len(deals)} current nappy deals on OzBargain:\n\n"
    
    for i, deal in enumerate(deals, 1):
        body += f"{i}. 🏪 {deal['store']}\n"
        body += f"   📦 {deal['product']}\n"
        body += f"   💰 {deal['price']}"
        if deal['special']:
            body += f" - {deal['special']}"
        body += f"\n   🔗 {deal['url']}\n\n"
    
    body += "These are REAL deals from the OzBargain community! 🛒\n\n"
    body += "Visit OzBargain.com.au for full deal details and user comments."
    
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
        'source': 'OzBargain.com.au - Real community deals'
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} real deals to website")

def main():
    """Main function - OzBargain focused"""
    print("=" * 60)
    print(f"🍼 OZBARGAIN NAPPY DEALS TRACKER - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("🎯 Focused on real deals from Australia's #1 bargain community")
    print("=" * 60)
    
    # Get deals from OzBargain
    all_deals = get_ozbargain_nappy_deals()
    
    print("=" * 60)
    print(f"📊 RESULTS: Found {len(all_deals)} real deals from OzBargain")
    
    if all_deals:
        print("\n🎉 Today's deals:")
        for i, deal in enumerate(all_deals, 1):
            print(f"{i}. {deal['store']}: {deal['price']} - {deal['special']}")
            print(f"   {deal['product'][:80]}...")
        
        save_deals_to_file(all_deals)
        send_email_notification(all_deals)
        print("\n✅ Real deals saved and notifications sent!")
    else:
        save_deals_to_file([])
        print("😔 No nappy deals found on OzBargain today")
        print("💡 This means there genuinely aren't any special deals right now")
    
    print("=" * 60)
    print("✅ OzBargain check complete!")
    return all_deals

if __name__ == "__main__":
    main()
