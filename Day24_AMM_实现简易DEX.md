# Day 24: AMM 实战 —— 手写简易版 Uniswap

> **学习时间**：6-8 小时（理论 1h + 实战 6h + 复习 1h）
> 
> **核心目标**：从零实现一个符合 $x \times y = k$ 恒定乘积公式的完整 AMM 合约，包含流动性管理、代币兑换、手续费累积、安全防护，并通过 Foundry 全面测试后部署。

---

## 🎯 今日学习目标

- [ ] 实现 **CPMM** (Constant Product Market Maker) 核心逻辑
- [ ] 编写 **addLiquidity** 与 **removeLiquidity** (LP Token 铸造与销毁)
- [ ] 编写 **swap** 函数 (含 0.3% 手续费扣除)
- [ ] 实现 **Quote 函数** 用于前端报价
- [ ] 实现 **MINIMUM_LIQUIDITY** 防止价格操纵
- [ ] 添加 **Events** 用于链下索引
- [ ] 使用 **Foundry Fuzz Testing** 验证 $k$ 值不变量
- [ ] 编写 **部署脚本** 并部署到测试网

---

## 📚 理论复习：核心公式代码化

### 1. 铸造 LP Token (Liquidity Provision)

当第一个用户添加流动性时：
$$ \text{Shares} = \sqrt{x \cdot y} - \text{MINIMUM\_LIQUIDITY} $$

> **为什么要锁定 MINIMUM_LIQUIDITY？**
> 防止第一个 LP 用极小的数量创建池子然后操纵价格。Uniswap V2 永久锁定前 1000 wei 的 LP token 到零地址。

后续用户添加时，按比例铸造：
$$ \text{Shares} = \min \left( \frac{\Delta x}{X} \times S, \frac{\Delta y}{Y} \times S \right) $$

### 2. 兑换 (Swap)

基于公式 $\Delta y = \frac{y \cdot \Delta x}{x + \Delta x}$。

**含手续费的精确公式** (使用整数运算避免精度损失):
```solidity
amountOut = (amountIn * 997 * reserveOut) / (reserveIn * 1000 + amountIn * 997)
```

### 3. 移除流动性

按 LP 比例取回两种代币：
$$ \text{amount0} = \frac{\text{shares}}{S} \times x $$
$$ \text{amount1} = \frac{\text{shares}}{S} \times y $$

---

## 🛠️ 实战：构建完整 SimpleAMM

### 1. 项目初始化

```bash
mkdir -p ~/blockchain-course/week4/day24_amm_impl
cd ~/blockchain-course/week4/day24_amm_impl
forge init --no-commit

# 安装 OpenZeppelin
forge install OpenZeppelin/openzeppelin-contracts --no-commit

# 创建 remappings
cat > remappings.txt << 'EOF'
@openzeppelin/=lib/openzeppelin-contracts/
EOF
```

### 2. Mock Token `src/MockERC20.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";

/// @title MockERC20
/// @notice 用于测试的 ERC20 代币
contract MockERC20 is ERC20 {
    uint8 private _decimals;

    constructor(
        string memory name,
        string memory symbol,
        uint8 decimals_
    ) ERC20(name, symbol) {
        _decimals = decimals_;
    }

    function decimals() public view override returns (uint8) {
        return _decimals;
    }

    /// @notice 任何人都可以 mint (仅用于测试)
    function mint(address to, uint256 amount) external {
        _mint(to, amount);
    }

    /// @notice 任何人都可以 burn (仅用于测试)
    function burn(address from, uint256 amount) external {
        _burn(from, amount);
    }
}
```

### 3. 完整 AMM 合约 `src/SimpleAMM.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/IERC20.sol";
import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/utils/SafeERC20.sol";
import "@openzeppelin/contracts/security/ReentrancyGuard.sol";
import "@openzeppelin/contracts/utils/math/Math.sol";

