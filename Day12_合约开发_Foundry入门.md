# Day 12: 合约开发 — Foundry 入门

> **学习时间**：4-6 小时（理论 1h + 实战 4h + 复习 0.5h）
>
> **核心目标**：掌握 Foundry 工具链，使用 Solidity 编写和测试智能合约

---

## 🎯 今日学习目标

- [ ] 安装并配置 Foundry 开发环境
- [ ] 掌握 forge/cast/anvil 三大工具的使用
- [ ] 编写 Counter 和 Bank 智能合约
- [ ] 使用 Solidity 编写合约测试
- [ ] 使用 AI 辅助生成测试用例

---

## 📚 理论课：为什么选择 Foundry

### Foundry vs 传统工具链对比

| 特性         | Foundry             | Hardhat/Truffle       |
| ------------ | ------------------- | --------------------- |
| **测试语言** | Solidity            | JavaScript/TypeScript |
| **执行速度** | 极快（Rust 编写）   | 较慢                  |
| **Fuzzing**  | 内置支持            | 需要插件              |
| **调试**     | 内置 trace          | 需要配置              |
| **依赖管理** | Git submodules      | npm                   |
| **学习曲线** | 简单（纯 Solidity） | 需要 JS 知识          |

### Foundry 工具链

```
┌────────────────────────────────────────────────────────────────┐
│                      Foundry 工具链                             │
├────────────────────────────────────────────────────────────────┤
│                                                                │
│  forge   ─── 合约编译、测试、部署                               │
│              • forge build    编译合约                         │
│              • forge test     运行测试                          │
│              • forge create   部署合约                         │
│              • forge script   运行部署脚本                      │
│                                                                │
│  cast    ─── 链上交互命令行工具                                 │
│              • cast call      读取合约                         │
│              • cast send      发送交易                          │
│              • cast balance   查询余额                          │
│              • cast abi-decode 解码数据                        │
│                                                                │
│  anvil   ─── 本地测试节点                                       │
│              • 快速区块                                        │
│              • 状态快照                                        │
│              • Mainnet Fork                                    │
│                                                                │
│  chisel  ─── Solidity REPL                                     │
│              • 交互式 Solidity 环境                            │
│                                                                │
└────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 实战作业

### 作业 1：环境安装

#### 1.1 安装 Foundry

```bash
# 安装 Foundryup
curl -L https://foundry.paradigm.xyz | bash

# 安装/更新 Foundry
foundryup

# 验证安装
forge --version
cast --version
anvil --version
```

#### 1.2 初始化项目

```bash
# 创建项目目录
mkdir -p ~/blockchain-course/day12-foundry
cd ~/blockchain-course/day12-foundry

# 初始化 Foundry 项目
forge init

# 项目结构
tree -L 2
# .
# ├── foundry.toml      # 配置文件
# ├── lib/              # 依赖库
# │   └── forge-std/    # 标准测试库
# ├── script/           # 部署脚本
# ├── src/              # 合约源码
# │   └── Counter.sol
# └── test/             # 测试文件
#     └── Counter.t.sol
```

#### 1.3 配置 foundry.toml

```toml
[profile.default]
src = "src"
out = "out"
libs = ["lib"]
solc = "0.8.20"
optimizer = true
optimizer_runs = 200

# 测试配置
[profile.default.fuzz]
runs = 256
max_test_rejects = 65536

# 格式化配置
[fmt]
line_length = 120
tab_width = 4
quote_style = "double"
```

---

### 作业 2：Counter 合约

#### 2.1 合约代码

```solidity
// src/Counter.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Counter 计数器合约
/// @notice 一个简单的计数器，支持增加、减少和设置值
contract Counter {
    /// @notice 当前计数值
    uint256 public number;
    
    /// @notice 计数变化事件
    /// @param oldValue 旧值
    /// @param newValue 新值
    event NumberChanged(uint256 indexed oldValue, uint256 indexed newValue);
    
    /// @notice 设置计数值
    /// @param newNumber 新的计数值
    function setNumber(uint256 newNumber) public {
        uint256 oldNumber = number;
        number = newNumber;
        emit NumberChanged(oldNumber, newNumber);
    }
    
    /// @notice 增加计数
    function increment() public {
        uint256 oldNumber = number;
        number++;
        emit NumberChanged(oldNumber, number);
    }
    
    /// @notice 减少计数
    function decrement() public {
        require(number > 0, "Counter: cannot decrement below zero");
        uint256 oldNumber = number;
        number--;
        emit NumberChanged(oldNumber, number);
    }
    
    /// @notice 重置计数器
    function reset() public {
        uint256 oldNumber = number;
        number = 0;
        emit NumberChanged(oldNumber, 0);
    }
}
```

#### 2.2 测试代码

```solidity
// test/Counter.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {Counter} from "../src/Counter.sol";

