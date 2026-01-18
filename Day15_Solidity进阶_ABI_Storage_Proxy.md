# Day 15: Solidity 进阶 — ABI, Storage 与 Proxy

> **学习时间**：4-6 小时（理论 2h + 实战 3h + 复习 1h）
>
> **核心目标**：深入理解 EVM 底层机制，掌握 ABI 编码、存储布局（Storage Layout）以及代理模式（Proxy Pattern）的核心原理。

---

## 🎯 今日学习目标

- [ ] 理解 ABI 编码规则与函数选择器（Selector）
- [ ] 掌握 `abi.encode` 与 `abi.encodePacked` 的区别
- [ ] 深入理解 EVM 存储槽（Slot）与变量打包（Packing）规则
- [ ] 掌握 `delegatecall` 的工作原理与上下文保留特性
- [ ] 实现并测试一个简单的升级代理合约（Proxy Pattern）

---

## 📚 理论课：EVM 底层机制

### 1. ABI 编码 (Application Binary Interface)

ABI 是与以太坊智能合约交互的标准方式，用于在 EVM 内部或外部（如 dApp）对数据进行编码和解码。

#### 函数选择器 (Function Selector)

函数选择器是函数调用数据（Calldata）的前 4 个字节，用于标识要调用的函数。

计算公式：`bytes4(keccak256("functionName(type1,type2)"))`

```solidity
// 示例：transfer(address,uint256)
// Keccak256 hash: a9059cbb2ab09eb219583f4a59a5d0623ade346d962bcd4e46b11da047c9049b
// Selector: 0xa9059cbb
```

#### 编码方式对比

| 方法                           | 描述           | 特点                       | 用途                      |
| :----------------------------- | :------------- | :------------------------- | :------------------------ |
| `abi.encode(...)`              | 标准 ABI 编码  | 每个参数填充为 32 字节     | 跨合约调用，数据完整性    |
| `abi.encodePacked(...)`        | 紧凑编码       | 不填充，节省空间           | 计算 Hash，节省 Gas       |
| `abi.encodeWithSignature(...)` | 带选择器的编码 | 自动计算 Selector + encode | 低级调用 (Low-level call) |

### 2. 存储布局 (Storage Layout)

EVM 的存储是一个巨大的键值对映射（Key-Value Map），每个槽（Slot）大小为 32 字节（256 位）。

#### 静态变量与打包 (Packing)

Solidity 会尝试将多个连续的小变量打包到一个 Slot 中，以节省 Gas（Storage 读写最贵）。

```solidity
contract StoragePacking {
    // Slot 0
    uint128 public a; // 16 bytes
    uint128 public b; // 16 bytes (16+16=32, 刚好填满 Slot 0)
    
    // Slot 1
    uint256 public c; // 32 bytes (独占 Slot 1)
    
    // Slot 2
    uint64 public d;  // 8 bytes
    address public e; // 20 bytes (8+20=28, 放在 Slot 2)
    // 剩余 4 bytes 空闲
}
```

#### 动态数据存储

- **映射 (Mapping)**: 
  - 值不直接存储在定义的 Slot 中。
  - 存储位置 = `keccak256(key . slot)`
- **动态数组 (Array)**:
  - 定义的 Slot 存储数组长度。
  - 元素起始位置 = `keccak256(slot)`
  - 元素 i 位置 = `keccak256(slot) + i`

### 3. Delegatecall 与 代理模式

#### Call vs Delegatecall

| 特性           | Call                   | Delegatecall               |
| :------------- | :--------------------- | :------------------------- |
| **执行环境**   | 被调用合约 (Target)    | **调用合约 (Caller)**      |
| **msg.sender** | Caller                 | **Original Sender (User)** |
| **msg.value**  | 转发的 Value           | **Original Value**         |
| **State 修改** | 修改 Target 的 Storage | **修改 Caller 的 Storage** |

`delegatecall` 是实现可升级合约（Proxy）的基础。它允许 Proxy 合约借用 Logic 合约的代码，来修改 Proxy 自己的状态。

#### 存储冲突 (Storage Collision)

使用 `delegatecall` 时，Proxy 和 Logic 合约必须拥有**完全一致的存储布局**，否则会发生严重的覆盖错误。

```
Proxy Storage:    Logic Storage:
Slot 0: Owner     Slot 0: Counter  <-- 危险！修改 Counter 会覆盖 Owner
Slot 1: Impl      Slot 1: Owner
```

---

## 🛠️ 实战作业

### 作业 1：ABI 编解码与 Selector

创建一个工具合约，用于验证 Selector 计算和数据编码。