/// @title SimpleAMM
/// @notice 一个简化版的 Uniswap V2 风格 AMM
/// @dev LP Token 本身也是一个 ERC-20
contract SimpleAMM is ERC20, ReentrancyGuard {
    using SafeERC20 for IERC20;

    // ============ 错误定义 ============
    error InvalidToken();
    error ZeroShares();
    error ZeroAmount();
    error InsufficientOutput();
    error InsufficientLiquidity();
    error InvariantViolation();

    // ============ 常量 ============
    uint256 public constant MINIMUM_LIQUIDITY = 1000;
    uint256 public constant FEE_NUMERATOR = 997;
    uint256 public constant FEE_DENOMINATOR = 1000;

    // ============ 状态变量 ============
    IERC20 public immutable token0;
    IERC20 public immutable token1;

    // 储备量 (缓存值，防止闪电贷操纵)
    uint256 public reserve0;
    uint256 public reserve1;

    // 累积手续费 (用于协议分成，本合约简化未使用)
    uint256 public kLast;

    // ============ 事件 ============
    event Mint(address indexed sender, uint256 amount0, uint256 amount1, uint256 shares);
    event Burn(address indexed sender, uint256 amount0, uint256 amount1, uint256 shares, address indexed to);
    event Swap(
        address indexed sender,
        uint256 amount0In,
        uint256 amount1In,
        uint256 amount0Out,
        uint256 amount1Out,
        address indexed to
    );
    event Sync(uint256 reserve0, uint256 reserve1);

    // ============ 构造函数 ============
    constructor(
        address _token0,
        address _token1,
        string memory _name,
        string memory _symbol
    ) ERC20(_name, _symbol) {
        token0 = IERC20(_token0);
        token1 = IERC20(_token1);
    }

    // ============ 读取函数 ============

    /// @notice 获取两个代币的储备量
    function getReserves() external view returns (uint256, uint256) {
        return (reserve0, reserve1);
    }

    /// @notice 获取当前价格 (token1 / token0)
    function getPrice() external view returns (uint256) {
        if (reserve0 == 0) return 0;
        return (reserve1 * 1e18) / reserve0;
    }

    /// @notice 预估交易输出 (报价函数)
    function quote(address tokenIn, uint256 amountIn) external view returns (uint256 amountOut) {
        if (tokenIn != address(token0) && tokenIn != address(token1)) revert InvalidToken();
        if (amountIn == 0) return 0;

        bool isToken0 = tokenIn == address(token0);
        (uint256 rIn, uint256 rOut) = isToken0 ? (reserve0, reserve1) : (reserve1, reserve0);

        uint256 amountInWithFee = amountIn * FEE_NUMERATOR;
        amountOut = (amountInWithFee * rOut) / (rIn * FEE_DENOMINATOR + amountInWithFee);
    }

    /// @notice 计算添加流动性获得的 LP 份额
    function quoteAddLiquidity(uint256 amount0, uint256 amount1) external view returns (uint256 shares) {
        uint256 _totalSupply = totalSupply();
        
        if (_totalSupply == 0) {
            shares = Math.sqrt(amount0 * amount1) - MINIMUM_LIQUIDITY;
        } else {
            uint256 share0 = (amount0 * _totalSupply) / reserve0;
            uint256 share1 = (amount1 * _totalSupply) / reserve1;
            shares = share0 < share1 ? share0 : share1;
        }
    }

    // ============ 流动性管理 ============

    /// @notice 添加流动性
    /// @param amount0Desired 希望添加的 token0 数量
    /// @param amount1Desired 希望添加的 token1 数量
    /// @return shares 获得的 LP 份额
    function addLiquidity(uint256 amount0Desired, uint256 amount1Desired) 
        external 
        nonReentrant 
        returns (uint256 shares) 
    {
        // 1. 转入代币
        token0.safeTransferFrom(msg.sender, address(this), amount0Desired);
        token1.safeTransferFrom(msg.sender, address(this), amount1Desired);

        // 2. 获取实际余额 (支持有转账税的代币)
        uint256 balance0 = token0.balanceOf(address(this));
        uint256 balance1 = token1.balanceOf(address(this));
        uint256 amount0 = balance0 - reserve0;
        uint256 amount1 = balance1 - reserve1;

        // 3. 计算 LP 份额
        uint256 _totalSupply = totalSupply();
        
        if (_totalSupply == 0) {
            // 初始流动性
            shares = Math.sqrt(amount0 * amount1) - MINIMUM_LIQUIDITY;
            // 永久锁定 MINIMUM_LIQUIDITY 到零地址
            _mint(address(0xdead), MINIMUM_LIQUIDITY);
        } else {
            // 后续流动性: 取两者较小值
            uint256 share0 = (amount0 * _totalSupply) / reserve0;
            uint256 share1 = (amount1 * _totalSupply) / reserve1;
            shares = share0 < share1 ? share0 : share1;
        }

        if (shares == 0) revert ZeroShares();

        // 4. 铸造 LP 给用户
        _mint(msg.sender, shares);

        // 5. 更新储备
        _update(balance0, balance1);

        emit Mint(msg.sender, amount0, amount1, shares);
    }

    /// @notice 移除流动性
    /// @param shares 要销毁的 LP 份额
    /// @return amount0 取回的 token0 数量
    /// @return amount1 取回的 token1 数量
    function removeLiquidity(uint256 shares) 
        external 
        nonReentrant 
        returns (uint256 amount0, uint256 amount1) 
    {
        if (shares == 0) revert ZeroShares();

        uint256 _totalSupply = totalSupply();
        
        // 1. 计算应得的代币份额
        amount0 = (shares * reserve0) / _totalSupply;
        amount1 = (shares * reserve1) / _totalSupply;

        if (amount0 == 0 || amount1 == 0) revert ZeroAmount();

        // 2. 销毁 LP
        _burn(msg.sender, shares);

        // 3. 转出代币
        token0.safeTransfer(msg.sender, amount0);
        token1.safeTransfer(msg.sender, amount1);

        // 4. 更新储备
        _update(token0.balanceOf(address(this)), token1.balanceOf(address(this)));

        emit Burn(msg.sender, amount0, amount1, shares, msg.sender);
    }

    // ============ 交易功能 ============

    /// @notice 兑换代币
    /// @param tokenIn 输入代币地址
    /// @param amountIn 输入数量
    /// @param amountOutMin 最小输出数量 (滑点保护)
    /// @return amountOut 实际输出数量
    function swap(address tokenIn, uint256 amountIn, uint256 amountOutMin) 
        external 
        nonReentrant 
        returns (uint256 amountOut) 
    {
        if (tokenIn != address(token0) && tokenIn != address(token1)) revert InvalidToken();
        if (amountIn == 0) revert ZeroAmount();

        // 1. 确定输入输出方向
        bool isToken0 = tokenIn == address(token0);
        (IERC20 tIn, IERC20 tOut, uint256 rIn, uint256 rOut) = isToken0
            ? (token0, token1, reserve0, reserve1)
            : (token1, token0, reserve1, reserve0);

        // 2. 转入代币
        tIn.safeTransferFrom(msg.sender, address(this), amountIn);

        // 3. 获取实际转入量
        uint256 balanceIn = tIn.balanceOf(address(this));
        uint256 actualAmountIn = balanceIn - (isToken0 ? reserve0 : reserve1);

        // 4. 计算输出 (含 0.3% 手续费)
        uint256 amountInWithFee = actualAmountIn * FEE_NUMERATOR;
        amountOut = (amountInWithFee * rOut) / (rIn * FEE_DENOMINATOR + amountInWithFee);

        if (amountOut < amountOutMin) revert InsufficientOutput();
        if (amountOut >= rOut) revert InsufficientLiquidity();

        // 5. 转出代币
        tOut.safeTransfer(msg.sender, amountOut);

        // 6. 更新储备并验证 K 值
        uint256 balance0 = token0.balanceOf(address(this));
        uint256 balance1 = token1.balanceOf(address(this));

        // K 值检查 (考虑手续费后应该增加)
        uint256 kAfter = balance0 * balance1;
        uint256 kBefore = reserve0 * reserve1;
        if (kAfter < kBefore) revert InvariantViolation();

        _update(balance0, balance1);

        // 7. 发出事件
        (uint256 amount0In, uint256 amount1In, uint256 amount0Out, uint256 amount1Out) = isToken0
            ? (actualAmountIn, uint256(0), uint256(0), amountOut)
            : (uint256(0), actualAmountIn, amountOut, uint256(0));

        emit Swap(msg.sender, amount0In, amount1In, amount0Out, amount1Out, msg.sender);
    }

    // ============ 强制同步 ============

    /// @notice 强制同步储备与实际余额 (用于捐赠等特殊情况)
    function sync() external nonReentrant {
        _update(token0.balanceOf(address(this)), token1.balanceOf(address(this)));
    }

    // ============ 内部函数 ============

    function _update(uint256 balance0, uint256 balance1) private {
        reserve0 = balance0;
        reserve1 = balance1;
        kLast = balance0 * balance1;
        emit Sync(reserve0, reserve1);
    }
}
```

### 4. 完整测试 `test/SimpleAMM.t.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SimpleAMM.sol";
import "../src/MockERC20.sol";