contract CounterTest is Test {
    Counter public counter;
    
    // 每个测试前执行
    function setUp() public {
        counter = new Counter();
    }
    
    // 测试初始值
    function test_InitialValue() public view {
        assertEq(counter.number(), 0);
    }
    
    // 测试增加
    function test_Increment() public {
        counter.increment();
        assertEq(counter.number(), 1);
    }
    
    // 测试多次增加
    function test_MultipleIncrements() public {
        counter.increment();
        counter.increment();
        counter.increment();
        assertEq(counter.number(), 3);
    }
    
    // 测试设置值
    function test_SetNumber() public {
        counter.setNumber(42);
        assertEq(counter.number(), 42);
    }
    
    // 测试减少
    function test_Decrement() public {
        counter.setNumber(10);
        counter.decrement();
        assertEq(counter.number(), 9);
    }
    
    // 测试减少到零以下会失败
    function test_RevertWhen_DecrementBelowZero() public {
        // 期望回滚，并验证错误消息
        vm.expectRevert("Counter: cannot decrement below zero");
        counter.decrement();
    }
    
    // 测试重置
    function test_Reset() public {
        counter.setNumber(100);
        counter.reset();
        assertEq(counter.number(), 0);
    }
    
    // 测试事件触发
    function test_EmitEvent() public {
        // 期望触发事件，检查 topic 和 data
        vm.expectEmit(true, true, false, true);
        emit Counter.NumberChanged(0, 42);
        
        counter.setNumber(42);
    }
    
    // Fuzz 测试：任意值设置
    function testFuzz_SetNumber(uint256 x) public {
        counter.setNumber(x);
        assertEq(counter.number(), x);
    }
    
    // Fuzz 测试：增加后值变大
    function testFuzz_Increment(uint256 start) public {
        // 避免溢出
        vm.assume(start < type(uint256).max);
        
        counter.setNumber(start);
        counter.increment();
        assertEq(counter.number(), start + 1);
    }
}
```

#### 2.3 运行测试

```bash
# 运行所有测试
forge test

# 显示详细输出
forge test -vv

# 显示 trace
forge test -vvvv

# 运行特定测试
forge test --match-test test_Increment

# 运行 Fuzz 测试（更多轮次）
forge test --match-test testFuzz_SetNumber --fuzz-runs 1000

# 显示 Gas 报告
forge test --gas-report
```

---

### 作业 3：Bank 合约

#### 3.1 合约代码

```solidity
// src/Bank.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

/// @title Bank 银行合约
/// @notice 支持存款、取款、查询余额的简易银行
contract Bank {
    /// @notice 用户余额映射
    mapping(address => uint256) public balances;
    
    /// @notice 合约总存款
    uint256 public totalDeposits;
    
    /// @notice 存款事件
    event Deposit(address indexed user, uint256 amount);
    
    /// @notice 取款事件
    event Withdrawal(address indexed user, uint256 amount);
    
    /// @notice 转账事件
    event Transfer(address indexed from, address indexed to, uint256 amount);
    
    /// @notice 存款
    function deposit() public payable {
        require(msg.value > 0, "Bank: deposit amount must be greater than 0");
        
        balances[msg.sender] += msg.value;
        totalDeposits += msg.value;
        
        emit Deposit(msg.sender, msg.value);
    }
    
    /// @notice 取款
    /// @param amount 取款金额
    function withdraw(uint256 amount) public {
        require(amount > 0, "Bank: withdraw amount must be greater than 0");
        require(balances[msg.sender] >= amount, "Bank: insufficient balance");
        
        balances[msg.sender] -= amount;
        totalDeposits -= amount;
        
        // 使用 call 发送 ETH（推荐方式）
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Bank: transfer failed");
        
        emit Withdrawal(msg.sender, amount);
    }
    
    /// @notice 取出全部余额
    function withdrawAll() public {
        uint256 amount = balances[msg.sender];
        require(amount > 0, "Bank: no balance to withdraw");
        
        balances[msg.sender] = 0;
        totalDeposits -= amount;
        
        (bool success, ) = msg.sender.call{value: amount}("");
        require(success, "Bank: transfer failed");
        
        emit Withdrawal(msg.sender, amount);
    }
    
    /// @notice 转账给其他用户
    /// @param to 接收地址
    /// @param amount 转账金额
    function transfer(address to, uint256 amount) public {
        require(to != address(0), "Bank: cannot transfer to zero address");
        require(to != msg.sender, "Bank: cannot transfer to yourself");
        require(amount > 0, "Bank: transfer amount must be greater than 0");
        require(balances[msg.sender] >= amount, "Bank: insufficient balance");
        
        balances[msg.sender] -= amount;
        balances[to] += amount;
        
        emit Transfer(msg.sender, to, amount);
    }
    
    /// @notice 查询余额
    /// @param user 用户地址
    /// @return 用户余额
    function getBalance(address user) public view returns (uint256) {
        return balances[user];
    }
    
    /// @notice 接收 ETH（直接转账时自动存款）
    receive() external payable {
        deposit();
    }
}
```

#### 3.2 Bank 测试

```solidity
// test/Bank.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import {Test, console} from "forge-std/Test.sol";
import {Bank} from "../src/Bank.sol";