```solidity
// src/ABITester.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract ABITester {
    event LogBytes(bytes data);

    // 1. 计算 Selector
    function getSelector(string calldata funcSig) public pure returns (bytes4) {
        return bytes4(keccak256(bytes(funcSig)));
    }

    // 2. 比较 encode 和 encodePacked
    function testEncodings(uint256 a, address b) public pure returns (bytes memory standard, bytes memory packed) {
        standard = abi.encode(a, b);         //  32 + 32 = 64 bytes
        packed = abi.encodePacked(a, b);     //  32 + 20 = 52 bytes
    }

    // 3. 构造低级调用数据
    function getCallData(address to, uint256 amount) public pure returns (bytes memory) {
        return abi.encodeWithSignature("transfer(address,uint256)", to, amount);
    }
}
```

### 作业 2：存储槽读取 (Using Assembly)

使用内联汇编（Yul）直接读取合约的私有存储槽。

```solidity
// src/Vault.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract Vault {
    // Slot 0
    uint256 private secretPassword;
    
    // Slot 1
    uint128 public id;
    uint128 public count;
    
    mapping(address => uint256) public balances; // Slot 2

    constructor(uint256 _password) {
        secretPassword = _password;
        id = 1;
        count = 0;
    }
    
    function deposit() public payable {
        balances[msg.sender] += msg.value;
    }
}

// src/SlotReader.sol
contract SlotReader {
    // 读取指定合约的指定 Slot
    function readSlot(address target, uint256 slot) public view returns (bytes32 result) {
        // 使用 staticcall 调用目标合约可能无法直接读 storage，
        // 实际上只能通过 extcodesize 等获取代码。
        // 但如果是在 Foundry 测试环境中，我们可以用 vm.load
        // 这里演示如果是在合约内部如何读取自己的 Slot (Yul)
        
        assembly {
            result := sload(slot)
        }
    }
}
```

**Foundry 测试脚本 (读取 Vault 私有数据)**:

```solidity
// test/Vault.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/Vault.sol";

contract VaultTest is Test {
    Vault vault;

    function setUp() public {
        vault = new Vault(123456);
    }

    function test_ReadPrivateSlot() public {
        // 使用 vm.load 读取任意合约的 storage
        bytes32 slot0 = vm.load(address(vault), bytes32(uint256(0)));
        uint256 password = uint256(slot0);
        
        console.log("Password:", password);
        assertEq(password, 123456);
    }

    function test_ReadMapping() public {
        address user = makeAddr("user");
        vm.deal(user, 1 ether);
        
        vm.prank(user);
        vault.deposit{value: 1 ether}();

        // 手动计算 Mapping 的 Slot
        // key = user, position = 2
        bytes32 slot = keccak256(abi.encode(user, uint256(2)));
        
        bytes32 val = vm.load(address(vault), slot);
        uint256 balance = uint256(val);
        
        assertEq(balance, 1 ether);
    }
}
```

### 作业 3：最小代理实现 (Proxy Pattern)

实现一个简单的可升级合约架构：Proxy + ImplementationV1 + ImplementationV2。

#### 3.1 逻辑合约 (Implementation)

注意：逻辑合约中不应定义构造函数（通常用 initialize），且必须注意存储布局。

```solidity
// src/LogicV1.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract LogicV1 {
    // 必须与 Proxy 布局一致 (ProxySlot 0 通常是 Implementation 地址，这里为了简化，我们假设 Proxy 使用标准布局)
    // 更好的做法是使用 Unstructured Storage 避免冲突，这里演示基本冲突风险
    
    uint256 public value;

    function initialize() public {
        value = 100;
    }

    function setValue(uint256 _value) public {
        value = _value;
    }
}

// src/LogicV2.sol (升级版，增加功能)
contract LogicV2 {
    uint256 public value;

    function initialize() public {
        // V2 初始化逻辑
    }

    function setValue(uint256 _value) public {
        value = _value * 2; // 逻辑改变：存入 2 倍
    }
    
    function increment() public {
        value += 1;
    }
}
```

#### 3.2 代理合约 (Proxy)