contract SimpleAMMTest is Test {
    SimpleAMM public amm;
    MockERC20 public tokenA;
    MockERC20 public tokenB;

    address public alice = address(0x1);
    address public bob = address(0x2);

    uint256 constant INITIAL_BALANCE = 1_000_000 ether;

    function setUp() public {
        // 部署代币
        tokenA = new MockERC20("Token A", "TKA", 18);
        tokenB = new MockERC20("Token B", "TKB", 18);

        // 部署 AMM
        amm = new SimpleAMM(
            address(tokenA),
            address(tokenB),
            "TKA-TKB LP",
            "TKA-TKB"
        );

        // 给用户铸造代币
        tokenA.mint(alice, INITIAL_BALANCE);
        tokenB.mint(alice, INITIAL_BALANCE);
        tokenA.mint(bob, INITIAL_BALANCE);
        tokenB.mint(bob, INITIAL_BALANCE);

        // 用户授权
        vm.prank(alice);
        tokenA.approve(address(amm), type(uint256).max);
        vm.prank(alice);
        tokenB.approve(address(amm), type(uint256).max);
        vm.prank(bob);
        tokenA.approve(address(amm), type(uint256).max);
        vm.prank(bob);
        tokenB.approve(address(amm), type(uint256).max);
    }

    // ============ 基础测试 ============

    function testAddLiquidityInitial() public {
        vm.prank(alice);
        uint256 shares = amm.addLiquidity(1000 ether, 1000 ether);

        // sqrt(1000e18 * 1000e18) - 1000 = 1000e18 - 1000
        assertApproxEqAbs(shares, 1000 ether - 1000, 1);
        
        (uint256 r0, uint256 r1) = amm.getReserves();
        assertEq(r0, 1000 ether);
        assertEq(r1, 1000 ether);
    }

    function testAddLiquiditySubsequent() public {
        // Alice 添加初始流动性
        vm.prank(alice);
        amm.addLiquidity(1000 ether, 2000 ether);

        // Bob 添加流动性 (按比例)
        vm.prank(bob);
        uint256 shares = amm.addLiquidity(500 ether, 1000 ether);

        // Bob 应该获得 Alice 份额的一半
        uint256 aliceShares = amm.balanceOf(alice);
        assertApproxEqRel(shares, aliceShares / 2, 0.01e18); // 1% 误差
    }

    function testRemoveLiquidity() public {
        vm.prank(alice);
        uint256 shares = amm.addLiquidity(1000 ether, 1000 ether);

        vm.prank(alice);
        (uint256 amount0, uint256 amount1) = amm.removeLiquidity(shares);

        // 应该取回几乎所有 (减去锁定的 MINIMUM_LIQUIDITY)
        assertApproxEqRel(amount0, 1000 ether, 0.01e18);
        assertApproxEqRel(amount1, 1000 ether, 0.01e18);
    }

    function testSwap() public {
        // 添加流动性
        vm.prank(alice);
        amm.addLiquidity(10 ether, 20000 ether); // 1 ETH = 2000 USDT

        // Bob 交换
        uint256 bobBalanceBefore = tokenB.balanceOf(bob);
        
        vm.prank(bob);
        uint256 amountOut = amm.swap(address(tokenA), 1 ether, 0);

        uint256 bobBalanceAfter = tokenB.balanceOf(bob);
        assertEq(bobBalanceAfter - bobBalanceBefore, amountOut);

        // 输出应该接近 ~1800 (考虑滑点和手续费)
        assertGt(amountOut, 1700 ether);
        assertLt(amountOut, 2000 ether);
    }

    function testQuote() public {
        vm.prank(alice);
        amm.addLiquidity(10 ether, 20000 ether);

        uint256 quoted = amm.quote(address(tokenA), 1 ether);

        // 实际交换应该和报价一致
        vm.prank(bob);
        uint256 actual = amm.swap(address(tokenA), 1 ether, 0);

        assertEq(quoted, actual);
    }

    function testSlippageProtection() public {
        vm.prank(alice);
        amm.addLiquidity(10 ether, 20000 ether);

        // 设置过高的最小输出
        vm.prank(bob);
        vm.expectRevert(SimpleAMM.InsufficientOutput.selector);
        amm.swap(address(tokenA), 1 ether, 2000 ether); // 不可能获得 2000
    }

    // ============ Fuzz 测试 ============

    function testFuzz_SwapIncreasesK(uint256 amountIn) public {
        // 约束输入范围
        amountIn = bound(amountIn, 0.001 ether, 100 ether);

        // 添加初始流动性
        vm.prank(alice);
        amm.addLiquidity(100 ether, 100 ether);

        (uint256 r0Before, uint256 r1Before) = amm.getReserves();
        uint256 kBefore = r0Before * r1Before;

        // 执行 Swap
        vm.prank(bob);
        amm.swap(address(tokenA), amountIn, 0);

        (uint256 r0After, uint256 r1After) = amm.getReserves();
        uint256 kAfter = r0After * r1After;

        // K 值应该增加 (因为手续费)
        assertGe(kAfter, kBefore, "K should not decrease");
    }

    function testFuzz_AddRemoveLiquidity(uint256 amount0, uint256 amount1) public {
        // 约束输入
        amount0 = bound(amount0, 1000, 1_000_000 ether);
        amount1 = bound(amount1, 1000, 1_000_000 ether);

        // Alice 添加流动性
        vm.prank(alice);
        uint256 shares = amm.addLiquidity(amount0, amount1);

        // Alice 移除全部流动性
        vm.prank(alice);
        (uint256 out0, uint256 out1) = amm.removeLiquidity(shares);

        // 应该取回接近原始数量 (减去锁定部分)
        assertApproxEqRel(out0, amount0, 0.01e18);
        assertApproxEqRel(out1, amount1, 0.01e18);
    }

    // ============ 边界测试 ============

    function testMinimumLiquidityLocked() public {
        vm.prank(alice);
        amm.addLiquidity(1000 ether, 1000 ether);

        // 检查死地址持有 MINIMUM_LIQUIDITY
        uint256 lockedLP = amm.balanceOf(address(0xdead));
        assertEq(lockedLP, 1000);
    }

    function testSyncAfterDonation() public {
        vm.prank(alice);
        amm.addLiquidity(1000 ether, 1000 ether);

        // 直接向合约捐赠代币 (不通过 addLiquidity)
        tokenA.mint(address(amm), 100 ether);

        // 储备应该还是旧值
        (uint256 r0Before, ) = amm.getReserves();
        assertEq(r0Before, 1000 ether);

        // 调用 sync
        amm.sync();

        // 储备应该更新
        (uint256 r0After, ) = amm.getReserves();
        assertEq(r0After, 1100 ether);
    }
}
```

### 5. 部署脚本 `script/DeployAMM.s.sol`

```solidity
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Script.sol";
import "../src/SimpleAMM.sol";
import "../src/MockERC20.sol";