contract BankTest is Test {
    Bank public bank;
    
    address public alice = makeAddr("alice");
    address public bob = makeAddr("bob");
    
    function setUp() public {
        bank = new Bank();
        
        // 给测试账户一些 ETH
        vm.deal(alice, 100 ether);
        vm.deal(bob, 100 ether);
    }
    
    // === 存款测试 ===
    
    function test_Deposit() public {
        vm.prank(alice);
        bank.deposit{value: 1 ether}();
        
        assertEq(bank.balances(alice), 1 ether);
        assertEq(bank.totalDeposits(), 1 ether);
    }
    
    function test_DepositMultiple() public {
        vm.startPrank(alice);
        bank.deposit{value: 1 ether}();
        bank.deposit{value: 2 ether}();
        vm.stopPrank();
        
        assertEq(bank.balances(alice), 3 ether);
    }
    
    function test_RevertWhen_DepositZero() public {
        vm.prank(alice);
        vm.expectRevert("Bank: deposit amount must be greater than 0");
        bank.deposit{value: 0}();
    }
    
    function test_DepositEmitsEvent() public {
        vm.expectEmit(true, false, false, true);
        emit Bank.Deposit(alice, 1 ether);
        
        vm.prank(alice);
        bank.deposit{value: 1 ether}();
    }
    
    // === 取款测试 ===
    
    function test_Withdraw() public {
        vm.startPrank(alice);
        bank.deposit{value: 5 ether}();
        
        uint256 beforeBalance = alice.balance;
        bank.withdraw(2 ether);
        uint256 afterBalance = alice.balance;
        
        assertEq(bank.balances(alice), 3 ether);
        assertEq(afterBalance - beforeBalance, 2 ether);
        vm.stopPrank();
    }
    
    function test_WithdrawAll() public {
        vm.startPrank(alice);
        bank.deposit{value: 5 ether}();
        bank.withdrawAll();
        vm.stopPrank();
        
        assertEq(bank.balances(alice), 0);
    }
    
    function test_RevertWhen_WithdrawInsufficientBalance() public {
        vm.startPrank(alice);
        bank.deposit{value: 1 ether}();
        
        vm.expectRevert("Bank: insufficient balance");
        bank.withdraw(2 ether);
        vm.stopPrank();
    }
    
    // === 转账测试 ===
    
    function test_Transfer() public {
        vm.prank(alice);
        bank.deposit{value: 5 ether}();
        
        vm.prank(alice);
        bank.transfer(bob, 2 ether);
        
        assertEq(bank.balances(alice), 3 ether);
        assertEq(bank.balances(bob), 2 ether);
    }
    
    function test_RevertWhen_TransferToZeroAddress() public {
        vm.startPrank(alice);
        bank.deposit{value: 5 ether}();
        
        vm.expectRevert("Bank: cannot transfer to zero address");
        bank.transfer(address(0), 1 ether);
        vm.stopPrank();
    }
    
    function test_RevertWhen_TransferToSelf() public {
        vm.startPrank(alice);
        bank.deposit{value: 5 ether}();
        
        vm.expectRevert("Bank: cannot transfer to yourself");
        bank.transfer(alice, 1 ether);
        vm.stopPrank();
    }
    
    // === Receive 测试 ===
    
    function test_ReceiveDeposit() public {
        vm.prank(alice);
        (bool success, ) = address(bank).call{value: 1 ether}("");
        assertTrue(success);
        
        assertEq(bank.balances(alice), 1 ether);
    }
    
    // === Fuzz 测试 ===
    
    function testFuzz_DepositAndWithdraw(uint256 depositAmount, uint256 withdrawAmount) public {
        // 限制范围避免溢出
        depositAmount = bound(depositAmount, 1, 50 ether);
        withdrawAmount = bound(withdrawAmount, 1, depositAmount);
        
        vm.deal(alice, depositAmount);
        
        vm.startPrank(alice);
        bank.deposit{value: depositAmount}();
        bank.withdraw(withdrawAmount);
        vm.stopPrank();
        
        assertEq(bank.balances(alice), depositAmount - withdrawAmount);
    }
    
    function testFuzz_Transfer(uint256 amount) public {
        amount = bound(amount, 1, 50 ether);
        vm.deal(alice, amount);
        
        vm.prank(alice);
        bank.deposit{value: amount}();
        
        vm.prank(alice);
        bank.transfer(bob, amount);
        
        assertEq(bank.balances(alice), 0);
        assertEq(bank.balances(bob), amount);
    }
}
```

---

### 作业 4：Cast 命令行工具

```bash
# === 启动 Anvil ===
anvil