```solidity
// src/SimpleProxy.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

contract SimpleProxy {
    // storage layout 必须非常小心
    // 为了避免与 Logic 合约冲突，通常将 implementation 地址存在一个随机的极远槽位 (EIP-1967)
    // 这里为了演示 delegatecall 原理，使用简单的 state 变量（这其实是反模式，仅供教学）
    
    address public implementation; // Slot 0
    uint256 public value;          // Slot 1 (对应 Logic 的 value)

    constructor(address _impl) {
        implementation = _impl;
    }

    function upgradeTo(address _newImpl) public {
        implementation = _newImpl;
    }

    // Fallback: 转发所有调用到 implementation
    fallback() external payable {
        address _impl = implementation;
        require(_impl != address(0), "Impl not set");

        assembly {
            // 1. 复制 calldata
            calldatacopy(0, 0, calldatasize())

            // 2. delegatecall
            // gas, address, argsOffset, argsSize, retOffset, retSize
            let result := delegatecall(gas(), _impl, 0, calldatasize(), 0, 0)

            // 3. 复制 return data
            returndatacopy(0, 0, returndatasize())

            // 4. 返回或回滚
            switch result
            case 0 { revert(0, returndatasize()) }
            default { return(0, returndatasize()) }
        }
    }
    
    receive() external payable {}
}
```

> **⚠️ 警告**：上面的 `SimpleProxy` 存在严重的存储冲突风险。因为 `SimpleProxy` 在 Slot 0 定义了 `implementation`，而如果是上面的 `LogicV1`，它的 Slot 0 是 `value`。当 Logic 修改 `value` 时，实际上会覆盖 Proxy 的 `implementation` 地址，导致合约崩溃！
>
> **修正版 Logic (State Layout Alignment)**:

```solidity
// src/LogicFixed.sol
contract LogicFixed {
    address public implementation; // 占位 Slot 0，与 Proxy 保持一致
    uint256 public value;          // Slot 1，真正的业务数据

    function setValue(uint256 _value) public {
        value = _value;
    }
}
```

### 作业 4：测试升级流程

```solidity
// test/Proxy.t.sol
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.20;

import "forge-std/Test.sol";
import "../src/SimpleProxy.sol";
import "../src/LogicFixed.sol"; // 使用修正后的逻辑合约

contract ProxyTest is Test {
    SimpleProxy proxy;
    LogicFixed logicV1;
    LogicFixed logicV2; // 假设有 V2

    function setUp() public {
        logicV1 = new LogicFixed();
        proxy = new SimpleProxy(address(logicV1));
    }

    function test_DelegateCall() public {
        // 把 Proxy 转换成 Logic 接口调用
        LogicFixed proxyAsLogic = LogicFixed(address(proxy));

        // 调用 setValue
        proxyAsLogic.setValue(42);

        // 检查 Proxy 的 storage
        assertEq(proxy.value(), 42); // Logic 修改了 Proxy 的 storage
        assertEq(logicV1.value(), 0); // Logic 自己的 storage 未变
    }
    
    function test_Upgrade() public {
        LogicFixed proxyAsLogic = LogicFixed(address(proxy));
        
        // 升级前：调用 setValue(10) 存储 10
        proxyAsLogic.setValue(10);
        assertEq(proxy.value(), 10);
        
        // 部署 V2 逻辑合约 (假设 setValue 存储 2 倍)
        LogicV2Fixed logicV2 = new LogicV2Fixed();
        proxy.upgradeTo(address(logicV2));
        
        // 升级后：调用 setValue(10) 存储 20
        proxyAsLogic.setValue(10);
        assertEq(proxy.value(), 20); // 10 * 2 = 20
    }
}
```

---

## 📝 知识点总结

### 1. Storage Slot 计算

| 类型            | 计算方式           | 解释                      |
| :-------------- | :----------------- | :------------------------ |
| `stateVar`      | count from 0       | 顺序排列，能 pack 则 pack |
| `mapping(k=>v)` | `keccak256(k . p)` | p 是定义 mapping 的 slot  |
| `array[]`       | `keccak256(p) + i` | p 存储长度，内容在哈希处  |

### 2. Proxy 模式核心

- **逻辑在实现合约，状态在代理合约**。
- **Delegatecall** 让逻辑合约的代码在代理合约的上下文中运行。
- **EIP-1967** 标准槽位：为了避免 Slot 0 冲突，通过计算固定的哈希值（如 `keccak256("eip1967.proxy.implementation") - 1`）来存储 implementation 地址。

---

## ✅ 今日检查清单

- [ ] 理解了为什么 `abi.encodePacked` 更省 Gas 但会造成哈希冲突（如果参数是动态类型）
- [ ] 能够手动计算 Mapping 某个 Key 的 Storage Slot
- [ ] 明白了 Delegatecall 的 "借尸还魂" 特性（借代码，改己身）
- [ ] 成功运行了 Proxy 测试，观察到了状态改变

---

## 📌 明日预告

**Day 16: Abigen 合约绑定与 Go 集成**
- 安装 `abigen` 工具
- 生成 Go 合约绑定文件
- 使用 Go 部署合约
- 监听合约事件（Go Client）
