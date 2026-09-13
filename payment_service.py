import razorpay
import logging
import config

logger = logging.getLogger("PaymentService")

class PaymentService:
    def __init__(self):
        self.client = None
        if config.RAZORPAY_KEY_ID and config.RAZORPAY_KEY_SECRET:
            try:
                self.client = razorpay.Client(auth=(config.RAZORPAY_KEY_ID, config.RAZORPAY_KEY_SECRET))
                logger.info("Razorpay Client initialized.")
            except Exception as e:
                logger.error(f"Failed to init Razorpay client: {e}")

    def create_order(self, order_id, amount_inr):
        """
        Creates an order on Razorpay.
        amount_inr is in Rupees (converted to Paise for Razorpay API).
        """
        amount_paise = int(round(amount_inr * 100))
        
        if not self.client:
            # Fallback simulator order ID
            return {
                "id": f"sim_order_{order_id}",
                "amount": amount_paise,
                "currency": config.CURRENCY,
                "is_simulation": True
            }

        try:
            rzp_order = self.client.order.create({
                "amount": amount_paise,
                "currency": config.CURRENCY,
                "receipt": f"receipt_{order_id}",
                "notes": {
                    "kiosk_order_id": order_id
                }
            })
            rzp_order["is_simulation"] = False
            return rzp_order
        except Exception as e:
            logger.error(f"Razorpay order creation failed: {e}")
            raise

    def verify_payment(self, razorpay_order_id, razorpay_payment_id, razorpay_signature):
        """
        Verifies the cryptographic HMAC signature returned by Razorpay Checkout.
        """
        if razorpay_order_id.startswith("sim_order_"):
            # Simulator check
            return True

        if not self.client:
            return False

        try:
            self.client.utility.verify_payment_signature({
                'razorpay_order_id': razorpay_order_id,
                'razorpay_payment_id': razorpay_payment_id,
                'razorpay_signature': razorpay_signature
            })
            return True
        except razorpay.errors.SignatureVerificationError as e:
            logger.error(f"Signature verification failed: {e}")
            return False

payment_service = PaymentService()
