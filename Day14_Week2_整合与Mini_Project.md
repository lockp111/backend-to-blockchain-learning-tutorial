# Day 14: Week 2 整合与 Mini Project

> **学习时间**：4-6 小时（复习 1h + 项目开发 3-4h + 部署 1h）
>
> **核心目标**：整合 Week 2 所学知识，完成 ERC-20 代币项目并部署到测试网

---

## 🎯 今日学习目标

- [ ] 回顾 Week 2 核心知识点
- [ ] 完成 Mini Project：功能完整的 ERC-20 代币
- [ ] 部署合约到 Sepolia 测试网
- [ ] 在 Etherscan 上验证合约源码

---

## 📚 Week 2 知识点复习

### 知识图谱

```
Week 2: 闪电网络 + EVM 基础
│
├── Day 8: 闪电网络基础
│   ├── 支付通道生命周期 (Funding → Commitment → Closing)
│   ├── HTLC 哈希时间锁合约
│   ├── BOLT-11 发票标准
│   └── Polar 本地测试环境
│
├── Day 9: LND 开发 (Go)
│   ├── LND 架构与组件
│   ├── gRPC API 集成
│   ├── Macaroon 鉴权
│   └── 发票生成与支付监听
│
├── Day 10: 以太坊基础
│   ├── UTXO vs Account 模型
│   ├── EOA vs Contract Account
│   ├── EVM 架构 (Stack/Memory/Storage)
│   ├── Gas 机制与 EIP-1559
│   └── MPT 状态存储
│
├── Day 11: Go 客户端开发
│   ├── 交易构造与签名
│   ├── Nonce 管理
│   ├── Multicall 批量调用
│   └── Rate Limiting 与 Failover
│
├── Day 12: Foundry 入门
│   ├── forge/cast/anvil 工具
│   ├── 合约编写与测试
│   ├── Gas 报告
│   └── AI 辅助生成测试
│
└── Day 13: Solidity 基础
    ├── 数据类型与存储位置
    ├── 函数可见性
    ├── 修饰器与事件
    ├── ERC-20 标准
    └── Fuzz 测试
```

---

### 核心概念速查表

| 概念             | 要点                         |
| ---------------- | ---------------------------- |
| **闪电网络**     | Layer 2 支付通道，链下交易   |
| **HTLC**         | 原子性多跳支付，哈希+时间锁  |
| **Account 模型** | 全局状态，Nonce 防重放       |
| **EVM**          | Stack-based 虚拟机，Gas 计量 |
| **EIP-1559**     | 基础费用燃烧 + 小费          |
| **Multicall**    | 批量 eth_call，减少 RPC 次数 |
| **Foundry**      | Rust 编写，Solidity 测试     |
| **ERC-20**       | 代币标准接口                 |

---

## 🏗️ Mini Project: 功能完整的 ERC-20 代币

### 项目要求

构建一个具有以下特性的 ERC-20 代币：

1. **基础 ERC-20 功能**
2. **所有者权限控制**
3. **铸造与销毁功能**
4. **暂停功能**
5. **完整的测试套件**
6. **部署到 Sepolia 测试网**

---

### 项目结构

```bash
mkdir -p ~/blockchain-course/week2-mini-project
cd ~/blockchain-course/week2-mini-project
forge init

# 安装 OpenZeppelin
forge install OpenZeppelin/openzeppelin-contracts --no-commit

# 更新 foundry.toml 添加 remappings
echo 'remappings = ["@openzeppelin/=lib/openzeppelin-contracts/"]' >> foundry.toml
```

---

### 合约实现

```solidity
// src/AdvancedToken.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "@openzeppelin/contracts/token/ERC20/ERC20.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Burnable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Pausable.sol";
import "@openzeppelin/contracts/access/Ownable.sol";
import "@openzeppelin/contracts/token/ERC20/extensions/ERC20Permit.sol";

/// @title AdvancedToken - Week 2 Mini Project
/// @notice 具有铸造、销毁、暂停、Permit 功能的 ERC-20 代币
contract AdvancedToken is ERC20, ERC20Burnable, ERC20Pausable, Ownable, ERC20Permit {
    /// @notice 最大供应量 (1 亿)
    uint256 public constant MAX_SUPPLY = 100_000_000 * 10 ** 18;
    
    /// @notice 铸造事件
    event TokensMinted(address indexed to, uint256 amount);
    
    /// @notice 构造函数
    /// @param name_ 代币名称
    /// @param symbol_ 代币符号
    /// @param initialSupply 初始供应量
    constructor(
        string memory name_,
        string memory symbol_,
        uint256 initialSupply
    ) 
        ERC20(name_, symbol_) 
        Ownable(msg.sender) 
        ERC20Permit(name_) 
    {
        require(initialSupply * 10 ** decimals() <= MAX_SUPPLY, "Exceeds max supply");
        _mint(msg.sender, initialSupply * 10 ** decimals());
    }
    
    /// @notice 铸造代币 (仅所有者)
    /// @param to 接收地址
    /// @param amount 铸造数量
    function mint(address to, uint256 amount) public onlyOwner {
        require(totalSupply() + amount <= MAX_SUPPLY, "Exceeds max supply");
        _mint(to, amount);
        emit TokensMinted(to, amount);
    }
    
    /// @notice 暂停合约 (仅所有者)
    function pause() public onlyOwner {
        _pause();
    }
    
    /// @notice 恢复合约 (仅所有者)
    function unpause() public onlyOwner {
        _unpause();
    }
    
    /// @notice 批量转账
    /// @param recipients 接收地址数组
    /// @param amounts 金额数组
    function batchTransfer(address[] calldata recipients, uint256[] calldata amounts) external {
        require(recipients.length == amounts.length, "Length mismatch");
        
        for (uint256 i = 0; i < recipients.length; i++) {
            transfer(recipients[i], amounts[i]);
        }
    }
    
    // 重写 _update 以支持暂停功能
    function _update(address from, address to, uint256 value)
        internal
        override(ERC20, ERC20Pausable)
    {
        super._update(from, to, value);
    }
}
```