contract DeployAMMScript is Script {
    function run() external {
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        address deployer = vm.addr(deployerPrivateKey);

        vm.startBroadcast(deployerPrivateKey);

        // 1. 部署测试代币
        MockERC20 tokenA = new MockERC20("Token A", "TKA", 18);
        MockERC20 tokenB = new MockERC20("Token B", "TKB", 18);
        
        console.log("Token A deployed to:", address(tokenA));
        console.log("Token B deployed to:", address(tokenB));

        // 2. 部署 AMM
        SimpleAMM amm = new SimpleAMM(
            address(tokenA),
            address(tokenB),
            "TKA-TKB LP Token",
            "TKA-TKB-LP"
        );
        
        console.log("SimpleAMM deployed to:", address(amm));

        // 3. 铸造初始代币
        tokenA.mint(deployer, 10000 ether);
        tokenB.mint(deployer, 10000 ether);

        // 4. 授权 AMM
        tokenA.approve(address(amm), type(uint256).max);
        tokenB.approve(address(amm), type(uint256).max);

        // 5. 添加初始流动性
        uint256 shares = amm.addLiquidity(1000 ether, 1000 ether);
        console.log("Initial LP shares:", shares);

        vm.stopBroadcast();
    }
}
```

### 6. 运行测试与部署

```bash
# 运行所有测试
forge test -vvv

