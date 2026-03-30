import time
from web3 import Web3
import getpass

def main():
    print("💰 مرحباً بك في سكربت سحب الأرباح التلقائي 💰")
    print("-" * 50)
    
    # 1. الاتصال بالشبكة الرئيسية (BSC Mainnet)
    bsc_mainnet_url = "https://bsc-dataseed.binance.org/"
    w3 = Web3(Web3.HTTPProvider(bsc_mainnet_url))

    if not w3.is_connected():
        print("❌ فشل الاتصال بشبكة BSC Mainnet. تأكد من الإنترنت أو حالة الـ RPC.")
        return
    print("✅ تم الاتصال بشبكة BSC Mainnet بنجاح.")

    # 2. الأمان: طلب الـ Private Key
    private_key = getpass.getpass("🔑 أدخل الـ Private Key الخاص بمحفظتك (لن يظهر على الشاشة): ")
    if not private_key:
        print("❌ لم يتم إدخال الـ Private Key.")
        return

    try:
        account = w3.eth.account.from_key(private_key)
        my_address = account.address
        print(f"👤 سيتم طلب السحب للمحفظة: {my_address}")
    except Exception as e:
        print(f"❌ خطأ في الـ Private Key: {e}")
        return

    # 3. تهيئة العقد الذكي
    # ضع هنا عنوان العقد الذكي الخاص بك الذي رفعته مؤخراً للشبكة الرئيسية
    FLASH_ARBITRAGE_ADDRESS = w3.to_checksum_address("0x077125c612F3703bBaF7135F1A177E9C44b0Ba7F") # قم بتغييره إذا تم نشر عقد آخر

    # الـ ABI المبسط الذي يحتوي على دالة withdrawProfits فقط
    FLASH_ARBITRAGE_ABI = [
        {
            "inputs": [
                {"internalType": "address", "name": "_token", "type": "address"}
            ],
            "name": "withdrawProfits",
            "outputs": [],
            "stateMutability": "nonpayable",
            "type": "function"
        }
    ]

    try:
        flash_contract = w3.eth.contract(address=FLASH_ARBITRAGE_ADDRESS, abi=FLASH_ARBITRAGE_ABI)
    except Exception as e:
        print(f"❌ يرجى التأكد من وضع عنوان عقدك الذكي بشكل صحيح في المتغير FLASH_ARBITRAGE_ADDRESS\nالتفاصيل: {e}")
        return

    # عناوين العملات للسحب (WBNB و USDT)
    WBNB_ADDRESS = w3.to_checksum_address("0xbb4CdB9CBd36B01bD1cBaEBF2De08d9173bc095c")
    USDT_ADDRESS = w3.to_checksum_address("0x55d398326f99059fF775485246999027B3197955")

    print("\nأرباح أي عملة تريد سحبها؟")
    print("1: WBNB")
    print("2: USDT")
    choice = input("👉 اختر (1 أو 2): ")

    if choice == '1':
        token_to_withdraw = WBNB_ADDRESS
        token_name = "WBNB"
    elif choice == '2':
        token_to_withdraw = USDT_ADDRESS
        token_name = "USDT"
    else:
        print("❌ اختيار غير صحيح، تم إيقاف السكربت.")
        return

    # 4. التنفيذ: بناء وإرسال معاملة السحب
    print(f"\n📦 جاري بناء معاملة لطلب سحب أرباحك ({token_name})...")
    try:
        nonce = w3.eth.get_transaction_count(my_address)
        
        transaction = flash_contract.functions.withdrawProfits(token_to_withdraw).build_transaction({
            'chainId': 56, # BSC Mainnet
            'gas': 100000, # 100 ألف غاز تعتبر أكثر من كافية لعملية تحويل بسيطة
            'gasPrice': w3.eth.gas_price,
            'nonce': nonce,
            'from': my_address
        })

        print("✍️ جاري توقيع المعاملة...")
        signed_txn = w3.eth.account.sign_transaction(transaction, private_key=private_key)

        print("🚀 جاري الإرسال للشبكة الرئيسية...")
        # دعم للنسخ القديمة والحديثة من بطاقات مكتبة Web3.py
        raw_tx = signed_txn.raw_transaction if hasattr(signed_txn, 'raw_transaction') else signed_txn.rawTransaction
        tx_hash = w3.eth.send_raw_transaction(raw_tx)

        # 5. التأكيد
        hash_hex = w3.to_hex(tx_hash)
        print(f"✅ تم الإرسال للشبكة بنجاح!")
        print(f"🔗 الهاش (Tx Hash): {hash_hex}")
        print(f"🔍 تابع العملية بـ BscScan: https://bscscan.com/tx/{hash_hex}")
        
        print("\n⏳ ننتظر تأكيد بلوك تشين باينانس... الرجاء الانتظار قليلاً...")
        w3.eth.wait_for_transaction_receipt(tx_hash)
        print(f"🎉 مبارك! وصلت أرباحك الصافية من {token_name} إلى محفظتك ({my_address}).")

    except Exception as e:
        print(f"❌ حدث خطأ أثناء السحب (قد لا تملك العقدة سيولة حالياً أو غاز المحفظة لا يكفي): {e}")

if __name__ == "__main__":
    main()