# === 在另一个终端执行 ===

# 查询余额
cast balance 0xf39Fd6e51aad88F6F4ce6aB8827279cffFb92266

# 发送 ETH
cast send 0x70997970C51812dc3A010C7d01b50e0d17dc79C8 \
  --value 1ether \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# 部署合约
forge create src/Counter.sol:Counter \
  --rpc-url http://127.0.0.1:8545 \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# 调用合约函数（读取）
cast call <CONTRACT_ADDRESS> "number()" --rpc-url http://127.0.0.1:8545

# 调用合约函数（写入）
cast send <CONTRACT_ADDRESS> "increment()" \
  --private-key 0xac0974bec39a17e36ba4a6b4d238ff944bacb478cbed5efcae784d7bf4f2ff80

# 解码 ABI
cast abi-decode "transfer(address,uint256)" 0x...

# 编码函数调用
cast calldata "transfer(address,uint256)" 0x70997970... 1000000

# 查询区块
cast block-number
cast block latest

# 查询 Gas 价格
cast gas-price

# 查询交易
cast tx <TX_HASH>
cast receipt <TX_HASH>
```

---

### 作业 5：AI 辅助生成测试

使用 Cursor 或其他 AI IDE，尝试以下 Prompt：

```
Generate a comprehensive test suite for this Bank contract using Foundry syntax.
Include:
1. Unit tests for all functions
2. Edge cases (zero amounts, overflow, underflow)
3. Fuzz tests for deposit and withdraw
4. Reentrancy attack test
5. Events emission tests
```

---

## 📝 知识点总结

### Foundry 核心命令

| 命令               | 用途           |
| ------------------ | -------------- |
| `forge init`       | 初始化项目     |
| `forge build`      | 编译合约       |
| `forge test`       | 运行测试       |
| `forge test -vvvv` | 显示详细 trace |
| `forge create`     | 部署合约       |
| `cast call`        | 调用读函数     |
| `cast send`        | 发送交易       |
| `anvil`            | 启动本地节点   |

### 测试语法

| 语法                    | 用途           |
| ----------------------- | -------------- |
| `vm.prank(addr)`        | 模拟地址调用   |
| `vm.deal(addr, amount)` | 设置 ETH 余额  |
| `vm.expectRevert(msg)`  | 期望回滚       |
| `vm.expectEmit(...)`    | 期望事件       |
| `bound(x, min, max)`    | 限制 Fuzz 范围 |

---

## ✅ 今日检查清单

- [ ] 成功安装并配置 Foundry
- [ ] 编写并测试了 Counter 合约
- [ ] 编写并测试了 Bank 合约
- [ ] 掌握了 Cast 命令行工具
- [ ] 尝试使用 AI 生成测试用例

---

## 📌 明日预告

**Day 13: Solidity 基础语法与 ERC-20**
- Solidity 数据类型与函数可见性
- 修饰器与事件
- ERC-20 标准实现
- Fuzzing 测试与安全性验证
