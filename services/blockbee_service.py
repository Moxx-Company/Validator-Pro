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
            logger.info(f"Using callback URL: {callback_url}")
            
            # Get receiving address (will raise error if not configured)
            try:
                receiving_address = self._get_receiving_address(blockbee_currency)
            except ValueError as e:
                logger.error(f"Wallet configuration error: {e}")
                return {'success': False, 'error': f'Payment not available for {currency.upper()}. Wallet address not configured.'}
            
            # Request payment address from BlockBee API
            params = {
                'callback': callback_url,
                'apikey': self.api_key,
                'address': receiving_address,
                'convert': 1,
                'pending': 1,  # Notify for pending transactions
                'post': 1,     # Use POST for webhooks  
                'json': 1      # JSON format for webhooks
            }
            
            logger.info(f"Creating BlockBee payment for {blockbee_currency}")
            logger.info(f"Request URL: {self.base_url}/{blockbee_currency}/create/")
            logger.info(f"Request params: {params}")
            response = requests.get(f"{self.base_url}/{blockbee_currency}/create/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                
                if data.get('status') == 'success':
                    payment_address = data['address_in']
                    # Get crypto amount using BlockBee conversion API
                    amount_crypto = self._get_crypto_amount(blockbee_currency, amount_usd)
                    
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
                logger.error(f"Response content: {response.text}")
                return {'success': False, 'error': 'Payment service unavailable'}
        
        except Exception as e:
            logger.error(f"Error getting payment info: {e}")
            return {'success': False, 'error': 'Payment info failed'}
    
    def _get_crypto_amount(self, currency: str, amount_usd: float) -> float:
        """Get crypto amount using BlockBee conversion API"""
        try:
            params = {
                'apikey': self.api_key,
                'value': amount_usd,
                'from': 'USD'
            }
            response = requests.get(f"{self.base_url}/{currency}/convert/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                if data.get('status') == 'success':
                    return float(data.get('value_coin', 0))
            
            # Fallback to approximate rates if API fails
            return self._calculate_crypto_amount_fallback(currency, amount_usd)
        except Exception as e:
            logger.error(f"Error converting amount: {e}")
            return self._calculate_crypto_amount_fallback(currency, amount_usd)
    
    def _calculate_crypto_amount_fallback(self, currency: str, amount_usd: float) -> float:
        """Fallback crypto amount calculation"""
        approximate_rates = {
            'btc': 0.00015,  # ~$67000 per BTC
            'eth': 0.003,    # ~$3300 per ETH
            'ltc': 0.15,     # ~$66 per LTC
            'doge': 7.5,     # ~$0.13 per DOGE
            'usdt_trc20': 9.99,  # ~$1 per USDT
            'usdt_erc20': 9.99,  # ~$1 per USDT
            'trx': 80,       # ~$0.125 per TRX
            'bnb': 0.017     # ~$580 per BNB
        }
        return approximate_rates.get(currency, 0.001) * amount_usd
    
    def _get_receiving_address(self, currency: str) -> str:
        """Get receiving address for currency from environment variables"""
        # Get wallet addresses from environment variables for security
        receiving_addresses = {
            'btc': os.getenv('BTC_WALLET_ADDRESS', ''),
            'eth': os.getenv('ETH_WALLET_ADDRESS', ''),
            'ltc': os.getenv('LTC_WALLET_ADDRESS', ''),
            'doge': os.getenv('DOGE_WALLET_ADDRESS', ''),
            'usdt_trc20': os.getenv('USDT_TRC20_WALLET_ADDRESS', ''),
            'usdt_erc20': os.getenv('USDT_ERC20_WALLET_ADDRESS', ''),
            'trx': os.getenv('TRX_WALLET_ADDRESS', ''),
            'bnb': os.getenv('BNB_WALLET_ADDRESS', '')
        }
        
        address = receiving_addresses.get(currency, '')
        if not address:
            raise ValueError(f"No receiving wallet address configured for {currency.upper()}. Please set {currency.upper()}_WALLET_ADDRESS environment variable.")
        return address
    
    def get_payment_info(self, address: str, currency: str) -> Dict:
        """Get payment information for an address"""
        try:
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
            
            blockbee_currency = currency_mapping.get(currency.lower())
            if not blockbee_currency:
                return {'success': False, 'error': 'Unsupported currency'}
            
            params = {'apikey': self.api_key}
            if address:
                params['address'] = address
            response = requests.get(f"{self.base_url}/{blockbee_currency}/info/", params=params)
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'data': data
                }
            else:
                return {'success': False, 'error': 'API request failed'}
                
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