# 运行 Fuzz 测试 (更多迭代)
forge test --match-test "testFuzz" -vvv --fuzz-runs 1000

# 部署到 Sepolia
forge script script/DeployAMM.s.sol:DeployAMMScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --verify

# 本地测试 (Anvil)
anvil &
forge script script/DeployAMM.s.sol:DeployAMMScript \
    --rpc-url http://localhost:8545 \
    --broadcast
```

---

## 📝 课后作业

1. **Router 合约**：
   - 实现 `Router.sol`，支持多池路由 (A -> B -> C)
   - 添加 deadline 参数防止交易被延迟执行

2. **闪电贷 (Flash Loan)**：
   - 添加 `flashLoan(amount0, amount1, data)` 函数
   - 允许用户在同一交易内借出并归还代币

3. **协议手续费**：
   - 添加 `feeTo` 地址，在 swap 时抽取 0.05% 给协议
   - 实现 `setFeeTo` 函数 (仅 Owner 可调用)

4. **Gas 优化**：
   - 使用 `unchecked` 优化已知安全的算术运算
   - 分析并优化存储布局

---

## 🔗 参考资料

- [Uniswap V2 Core Contract](https://github.com/Uniswap/v2-core/blob/master/contracts/UniswapV2Pair.sol)
- [Uniswap V2 Periphery](https://github.com/Uniswap/v2-periphery)
- [Solidity by Example: DeFi AMM](https://solidity-by-example.org/defi/constant-product-amm/)
- [Foundry Book: Fuzz Testing](https://book.getfoundry.sh/forge/fuzz-testing)