---

### 测试套件

```solidity
// test/AdvancedToken.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {AdvancedToken} from "../src/AdvancedToken.sol";

contract AdvancedTokenTest is Test {
    AdvancedToken public token;
    
    address public owner = makeAddr("owner");
    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    
    uint256 public constant INITIAL_SUPPLY = 1_000_000;
    
    function setUp() public {
        vm.prank(owner);
        token = new AdvancedToken("AdvancedToken", "ATK", INITIAL_SUPPLY);
    }
    
    // ============ 基础测试 ============
    
    function test_Metadata() public view {
        assertEq(token.name(), "AdvancedToken");
        assertEq(token.symbol(), "ATK");
        assertEq(token.decimals(), 18);
        assertEq(token.owner(), owner);
    }
    
    function test_InitialSupply() public view {
        assertEq(token.totalSupply(), INITIAL_SUPPLY * 1e18);
        assertEq(token.balanceOf(owner), INITIAL_SUPPLY * 1e18);
    }
    
    // ============ 铸造测试 ============
    
    function test_Mint() public {
        uint256 amount = 1000 * 1e18;
        
        vm.prank(owner);
        token.mint(alice, amount);
        
        assertEq(token.balanceOf(alice), amount);
    }
    
    function test_RevertWhen_MintByNonOwner() public {
        vm.prank(alice);
        vm.expectRevert();
        token.mint(alice, 1000 * 1e18);
    }
    
    function test_RevertWhen_MintExceedsMaxSupply() public {
        uint256 excess = token.MAX_SUPPLY() - token.totalSupply() + 1;
        
        vm.prank(owner);
        vm.expectRevert("Exceeds max supply");
        token.mint(alice, excess);
    }
    
    // ============ 销毁测试 ============
    
    function test_Burn() public {
        uint256 burnAmount = 1000 * 1e18;
        uint256 beforeSupply = token.totalSupply();
        
        vm.prank(owner);
        token.burn(burnAmount);
        
        assertEq(token.totalSupply(), beforeSupply - burnAmount);
    }
    
    // ============ 暂停测试 ============
    
    function test_Pause() public {
        vm.prank(owner);
        token.pause();
        
        assertTrue(token.paused());
        
        vm.prank(owner);
        vm.expectRevert();
        token.transfer(alice, 1000 * 1e18);
    }
    
    function test_Unpause() public {
        vm.startPrank(owner);
        token.pause();
        token.unpause();
        vm.stopPrank();
        
        assertFalse(token.paused());
        
        vm.prank(owner);
        token.transfer(alice, 1000 * 1e18);
        assertEq(token.balanceOf(alice), 1000 * 1e18);
    }
    
    // ============ 批量转账测试 ============
    
    function test_BatchTransfer() public {
        address[] memory recipients = new address[](3);
        recipients[0] = alice;
        recipients[1] = bob;
        recipients[2] = makeAddr("charlie");
        
        uint256[] memory amounts = new uint256[](3);
        amounts[0] = 100 * 1e18;
        amounts[1] = 200 * 1e18;
        amounts[2] = 300 * 1e18;
        
        vm.prank(owner);
        token.batchTransfer(recipients, amounts);
        
        assertEq(token.balanceOf(alice), 100 * 1e18);
        assertEq(token.balanceOf(bob), 200 * 1e18);
        assertEq(token.balanceOf(recipients[2]), 300 * 1e18);
    }
    
    // ============ Fuzz 测试 ============
    
    function testFuzz_Mint(address to, uint256 amount) public {
        vm.assume(to != address(0));
        uint256 remaining = token.MAX_SUPPLY() - token.totalSupply();
        amount = bound(amount, 1, remaining);
        
        vm.prank(owner);
        token.mint(to, amount);
        
        assertEq(token.balanceOf(to), amount);
    }
    
    function testFuzz_BurnAfterMint(uint256 mintAmount, uint256 burnAmount) public {
        uint256 remaining = token.MAX_SUPPLY() - token.totalSupply();
        mintAmount = bound(mintAmount, 1, remaining);
        
        vm.prank(owner);
        token.mint(alice, mintAmount);
        
        burnAmount = bound(burnAmount, 1, mintAmount);
        
        vm.prank(alice);
        token.burn(burnAmount);
        
        assertEq(token.balanceOf(alice), mintAmount - burnAmount);
    }
}
```

