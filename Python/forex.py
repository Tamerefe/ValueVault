from urllib.request import urlopen
import xml.etree.ElementTree as ET
from termcolor import colored

try:
    response = urlopen('http://www.tcmb.gov.tr/kurlar/today.xml')
    xml = ET.parse(response)
    root = xml.getroot()

    print(colored("Currency To TL", 'yellow'))
    print('-' * 40)
    for i in root.findall('Currency'):
        currency_name = i.find('CurrencyName').text or 'N/A'
        forex_buying = i.find('ForexBuying').text or 'N/A'
        forex_selling = i.find('ForexSelling').text or 'N/A'

        print(colored(f"{currency_name}", 'cyan'))
        print(colored(f"  Forex Buying: {forex_buying}", 'green'))
        print(colored(f"  Forex Selling: {forex_selling}", 'red'))
        print('-' * 40)
except Exception as e:
    print(colored(f"An error occurred: {e}", 'red'))
