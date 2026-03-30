// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

// ==========================================
// 1. الواجهات (Interfaces)
// ==========================================

interface IERC20 {
    function totalSupply() external view returns (uint256);
    function balanceOf(address account) external view returns (uint256);
    function transfer(address recipient, uint256 amount) external returns (bool);
    function allowance(address owner, address spender) external view returns (uint256);
    function approve(address spender, uint256 amount) external returns (bool);
    function transferFrom(address sender, address recipient, uint256 amount) external returns (bool);
}

interface IPancakeRouter02 {
    function swapExactTokensForTokens(
        uint amountIn,
        uint amountOutMin,
        address[] calldata path,
        address to,
        uint deadline
    ) external returns (uint[] memory amounts);

    function getAmountsOut(uint amountIn, address[] calldata path) external view returns (uint[] memory amounts);
}

interface IPancakePair {
    function swap(uint amount0Out, uint amount1Out, address to, bytes calldata data) external;
    function token0() external view returns (address);
    function token1() external view returns (address);
}

interface IPancakeCallee {
    function pancakeCall(address sender, uint amount0, uint amount1, bytes calldata data) external;
}


// ==========================================
// عقد القناص (Flash Arbitrage Contract)
// ==========================================

contract FlashArbitrage is IPancakeCallee {
    address public owner;

    constructor() {
        // حماية العقد بحيث لا يستطيع تشغيله أو سحب أرباحه إلا أنت
        owner = msg.sender;
    }

    modifier onlyOwner() {
        require(msg.sender == owner, "Only owner can call this!");
        _;
    }

    // هيكل لتمرير البيانات من الهجوم الأولي إلى دالة الاستدعاء المعكوس (Callback)
    struct ArbitrageData {
        address router1;      // المنصة الأرخص (للشراء)
        address router2;      // المنصة الأغلى (للبيع)
        address wbnb;         // عملة WBNB (المستخدمة في القرض)
        address usdt;         // عملة USDT
        uint256 borrowAmount; // كمية القرض السريع
    }

    // ------------------------------------------------------------------------
    // 2. دالة إطلاق الهجوم (startArbitrage)
    // ------------------------------------------------------------------------
    // _pairAddress: عنوان مسبح السيولة الذي سنقترض منه WBNB (مثلاً مسبح WBNB/USDT على بانكيك سواب)
    function startArbitrage(
        address _pairAddress, 
        uint256 _amountToBorrow,
        address _wbnb,
        address _usdt,
        address _router1, 
        address _router2  
    ) external onlyOwner {
        IPancakePair pair = IPancakePair(_pairAddress);
        
        address token0 = pair.token0();
        address token1 = pair.token1();
        require(token0 == _wbnb || token1 == _wbnb, "WBNB missing in pair");

        // تحديد ما إذا كنا سنقترض token0 أم token1
        uint256 amount0Out = _wbnb == token0 ? _amountToBorrow : 0;
        uint256 amount1Out = _wbnb == token1 ? _amountToBorrow : 0;

        // تغليف بيانات المراجحة ليتم إرسالها إلى مسبح السيولة 
        // سيقوم المسبح بإرجاع هذه البيانات إلينا داخل دالة pancakeCall
        bytes memory data = abi.encode(
            ArbitrageData({
                router1: _router1,
                router2: _router2,
                wbnb: _wbnb,
                usdt: _usdt,
                borrowAmount: _amountToBorrow
            })
        );

        // تنفيذ طلب القرض السريع (Flash Swap)!
        // بمجرد استدعاء هذه الدالة، سيقوم المسبح بإرسال الـ WBNB لنا وتفعيل pancakeCall
        pair.swap(amount0Out, amount1Out, address(this), data);
    }


    // ------------------------------------------------------------------------
    // 3. دالة الاستدعاء والتنفيذ (pancakeCall) - قلب القناص
    // ------------------------------------------------------------------------
    function pancakeCall(
        address /*_sender*/,
        uint /*_amount0*/,
        uint /*_amount1*/,
        bytes calldata _data
    ) external override {
        // فك تشفير البيانات المرسلة من دالة startArbitrage
        ArbitrageData memory arbData = abi.decode(_data, (ArbitrageData));
        uint256 amountBorrowed = arbData.borrowAmount;

        // الخطوة 1: الموافقة للمنصة الأولى (الأرخص) وبيع الـ WBNB مقابل USDT
        IERC20(arbData.wbnb).approve(arbData.router1, amountBorrowed);
        
        address[] memory path1 = new address[](2);
        path1[0] = arbData.wbnb;
        path1[1] = arbData.usdt;

        // تنفيذ البيع
        uint[] memory amounts1 = IPancakeRouter02(arbData.router1).swapExactTokensForTokens(
            amountBorrowed,
            0, // نستخدم 0 كحد أدنى لأن سكربت بايثون قد تأكد بالفعل من الربحية (لكن في الإنتاج يمكن تمرير amountOutMin)
            path1,
            address(this),
            block.timestamp
        );
        uint256 usdtReceived = amounts1[1]; // كمية USDT التي حصلنا عليها الآن


        // الخطوة 2: الموافقة للمنصة الثانية (الأغلى) وبيع الـ USDT لاسترجاع كمية أكبر من الـ WBNB
        IERC20(arbData.usdt).approve(arbData.router2, usdtReceived);
        
        address[] memory path2 = new address[](2);
        path2[0] = arbData.usdt;
        path2[1] = arbData.wbnb;

        // تنفيذ البيع العكسي
        uint[] memory amounts2 = IPancakeRouter02(arbData.router2).swapExactTokensForTokens(
            usdtReceived,
            0,
            path2,
            address(this),
            block.timestamp
        );
        uint256 wbnbReturned = amounts2[1]; // كمية WBNB التي عدنا بها


        // الخطوة 3: حساب رسوم القرض والتأكد من الربحية
        // يجب إرجاع القرض + 0.3% رسوم مسبح السيولة
        // المعادلة: (amountBorrowed * 1000 / 997) + 1 لتفادي أعطال كسر العملة
        uint256 fee = ((amountBorrowed * 3) / 997) + 1;
        uint256 amountToRepay = amountBorrowed + fee;

        // التحذير الصارم: إذا لم يغطي المبلغ الراجع قيمة القرض ورسومه... سيعكس العقد الترانزكشن بالكامل!
        require(wbnbReturned > amountToRepay, "Transaction failed: Arbitrage not profitable!");

        // الخطوة 4: تسديد القرض + الرسوم للمسبح الأصلي (msg.sender هنا هو مسبح السيولة الذي طلبنا منه)
        IERC20(arbData.wbnb).transfer(msg.sender, amountToRepay);

        // تم التنفيذ بنجاح! الربح الصافي يبقى مخزناً داخل العقد الذكي إلى حين سحبه.
    }


    // ------------------------------------------------------------------------
    // 4. دالة سحب الأرباح (withdrawProfits)
    // ------------------------------------------------------------------------
    function withdrawProfits(address _token) external onlyOwner {
        uint256 balance = IERC20(_token).balanceOf(address(this));
        require(balance > 0, "No funds to withdraw");
        
        // إرسال جميع الأرباح المتراكمة إلى محفظة المالك
        IERC20(_token).transfer(owner, balance);
    }
    
    // استقبال الرمز الأصلي للشبكة إن تم إرساله بالخطأ
    receive() external payable {}
}