---

### 部署脚本

```solidity
// script/Deploy.s.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Script, console} from "forge-std/Script.sol";
import {AdvancedToken} from "../src/AdvancedToken.sol";

contract DeployScript is Script {
    function run() public {
        // 从环境变量获取私钥
        uint256 deployerPrivateKey = vm.envUint("PRIVATE_KEY");
        
        vm.startBroadcast(deployerPrivateKey);
        
        // 部署合约
        AdvancedToken token = new AdvancedToken(
            "AdvancedToken",    // name
            "ATK",              // symbol
            1_000_000           // initial supply (1M)
        );
        
        console.log("Token deployed at:", address(token));
        console.log("Owner:", token.owner());
        console.log("Total Supply:", token.totalSupply());
        
        vm.stopBroadcast();
    }
}
```

---

### 部署到 Sepolia

#### 1. 准备工作

```bash
# 获取 Sepolia 测试 ETH
# https://sepoliafaucet.com/
# https://www.alchemy.com/faucets/ethereum-sepolia

# 设置环境变量
export PRIVATE_KEY=your_private_key_here
export SEPOLIA_RPC_URL=https://eth-sepolia.g.alchemy.com/v2/YOUR_KEY
export ETHERSCAN_API_KEY=your_etherscan_api_key
```

#### 2. 运行测试

```bash
# 确保所有测试通过
forge test -vv

# 检查 Gas 消耗
forge test --gas-report
```

#### 3. 部署合约

```bash
# 模拟部署（不实际执行）
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --dry-run

# 实际部署
forge script script/Deploy.s.sol:DeployScript \
    --rpc-url $SEPOLIA_RPC_URL \
    --broadcast \
    --verify \
    -vvvv
```

#### 4. 验证合约

```bash
# 如果部署时没有自动验证，手动验证
forge verify-contract \
    <DEPLOYED_ADDRESS> \
    src/AdvancedToken.sol:AdvancedToken \
    --chain sepolia \
    --constructor-args $(cast abi-encode "constructor(string,string,uint256)" "AdvancedToken" "ATK" 1000000)
```

---

### 合约交互

```bash
# 查询余额
cast call <TOKEN_ADDRESS> "balanceOf(address)(uint256)" <YOUR_ADDRESS> \
    --rpc-url $SEPOLIA_RPC_URL

# 转账
cast send <TOKEN_ADDRESS> "transfer(address,uint256)(bool)" \
    <RECIPIENT> 1000000000000000000 \
    --private-key $PRIVATE_KEY \
    --rpc-url $SEPOLIA_RPC_URL

# 铸造（仅 owner）
cast send <TOKEN_ADDRESS> "mint(address,uint256)" \
    <RECIPIENT> 1000000000000000000 \
    --private-key $PRIVATE_KEY \
    --rpc-url $SEPOLIA_RPC_URL
```

---

## 📝 Week 2 总结

### 技术栈掌握

| 领域          | 技术               | 掌握程度           |
| ------------- | ------------------ | ------------------ |
| **Layer 2**   | 闪电网络、LND      | 理解原理，能开发   |
| **EVM**       | Account 模型、Gas  | 深入理解           |
| **Go 客户端** | go-ethereum        | 能封装生产级客户端 |
| **合约开发**  | Foundry + Solidity | 能编写和测试       |
| **代币标准**  | ERC-20             | 完整实现           |

### 完成的项目

1. **Day 8**: Polar 闪电网络测试环境
2. **Day 9**: LND Go 客户端
3. **Day 10-11**: ETH 交易客户端 + Multicall
4. **Day 12**: Counter + Bank 合约
5. **Day 13**: ERC-20 实现
6. **Day 14**: 完整部署流程

---

## ✅ Week 2 检查清单

- [ ] 理解闪电网络支付通道和 HTLC
- [ ] 能使用 Go 开发 LND 客户端
- [ ] 理解 EVM 架构和 Gas 机制
- [ ] 能构造、签名、发送以太坊交易
- [ ] 掌握 Foundry 工具链
- [ ] 实现并测试了 ERC-20 合约
- [ ] 成功部署合约到 Sepolia
- [ ] 在 Etherscan 验证了合约

---

## 🔗 参考资源

- [OpenZeppelin Contracts](https://docs.openzeppelin.com/contracts)
- [Foundry Book](https://book.getfoundry.sh/)
- [Sepolia Faucet](https://sepoliafaucet.com/)
- [Etherscan Sepolia](https://sepolia.etherscan.io/)

---

## 📌 下周预告

**Week 3: 合约进阶与 Go 集成**
- Day 15: Solidity 进阶 (ABI + 存储布局 + Proxy)
- Day 16: Abigen 合约绑定与 Go 集成
- Day 17: Go + Anvil E2E 集成测试
- Day 18-19: 高性能事件监听与 Custom Indexer
- Day 20-21: Week 3 整合与 Mini Project
