"""
BlockBee cryptocurrency payment service integration
"""
import os
import requests
import logging
import qrcode
from io import BytesIO
from typing import Dict, Optional
from config import BLOCKBEE_API_KEY, BLOCKBEE_WEBHOOK_URL, SUPPORTED_CRYPTOS

logger = logging.getLogger(__name__)

class BlockBeeService:
    def __init__(self):
        self.api_key = BLOCKBEE_API_KEY
        self.base_url = "https://api.blockbee.io"
        self.webhook_url = BLOCKBEE_WEBHOOK_URL
    
    def create_payment_address(self, currency: str, user_id: str, amount_usd: float) -> Dict:
        """Create payment address via BlockBee API"""
        try:
            # Map our currency codes to BlockBee codes
            currency_mapping = {
                'btc': 'btc',
                'eth': 'eth', 
                'ltc': 'ltc',
                'doge': 'doge',
                'usdt_trc20': 'usdt_trc20',
                'usdt_erc20': 'usdt_erc20',
                'trx': 'trx',
                'bsc': 'bnb'
            }
            
            blockbee_currency = currency_mapping.get(currency)
            if not blockbee_currency:
                raise ValueError(f"Unsupported currency: {currency}")
            
            # Create callback URL with user info
            callback_url = f"{self.webhook_url}?user_id={user_id}&currency={currency}&amount_usd={amount_usd}"
            
            # Request payment address from BlockBee
            response = requests.post(f"{self.base_url}/{blockbee_currency}/create", {
                'apikey': self.api_key,
                'callback': callback_url,
                'address': 'your_receiving_address',  # Your receiving address
                'convert': 1  # Convert to fiat
            })
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    payment_address = data['address_in']
                    amount_crypto = data.get('amount_coin', 0)
                    
                    # Generate QR code
                    qr_image = self.generate_qr_code(payment_address, amount_crypto, currency)
                    
                    return {
                        'success': True,
                        'address': payment_address,
                        'amount_crypto': amount_crypto,
                        'amount_usd': amount_usd,
                        'currency': currency,
                        'qr_code': qr_image,
                        'reference': data.get('uuid')
                    }
                else:
                    logger.error(f"BlockBee API error: {data.get('error', 'Unknown error')}")
                    return {'success': False, 'error': data.get('error', 'Payment creation failed')}
            else:
                logger.error(f"BlockBee API request failed: {response.status_code}")
                return {'success': False, 'error': 'Payment service unavailable'}
                
        except Exception as e:
            logger.error(f"Error creating payment address: {e}")
            return {'success': False, 'error': str(e)}
    
    def generate_qr_code(self, address: str, amount: float, currency: str) -> BytesIO:
        """Generate QR code for payment"""
        try:
            # Create payment URI based on currency
            if currency == 'btc':
                uri = f"bitcoin:{address}?amount={amount}"
            elif currency == 'eth':
                uri = f"ethereum:{address}?value={amount}"
            elif currency in ['usdt_trc20', 'trx']:
                uri = f"tron:{address}?amount={amount}"
            elif currency == 'bsc':
                uri = f"bnb:{address}?amount={amount}"
            else:
                # Generic format
                uri = address
            
            # Generate QR code
            qr = qrcode.QRCode(
                version=1,
                error_correction=qrcode.constants.ERROR_CORRECT_L,
                box_size=10,
                border=4,
            )
            qr.add_data(uri)
            qr.make(fit=True)
            
            # Create image
            img = qr.make_image(fill_color="black", back_color="white")
            
            # Convert to bytes
            bio = BytesIO()
            img.save(bio, 'PNG')
            bio.seek(0)
            
            return bio
            
        except Exception as e:
            logger.error(f"Error generating QR code: {e}")
            return None
    
    def verify_payment(self, reference: str) -> Dict:
        """Verify payment status via BlockBee"""
        try:
            response = requests.get(f"{self.base_url}/info/{reference}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'confirmed': data.get('confirmed', False),
                    'amount_received': data.get('amount_received', 0),
                    'confirmations': data.get('confirmations', 0)
                }
            else:
                return {'success': False, 'error': 'Verification failed'}
                
        except Exception as e:
            logger.error(f"Error verifying payment: {e}")
            return {'success': False, 'error': str(e)}
    
    def get_crypto_price(self, currency: str) -> Optional[float]:
        """Get current crypto price in USD"""
        try:
            # Map to CoinGecko IDs
            coin_mapping = {
                'btc': 'bitcoin',
                'eth': 'ethereum',
                'ltc': 'litecoin', 
                'doge': 'dogecoin',
                'usdt_trc20': 'tether',
                'usdt_erc20': 'tether',
                'trx': 'tron',
                'bsc': 'binancecoin'
            }
            
            coin_id = coin_mapping.get(currency)
            if not coin_id:
                return None
            
            response = requests.get(
                f"https://api.coingecko.com/api/v3/simple/price?ids={coin_id}&vs_currencies=usd"
            )
            
            if response.status_code == 200:
                data = response.json()
                return data.get(coin_id, {}).get('usd')
            
            return None
            
        except Exception as e:
            logger.error(f"Error getting crypto price: {e}")
            return None
    
    def get_supported_currencies(self) -> Dict[str, str]:
        """Get list of supported cryptocurrencies"""
        return SUPPORTED_CRYPTOS