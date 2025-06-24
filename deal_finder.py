import requests
from bs4 import BeautifulSoup
import json
from datetime import datetime
import smtplib
from email.mime.text import MIMEText
import os

def check_coles_deals():
    """Check Coles for diaper deals"""
    print("Checking Coles...")
    deals = []
    
    try:
        # Search for nappies/diapers on Coles
        url = "https://www.coles.com.au/search?q=nappies"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for product tiles with special offers
        products = soup.find_all('section', {'data-testid': 'product-tile'})
        
        for product in products[:10]:  # Check first 10 products
            try:
                name_element = product.find('h3')
                price_element = product.find('span', class_='price')
                special_element = product.find('span', class_='special') or product.find('div', class_='special-badge')
                link_element = product.find('a')
                
                if name_element and price_element:
                    name = name_element.get_text().strip()
                    price = price_element.get_text().strip()
                    
                    # Only include if there's a special offer or it's a good brand
                    if (special_element or 
                        any(brand in name.lower() for brand in ['huggies', 'pampers', 'babylove', 'tooshies'])):
                        
                        special_text = special_element.get_text().strip() if special_element else "Regular Price"
                        link = "https://www.coles.com.au" + link_element['href'] if link_element and link_element.get('href') else "https://www.coles.com.au"
                        
                        deals.append({
                            'store': 'Coles',
                            'product': name,
                            'price': price,
                            'special': special_text,
                            'url': link
                        })
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Error checking Coles: {e}")
    
    print(f"Found {len(deals)} Coles deals")
    return deals

def check_woolworths_deals():
    """Check Woolworths for diaper deals"""
    print("Checking Woolworths...")
    deals = []
    
    try:
        url = "https://www.woolworths.com.au/shop/search/products?searchTerm=nappies"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for product tiles with special pricing
        products = soup.find_all('div', {'data-testid': 'product-tile'})
        
        for product in products[:10]:  # Check first 10 products
            try:
                name_element = product.find('h3')
                price_element = product.find('span', class_='primary')
                special_element = product.find('div', class_='special-badge') or product.find('span', class_='was')
                link_element = product.find('a')
                
                if name_element and price_element:
                    name = name_element.get_text().strip()
                    price = price_element.get_text().strip()
                    
                    # Only include if there's a special offer or it's a good brand
                    if (special_element or 
                        any(brand in name.lower() for brand in ['huggies', 'pampers', 'babylove', 'tooshies'])):
                        
                        special_text = special_element.get_text().strip() if special_element else "Regular Price"
                        link = "https://www.woolworths.com.au" + link_element['href'] if link_element and link_element.get('href') else "https://www.woolworths.com.au"
                        
                        deals.append({
                            'store': 'Woolworths',
                            'product': name,
                            'price': price,
                            'special': special_text,
                            'url': link
                        })
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Error checking Woolworths: {e}")
    
    print(f"Found {len(deals)} Woolworths deals")
    return deals

def check_aldi_deals():
    """Check Aldi Special Buys for diapers"""
    print("Checking Aldi...")
    deals = []
    
    try:
        url = "https://www.aldi.com.au/en/special-buys/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Look for baby/diaper related items in special buys
        products = soup.find_all('div', class_='box--content')
        
        for product in products:
            try:
                title_element = product.find('h3') or product.find('h2')
                price_element = product.find('span', class_='box--price')
                
                if title_element:
                    title = title_element.get_text().strip()
                    
                    # Check if it's diaper/baby related
                    if any(word in title.lower() for word in ['napp', 'diaper', 'baby', 'toddler']):
                        price = price_element.get_text().strip() if price_element else 'Check in store'
                        
                        deals.append({
                            'store': 'Aldi',
                            'product': title,
                            'price': price,
                            'special': 'Special Buy',
                            'url': 'https://www.aldi.com.au/en/special-buys/'
                        })
            except Exception as e:
                continue
                
    except Exception as e:
        print(f"Error checking Aldi: {e}")
    
    print(f"Found {len(deals)} Aldi deals")
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
    subject = f"🍼 Daily Diaper Deals - {datetime.now().strftime('%d/%m/%Y')}"
    body = f"Found {len(deals)} diaper deals today!\n\n"
    
    for deal in deals:
        body += f"🏪 {deal['store']}\n"
        body += f"📦 {deal['product']}\n"
        body += f"💰 {deal['price']}"
        if deal['special'] != 'Regular Price':
            body += f" - {deal['special']}"
        body += f"\n🔗 {deal['url']}\n\n"
    
    body += "Happy shopping! 🛒\n\n"
    body += "This email was sent automatically by your Diaper Deals Tracker."
    
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
        'deals': deals
    }
    
    with open('docs/latest_deals.json', 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"✅ Saved {len(deals)} deals to website")

def main():
    """Main function to run daily"""
    print(f"🔍 Starting diaper deal check - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    all_deals = []
    
    # Check each store
    all_deals.extend(check_coles_deals())
    all_deals.extend(check_woolworths_deals())
    all_deals.extend(check_aldi_deals())
    
    print(f"\n📊 SUMMARY: Found {len(all_deals)} total deals")
    
    if all_deals:
        save_deals_to_file(all_deals)
        send_email_notification(all_deals)
        
        print("\n🎉 Top 3 deals today:")
        for i, deal in enumerate(all_deals[:3], 1):
            print(f"{i}. {deal['store']}: {deal['product']} - {deal['price']}")
    else:
        # Still save empty file so website shows "no deals"
        save_deals_to_file([])
        print("😔 No deals found today - better luck tomorrow!")
    
    print("\n✅ Daily check complete!")
    return all_deals

if __name__ == "__main__":
    main()
